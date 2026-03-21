from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Iterable, List

from backend.bd.database import SessionLocal
from backend.bd.models import Restaurant
from backend.routers.iiko_sales import (
    _build_sync_source_conflict_map,
    _build_sync_source_groups,
    _restaurant_iiko_source_key,
    _sync_sales_orders_and_items_resilient,
)


def _parse_restaurant_ids(value: str) -> List[int]:
    ids: List[int] = []
    for chunk in str(value or "").split(","):
        clean = chunk.strip()
        if not clean:
            continue
        try:
            ids.append(int(clean))
        except Exception:
            raise argparse.ArgumentTypeError(f"Invalid restaurant id: {clean}")
    unique_sorted = sorted({rid for rid in ids if rid > 0})
    if not unique_sorted:
        raise argparse.ArgumentTypeError("restaurant ids list is empty")
    return unique_sorted


def _iter_target_restaurants(restaurants: Iterable[Restaurant], requested_ids: List[int] | None) -> List[Restaurant]:
    rows = list(restaurants)
    if not requested_ids:
        return sorted(rows, key=lambda row: int(row.id))
    requested_set = {int(rid) for rid in requested_ids}
    selected = [row for row in rows if int(row.id) in requested_set]
    missing = sorted(requested_set.difference({int(row.id) for row in selected}))
    if missing:
        raise RuntimeError(f"Restaurants not found: {', '.join(str(v) for v in missing)}")
    return sorted(selected, key=lambda row: int(row.id))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill iiko sales history directly on backend with chunked windows. "
            "Useful for long periods (months/years) without frontend timeouts."
        )
    )
    parser.add_argument("--from-date", required=True, help="Start date, YYYY-MM-DD")
    parser.add_argument("--to-date", required=True, help="End date, YYYY-MM-DD")
    parser.add_argument(
        "--restaurant-ids",
        type=_parse_restaurant_ids,
        default=None,
        help="Comma-separated ids, example: 1,2,5. If omitted, all restaurants are processed.",
    )
    parser.add_argument(
        "--batch-days",
        type=int,
        default=31,
        help=(
            "High-level batch size in days with commit after each batch. "
            "Recommended 14-31 for long backfill. Default: 31"
        ),
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=3,
        help="Sync window chunk size in days (recommended 1-3 for large history). Default: 3",
    )
    parser.add_argument(
        "--retry-count",
        type=int,
        default=6,
        help="Retries per chunk on timeout/network errors. Default: 6",
    )
    parser.add_argument(
        "--retry-base-seconds",
        type=float,
        default=2.0,
        help="Base retry delay (exponential). Default: 2.0",
    )
    parser.add_argument(
        "--retry-max-seconds",
        type=float,
        default=30.0,
        help="Maximum retry delay. Default: 30.0",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=600,
        help="iiko OLAP HTTP timeout in seconds. Default: 600",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with next restaurant if one restaurant fails.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making sync requests.",
    )
    return parser


def _set_runtime_sync_env(args: argparse.Namespace) -> None:
    os.environ["IIKO_SALES_SYNC_CHUNK_DAYS"] = str(max(1, int(args.chunk_days)))
    os.environ["IIKO_SALES_SYNC_RETRY_COUNT"] = str(max(0, int(args.retry_count)))
    os.environ["IIKO_SALES_SYNC_RETRY_BASE_SECONDS"] = str(max(0.1, float(args.retry_base_seconds)))
    os.environ["IIKO_SALES_SYNC_RETRY_MAX_SECONDS"] = str(max(0.1, float(args.retry_max_seconds)))
    os.environ["IIKO_OLAP_TIMEOUT_SECONDS"] = str(max(30, int(args.timeout_seconds)))


def _parse_iso_date(value: str):
    clean = str(value or "").strip()
    try:
        return datetime.strptime(clean, "%Y-%m-%d").date()
    except Exception as exc:
        raise ValueError(f"Invalid date format '{value}'. Expected YYYY-MM-DD") from exc


