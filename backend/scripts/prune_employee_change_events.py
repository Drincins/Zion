from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

from sqlalchemy import func

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.bd.database import SessionLocal
from backend.bd.models import EmployeeChangeEvent


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prune old employee change events safely. Defaults to dry-run.",
    )
    parser.add_argument(
        "--before-date",
        required=True,
        help="Delete events with created_at before this ISO date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--field",
        default="attendance",
        help="Only prune events for this field. Default: attendance",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Optional source filter. Can be passed multiple times.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Deletion batch size when --apply is used. Default: 5000",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete matching rows. Without this flag the script is dry-run only.",
    )
    return parser.parse_args()


def _monthly_breakdown(db, *, field: str, before_date: date, sources: Sequence[str]) -> list[tuple]:
    query = (
        db.query(
            func.date_trunc("month", EmployeeChangeEvent.created_at).label("month"),
            func.count(EmployeeChangeEvent.id).label("rows_count"),
        )
        .filter(
            EmployeeChangeEvent.field == field,
            EmployeeChangeEvent.created_at < before_date,
        )
    )
    if sources:
        query = query.filter(EmployeeChangeEvent.source.in_(sources))
    return (
        query.group_by(func.date_trunc("month", EmployeeChangeEvent.created_at))
        .order_by(func.date_trunc("month", EmployeeChangeEvent.created_at).asc())
        .all()
    )


def _matching_count(db, *, field: str, before_date: date, sources: Sequence[str]) -> int:
    query = db.query(func.count(EmployeeChangeEvent.id)).filter(
        EmployeeChangeEvent.field == field,
        EmployeeChangeEvent.created_at < before_date,
    )
    if sources:
        query = query.filter(EmployeeChangeEvent.source.in_(sources))
    return int(query.scalar() or 0)


def _delete_batches(db, *, field: str, before_date: date, sources: Sequence[str], batch_size: int) -> int:
    deleted_total = 0
    while True:
        query = db.query(EmployeeChangeEvent.id).filter(
            EmployeeChangeEvent.field == field,
            EmployeeChangeEvent.created_at < before_date,
        )
        if sources:
            query = query.filter(EmployeeChangeEvent.source.in_(sources))
        batch_ids = [row[0] for row in query.order_by(EmployeeChangeEvent.id.asc()).limit(batch_size).all()]
        if not batch_ids:
            break
        (
            db.query(EmployeeChangeEvent)
            .filter(EmployeeChangeEvent.id.in_(batch_ids))
            .delete(synchronize_session=False)
        )
        db.commit()
        deleted_total += len(batch_ids)
        print(f"deleted batch: {len(batch_ids)} rows (total {deleted_total})")
    return deleted_total


def main() -> int:
    args = _parse_args()
    before_date = date.fromisoformat(args.before_date)
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")

    db = SessionLocal()
    try:
        count = _matching_count(
            db,
            field=args.field,
            before_date=before_date,
            sources=args.source,
        )
        print(f"field={args.field}")
        print(f"before_date={before_date.isoformat()}")
        print(f"sources={args.source or ['*']}")
        print(f"matching_rows={count}")
        print("")
        print("monthly_breakdown:")
        for month, rows_count in _monthly_breakdown(
            db,
            field=args.field,
            before_date=before_date,
            sources=args.source,
        ):
            month_label = month.date().isoformat() if month is not None else "unknown"
            print(f"  {month_label}: {rows_count}")

        if not args.apply:
            print("")
            print("dry-run only; nothing deleted")
            print("run again with --apply to delete matching rows")
            return 0

        print("")
        deleted_total = _delete_batches(
            db,
            field=args.field,
            before_date=before_date,
            sources=args.source,
            batch_size=args.batch_size,
        )
        print("")
        print(f"deleted_total={deleted_total}")
        print("note: run VACUUM (or wait for autovacuum) if you want space reuse to catch up")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