def _iter_date_batches(from_date: str, to_date: str, batch_days: int):
    start = _parse_iso_date(from_date)
    end = _parse_iso_date(to_date)
    if start > end:
        raise ValueError("from-date cannot be later than to-date")
    step = max(1, int(batch_days))
    cursor = start
    while cursor <= end:
        batch_end = min(cursor + timedelta(days=step - 1), end)
        yield cursor.isoformat(), batch_end.isoformat()
        cursor = batch_end + timedelta(days=1)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    _set_runtime_sync_env(args)
    date_batches = list(_iter_date_batches(args.from_date, args.to_date, args.batch_days))

    try:
        with SessionLocal() as db:
            all_restaurants = db.query(Restaurant).order_by(Restaurant.id.asc()).all()
            restaurants = _iter_target_restaurants(all_restaurants, args.restaurant_ids)
            if not restaurants:
                print("No restaurants selected.")
                return 0

            # Route strictness/conflicts should be evaluated only within current sync scope.
            # Otherwise hidden/non-synced restaurants with the same iiko credentials can
            # force strict routing and drop rows as routing_conflicts.
            routing_scope_restaurants = [
                row for row in restaurants if bool(getattr(row, "participates_in_sales", True))
            ]
            source_groups = _build_sync_source_groups(routing_scope_restaurants)
            source_conflicts = _build_sync_source_conflict_map(routing_scope_restaurants)

            print(
                f"Starting iiko sales backfill: {args.from_date}..{args.to_date}, "
                f"restaurants={len(restaurants)}, chunk_days={os.environ['IIKO_SALES_SYNC_CHUNK_DAYS']}, "
                f"batch_days={max(1, int(args.batch_days))}, timeout={os.environ['IIKO_OLAP_TIMEOUT_SECONDS']}s"
            )

            synced = 0
            skipped = 0
            errors = 0

            for restaurant in restaurants:
                rest_id = int(restaurant.id)
                rest_name = restaurant.name or f"#{rest_id}"
                print(f"\n[{rest_id}] {rest_name}")

                conflict = source_conflicts.get(rest_id)
                if conflict:
                    errors += 1
                    related = ", ".join(conflict.get("related") or [])
                    print(
                        "  ERROR source conflict: "
                        f"allowed via #{conflict.get('primary_id')} ({conflict.get('primary_name')}); related: {related}"
                    )
                    if not args.continue_on_error:
                        return 1
                    continue

                if not restaurant.server or not restaurant.iiko_login or not restaurant.iiko_password_sha1:
                    skipped += 1
                    print("  SKIP no iiko credentials configured")
                    continue

                source_key = _restaurant_iiko_source_key(restaurant)
                strict_source_routing = bool(source_key and len(source_groups.get(source_key, [])) > 1)

                if args.dry_run:
                    print(
                        f"  DRY RUN strict_source_routing={strict_source_routing}, "
                        f"server={restaurant.server}, batches={len(date_batches)}"
                    )
                    continue

                restaurant_orders = 0
                restaurant_items = 0
                restaurant_errors = 0
                for index, (batch_from, batch_to) in enumerate(date_batches, start=1):
                    try:
                        result = _sync_sales_orders_and_items_resilient(
                            db,
                            restaurant,
                            batch_from,
                            batch_to,
                            strict_source_routing=strict_source_routing,
                            sync_actor="script",
                        )
                        db.commit()
                        batch_orders = int(result.get("orders") or 0)
                        batch_items = int(result.get("items") or 0)
                        mapped_orders = int(result.get("mapped_orders") or 0)
                        unmapped_orders = int(result.get("unmapped_orders") or 0)
                        routing_conflicts = int(result.get("routing_conflicts") or 0)
                        restaurant_orders += batch_orders
                        restaurant_items += batch_items
                        print(
                            f"  batch {index}/{len(date_batches)} {batch_from}..{batch_to}: "
                            f"OK orders={batch_orders}, items={batch_items}, "
                            f"mapped={mapped_orders}, unmapped={unmapped_orders}, "
                            f"routing_conflicts={routing_conflicts}"
                        )
                    except Exception as exc:
                        db.rollback()
                        errors += 1
                        restaurant_errors += 1
                        print(
                            f"  batch {index}/{len(date_batches)} {batch_from}..{batch_to}: ERROR {exc}"
                        )
                        error_text = str(exc)
                        auth_forbidden = "resto/api/auth" in error_text and "403" in error_text
                        if auth_forbidden:
                            print(
                                "  AUTH 403 detected, skipping remaining batches for this restaurant "
                                "to avoid lock escalation."
                            )
                            break
                        if not args.continue_on_error:
                            return 1

                if restaurant_errors == 0:
                    synced += 1
                    print(f"  RESULT OK orders={restaurant_orders}, items={restaurant_items}")
                else:
                    print(
                        f"  RESULT PARTIAL orders={restaurant_orders}, items={restaurant_items}, "
                        f"errors={restaurant_errors}"
                    )

            print(
                "\nDone: "
                f"synced={synced}, skipped={skipped}, errors={errors}, total={len(restaurants)}"
            )
            return 0 if errors == 0 else (0 if args.continue_on_error else 1)
    except Exception as exc:
        print(f"Fatal error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
