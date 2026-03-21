from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Iterable, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, case, func, or_, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload, load_only

from backend.bd.database import get_db
from backend.bd.models import (
    Attendance,
    KpiMetricGroup,
    KpiMetricGroupRule,
    KpiMetric,
    KpiResult,
    KpiRule,
    KpiPayoutBatch,
    KpiPayoutItem,
    KpiMetricGroupPlanFact,
    KpiMetricGroupPlanPreference,
    KpiPlanFact,
    KpiPlanPreference,
    PayrollAdjustment,
    PayrollAdjustmentType,
    Position,
    User,
    user_restaurants,
)
from backend.schemas import (
    KpiMetricGroupCreate,
    KpiMetricGroupListResponse,
    KpiMetricGroupPublic,
    KpiMetricGroupRuleCreate,
    KpiMetricGroupRuleListResponse,
    KpiMetricGroupRulePublic,
    KpiMetricGroupRuleUpdate,
    KpiMetricGroupUpdate,
    KpiMetricGroupPlanFactCreate,
    KpiMetricGroupPlanFactPublic,
    KpiMetricGroupPlanFactListResponse,
    KpiMetricGroupPlanFactBulkItem,
    KpiMetricGroupPlanFactBulkResponse,
    KpiMetricGroupPlanPreferenceCreate,
    KpiMetricGroupPlanPreferencePublic,
    KpiMetricGroupPlanPreferenceListResponse,
    KpiMetricCreate,
    KpiMetricListResponse,
    KpiMetricPublic,
    KpiMetricUpdate,
    KpiResultCreate,
    KpiResultListResponse,
    KpiResultPublic,
    KpiResultStatus,
    KpiResultUpdate,
    KpiRuleCreate,
    KpiRuleListResponse,
    KpiRulePublic,
    KpiRuleUpdate,
    KpiThresholdType,
    KpiPayoutPreviewRequest,
    KpiPayoutPreviewByMetricRequest,
    KpiPayoutItemUpdate,
    KpiPayoutPostRequest,
    KpiPayoutBatchPublic,
    KpiPayoutBatchListResponse,
    KpiPayoutItemPublic,
    KpiPlanFactCreate,
    KpiPlanFactUpdate,
    KpiPlanFactPublic,
    KpiPlanFactListResponse,
    KpiPlanFactBulkItem,
    KpiPlanFactBulkResponse,
    KpiPlanPreferenceCreate,
    KpiPlanPreferencePublic,
    KpiPlanPreferenceListResponse,
)
from backend.services.payroll_calculations import calc_amounts as calc_payroll_amounts
from backend.services.payroll_calculations import resolve_rate as resolve_payroll_rate
from backend.services.reference_cache import cached_reference_data, invalidate_reference_scope

try:  # pragma: no cover - shared dependency injection fallback
    from backend.utils import get_current_user
    from backend.services.permissions import (
        PermissionCode,
        has_permission,
        has_global_access,
    )
except Exception:  # pragma: no cover
    from fastapi.security import OAuth2PasswordBearer
    from jose import JWTError, jwt
    import os

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")
    SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "CHANGE_ME"
    ALGORITHM = "HS256"

    def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            sub = payload.get("sub")
            if not sub:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            user = db.query(User).get(int(sub))
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
            if user.fired:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь уволен")
            return user
        except JWTError:  # pragma: no cover - fallback branch
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    class PermissionCode:
        KPI_VIEW = "kpi.view"
        KPI_MANAGE = "kpi.manage"
        KPI_METRICS_VIEW = "kpi.metrics.view"
        KPI_METRICS_MANAGE = "kpi.metrics.manage"
        KPI_METRIC_GROUPS_VIEW = "kpi.metric_groups.view"
        KPI_METRIC_GROUPS_MANAGE = "kpi.metric_groups.manage"
        KPI_RULES_ASSIGN = "kpi.rules.assign"
        KPI_FACTS_VIEW = "kpi.facts.view"
        KPI_FACTS_MANAGE = "kpi.facts.manage"
        KPI_RESULTS_VIEW = "kpi.results.view"
        KPI_PAYOUTS_VIEW = "kpi.payouts.view"
        KPI_PAYOUTS_MANAGE = "kpi.payouts.manage"

    def ensure_permissions(user: User, *codes: str) -> None:
        return

    def has_permission(user: User, code: str) -> bool:
        return True

    def has_global_access(user: User) -> bool:
        return True


router = APIRouter(prefix="/kpi", tags=["KPI"])

KPI_BONUS_ADJUSTMENT_NAME = "KPI бонус"
KPI_PENALTY_ADJUSTMENT_NAME = "KPI штраф"
KPI_SECTION_METRICS_PERMISSION_CODE = "sections.kpi.metrics"
KPI_SECTION_PLAN_FACT_PERMISSION_CODE = "sections.kpi.plan_fact"
KPI_SECTION_FACTS_PERMISSION_CODE = "sections.kpi.facts"
KPI_SECTION_PAYOUTS_PERMISSION_CODE = "sections.kpi.payouts"
KPI_SECTION_PERMISSION_CODES = (
    KPI_SECTION_METRICS_PERMISSION_CODE,
    KPI_SECTION_PLAN_FACT_PERMISSION_CODE,
    KPI_SECTION_FACTS_PERMISSION_CODE,
    KPI_SECTION_PAYOUTS_PERMISSION_CODE,
)
KPI_METRICS_VIEW_PERMISSION_CODES = (PermissionCode.KPI_METRICS_VIEW,)
KPI_METRICS_MANAGE_PERMISSION_CODES = (PermissionCode.KPI_METRICS_MANAGE,)
KPI_METRIC_GROUPS_VIEW_PERMISSION_CODES = (PermissionCode.KPI_METRIC_GROUPS_VIEW,)
KPI_METRIC_GROUPS_MANAGE_PERMISSION_CODES = (PermissionCode.KPI_METRIC_GROUPS_MANAGE,)
KPI_RULES_ASSIGN_PERMISSION_CODES = (PermissionCode.KPI_RULES_ASSIGN,)
KPI_FACTS_VIEW_PERMISSION_CODES = (PermissionCode.KPI_FACTS_VIEW,)
KPI_FACTS_MANAGE_PERMISSION_CODES = (PermissionCode.KPI_FACTS_MANAGE,)
KPI_RESULTS_VIEW_PERMISSION_CODES = (PermissionCode.KPI_RESULTS_VIEW,)
KPI_PAYOUTS_VIEW_PERMISSION_CODES = (PermissionCode.KPI_PAYOUTS_VIEW,)
KPI_PAYOUTS_MANAGE_PERMISSION_CODES = (PermissionCode.KPI_PAYOUTS_MANAGE,)
KPI_METRIC_GROUPS_CACHE_SCOPE = "kpi:metric_groups"
KPI_METRICS_CACHE_SCOPE = "kpi:metrics"
KPI_PLAN_PREFERENCES_CACHE_SCOPE = "kpi:plan_preferences"
KPI_REFERENCE_CACHE_TTL_SECONDS = 45


def _normalize_role_key(value: Optional[str]) -> str:
    """Normalize role name into a stable key (ignore spaces, hyphens, casing)."""
    if not value:
        return ""
    return "".join(ch for ch in value.strip().lower() if ch.isalnum())


def _is_superadmin_role(user: User) -> bool:
    role_obj = getattr(user, "role", None)
    role_name = getattr(role_obj, "name", None) if role_obj is not None else None
    key = _normalize_role_key(role_name)
    return key in {"суперадмин", "superadmin"}


def _ensure_kpi_view_access(
    user: User,
    *view_codes: str,
    section_codes: tuple[str, ...] = (),
    detail: str,
) -> None:
    if _is_superadmin_role(user) or has_global_access(user):
        return
    allowed_codes = [
        *view_codes,
        *section_codes,
        PermissionCode.KPI_VIEW,
        PermissionCode.KPI_MANAGE,
    ]
    if any(has_permission(user, code) for code in allowed_codes):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _ensure_kpi_manage_access(user: User, *manage_codes: str, detail: str) -> None:
    if _is_superadmin_role(user) or has_global_access(user):
        return
    allowed_codes = [
        *manage_codes,
        PermissionCode.KPI_MANAGE,
    ]
    if any(has_permission(user, code) for code in allowed_codes):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _ensure_metric_groups_view(user: User) -> None:
    _ensure_kpi_view_access(
        user,
        *KPI_METRIC_GROUPS_VIEW_PERMISSION_CODES,
        *KPI_METRIC_GROUPS_MANAGE_PERMISSION_CODES,
        section_codes=(KPI_SECTION_METRICS_PERMISSION_CODE,),
        detail="Недостаточно прав для просмотра групп KPI",
    )


def _ensure_metric_groups_manage(user: User) -> None:
    _ensure_kpi_manage_access(
        user,
        *KPI_METRIC_GROUPS_MANAGE_PERMISSION_CODES,
        detail="Недостаточно прав для изменения групп KPI",
    )


def _ensure_metrics_view(user: User) -> None:
    _ensure_kpi_view_access(
        user,
        *KPI_METRICS_VIEW_PERMISSION_CODES,
        *KPI_METRICS_MANAGE_PERMISSION_CODES,
        *KPI_FACTS_VIEW_PERMISSION_CODES,
        *KPI_FACTS_MANAGE_PERMISSION_CODES,
        *KPI_RESULTS_VIEW_PERMISSION_CODES,
        *KPI_PAYOUTS_VIEW_PERMISSION_CODES,
        *KPI_PAYOUTS_MANAGE_PERMISSION_CODES,
        section_codes=KPI_SECTION_PERMISSION_CODES,
        detail="Недостаточно прав для просмотра показателей KPI",
    )


def _ensure_metrics_manage(user: User) -> None:
    _ensure_kpi_manage_access(
        user,
        *KPI_METRICS_MANAGE_PERMISSION_CODES,
        detail="Недостаточно прав для изменения показателей KPI",
    )


def _ensure_rules_view(user: User) -> None:
    _ensure_kpi_view_access(
        user,
        *KPI_RULES_ASSIGN_PERMISSION_CODES,
        *KPI_METRICS_VIEW_PERMISSION_CODES,
        *KPI_METRIC_GROUPS_VIEW_PERMISSION_CODES,
        section_codes=(KPI_SECTION_METRICS_PERMISSION_CODE,),
        detail="Недостаточно прав для просмотра правил KPI",
    )


def _ensure_rules_assign(user: User) -> None:
    _ensure_kpi_manage_access(
        user,
        *KPI_RULES_ASSIGN_PERMISSION_CODES,
        detail="Недостаточно прав для назначения правил KPI",
    )


def _ensure_facts_view(user: User) -> None:
    _ensure_kpi_view_access(
        user,
        *KPI_FACTS_VIEW_PERMISSION_CODES,
        *KPI_FACTS_MANAGE_PERMISSION_CODES,
        *KPI_RESULTS_VIEW_PERMISSION_CODES,
        section_codes=(
            KPI_SECTION_FACTS_PERMISSION_CODE,
            KPI_SECTION_PLAN_FACT_PERMISSION_CODE,
        ),
        detail="Недостаточно прав для просмотра фактических результатов KPI",
    )


def _ensure_facts_manage(user: User) -> None:
    _ensure_kpi_manage_access(
        user,
        *KPI_FACTS_MANAGE_PERMISSION_CODES,
        detail="Недостаточно прав для редактирования фактических результатов KPI",
    )


def _ensure_results_view(user: User) -> None:
    _ensure_kpi_view_access(
        user,
        *KPI_RESULTS_VIEW_PERMISSION_CODES,
        section_codes=(KPI_SECTION_PLAN_FACT_PERMISSION_CODE,),
        detail="Недостаточно прав для просмотра результатов KPI",
    )


def _ensure_payouts_view(user: User) -> None:
    _ensure_kpi_view_access(
        user,
        *KPI_PAYOUTS_VIEW_PERMISSION_CODES,
        *KPI_PAYOUTS_MANAGE_PERMISSION_CODES,
        section_codes=(KPI_SECTION_PAYOUTS_PERMISSION_CODE,),
        detail="Недостаточно прав для просмотра выплат KPI",
    )


def _ensure_payouts_manage(user: User) -> None:
    _ensure_kpi_manage_access(
        user,
        *KPI_PAYOUTS_MANAGE_PERMISSION_CODES,
        detail="Недостаточно прав для формирования выплат KPI",
    )


def _metric_public(metric: KpiMetric) -> KpiMetricPublic:
    return KpiMetricPublic.from_orm(metric)


def _metric_group_public(group: KpiMetricGroup) -> KpiMetricGroupPublic:
    return KpiMetricGroupPublic.from_orm(group)


def _normalize_plan_direction_value(value: object) -> str:
    if hasattr(value, "value"):
        return str(getattr(value, "value"))
    return str(value or "higher_better")


def _resolve_metric_rule_conditions(rule: KpiRule) -> tuple[str, str]:
    bonus_condition = str(getattr(rule, "bonus_condition", "gte") or "gte")
    penalty_condition = str(getattr(rule, "penalty_condition", "lte") or "lte")
    # Для правил KPI условия должны следовать направлению метрики.
    # Это позволяет корректно считать старые правила, сохраненные до фикса синхронизации.
    if {bonus_condition, penalty_condition}.issubset({"gte", "lte"}):
        plan_direction = _normalize_plan_direction_value(getattr(getattr(rule, "metric", None), "plan_direction", None))
        if plan_direction == "lower_better":
            return "lte", "gte"
        return "gte", "lte"
    return bonus_condition, penalty_condition


def _metric_group_rule_public(rule: KpiMetricGroupRule) -> KpiMetricGroupRulePublic:
    return KpiMetricGroupRulePublic.from_orm(rule)


def _rule_public(rule: KpiRule) -> KpiRulePublic:
    public = KpiRulePublic.from_orm(rule)
    bonus_condition, penalty_condition = _resolve_metric_rule_conditions(rule)
    return public.model_copy(
        update={
            "bonus_condition": bonus_condition,
            "penalty_condition": penalty_condition,
        },
    )


def _result_public(result: KpiResult) -> KpiResultPublic:
    return KpiResultPublic.from_orm(result)


def _plan_fact_public(entry: KpiPlanFact) -> KpiPlanFactPublic:
    return KpiPlanFactPublic.from_orm(entry)


def _plan_pref_public(entry: KpiPlanPreference) -> KpiPlanPreferencePublic:
    return KpiPlanPreferencePublic.from_orm(entry)


def _group_plan_fact_public(entry: KpiMetricGroupPlanFact) -> KpiMetricGroupPlanFactPublic:
    return KpiMetricGroupPlanFactPublic.from_orm(entry)


def _group_plan_pref_public(entry: KpiMetricGroupPlanPreference) -> KpiMetricGroupPlanPreferencePublic:
    return KpiMetricGroupPlanPreferencePublic.from_orm(entry)


def _normalize_restaurant_ids(value: Optional[Iterable[int]]) -> Optional[list[int]]:
    if value is None:
        return None
    normalized: list[int] = []
    for item in value:
        if item is None:
            continue
        try:
            normalized.append(int(item))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(normalized))


def _validate_metric_group_id(db: Session, group_id: Optional[int]) -> None:
    if group_id is None:
        return
    group = db.query(KpiMetricGroup.id).filter(KpiMetricGroup.id == int(group_id)).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Группа KPI не найдена")


def _normalize_metric_group_plan_target(value: Optional[float]) -> float:
    if value is None:
        return 100.0
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Некорректный целевой процент группы KPI")
    if normalized < 0 or normalized > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Целевой процент группы KPI должен быть в диапазоне от 0 до 100",
        )
    return normalized


def _normalize_metric_scale_fields(
    data: dict,
    *,
    existing_use_max_scale: Optional[bool] = None,
    existing_max_scale_value: Optional[Decimal] = None,
) -> None:
    use_max_scale = data.get("use_max_scale")
    if use_max_scale is None:
        use_max_scale = bool(existing_use_max_scale) if existing_use_max_scale is not None else False

    if not use_max_scale:
        if "use_max_scale" in data or "max_scale_value" in data:
            data["max_scale_value"] = None
        return

    max_scale_value = data.get("max_scale_value", existing_max_scale_value)
    if max_scale_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите максимальное значение шкалы",
        )

    if _decimal(max_scale_value) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Максимальное значение шкалы должно быть больше нуля",
        )


def _validate_metric_adjustment_types(
    db: Session,
    *,
    bonus_adjustment_type_id: Optional[int],
    penalty_adjustment_type_id: Optional[int],
) -> None:
    if bonus_adjustment_type_id is not None:
        bonus_type = db.query(PayrollAdjustmentType).get(int(bonus_adjustment_type_id))
        if not bonus_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тип выплаты не найден")
        if bonus_type.kind != "accrual":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Тип выплаты должен быть начислением (accrual)",
            )
    if penalty_adjustment_type_id is not None:
        penalty_type = db.query(PayrollAdjustmentType).get(int(penalty_adjustment_type_id))
        if not penalty_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тип удержания не найден")
        if penalty_type.kind != "deduction":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Тип удержания должен быть удержанием (deduction)",
            )


MONEY_QUANT = Decimal("0.01")


def _quantize_money(amount: Decimal) -> Decimal:
    return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _maybe_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _compare_value(value: Decimal, operator: str, threshold: Decimal) -> bool:
    if operator == "gt":
        return value > threshold
    if operator == "lt":
        return value < threshold
    if operator == "lte":
        return value <= threshold
    if operator == "eq":
        return value == threshold
    return value >= threshold


def _resolve_rate(
    user: User,
    position: Optional[Position],
    payment_mode: Optional[str],
    *,
    stats_rate: Optional[Decimal] = None,
) -> Decimal:
    # Keep the same rate resolution as in payroll statements/exports.
    return resolve_payroll_rate(user, position, payment_mode, stats_rate=stats_rate)


def _calc_effect_amount(
    effect_type: str,
    effect_value: Decimal,
    effect_base: str,
    *,
    base_amount: Decimal,
    hours_sum: Decimal,
    rate: Decimal,
) -> Decimal:
    if effect_type == "fixed":
        return _quantize_money(effect_value)
    if effect_type != "percent":
        return Decimal("0")
    if effect_base == "hours_sum":
        base = hours_sum * rate
    elif effect_base == "rate":
        base = rate
    elif effect_base == "salary":
        base = base_amount
    else:
        base = Decimal("0")
    return _quantize_money((base * effect_value) / Decimal("100"))


def _full_name(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    parts = [user.last_name or "", user.first_name or ""]
    name = " ".join(p for p in parts if p).strip()
    if name:
        return name
    return user.username


def _normalize_amount(amount: Decimal, kind: str) -> Decimal:
    value = abs(_decimal(amount))
    return -value if kind == "deduction" else value


def _resolve_item_amount(item: KpiPayoutItem) -> Decimal:
    bonus = _decimal(getattr(item, "bonus_amount", None))
    penalty = _decimal(getattr(item, "penalty_amount", None))
    if bonus > 0 and penalty > 0:
        return _quantize_money(bonus - penalty)
    if bonus > 0:
        return _quantize_money(bonus)
    if penalty > 0:
        return _quantize_money(penalty)
    return Decimal("0")


def _resolve_comparison_value(
    basis: str,
    plan_value: Optional[Decimal],
    fact_value: Optional[Decimal],
    *,
    plan_direction: str = "higher_better",
) -> Optional[Decimal]:
    if fact_value is None:
        return None
    if basis == "plan_percent":
        if plan_direction == "lower_better":
            if plan_value is None:
                return None
            if plan_value == 0:
                return Decimal("100") if fact_value == 0 else Decimal("0")
            if fact_value <= 0:
                return Decimal("100")
            raw_percent = (plan_value / fact_value) * Decimal("100")
            return max(Decimal("0"), raw_percent)
        if plan_value is None or plan_value == 0:
            return None
        raw_percent = (fact_value / plan_value) * Decimal("100")
        return max(Decimal("0"), raw_percent)
    if basis == "plan_delta_percent":
        if plan_value is None or plan_value == 0:
            return None
        delta = ((fact_value - plan_value) / plan_value) * Decimal("100")
        return -delta if plan_direction == "lower_better" else delta
    return fact_value


def _find_adjustment_type(db: Session, name: str, kind: str) -> Optional[PayrollAdjustmentType]:
    return (
        db.query(PayrollAdjustmentType)
        .filter(
            func.lower(PayrollAdjustmentType.name) == func.lower(name),
            PayrollAdjustmentType.kind == kind,
        )
        .first()
    )


def _payout_batch_brief_load_options():
    return (
        load_only(
            KpiPayoutBatch.id,
            KpiPayoutBatch.rule_id,
            KpiPayoutBatch.result_id,
            KpiPayoutBatch.restaurant_id,
            KpiPayoutBatch.position_id,
            KpiPayoutBatch.period_start,
            KpiPayoutBatch.period_end,
            KpiPayoutBatch.status,
            KpiPayoutBatch.comment,
            KpiPayoutBatch.created_at,
            KpiPayoutBatch.created_by_id,
            KpiPayoutBatch.posted_at,
            KpiPayoutBatch.posted_by_id,
        ),
    )


def _payout_batch_detail_load_options(*, include_rule_metric: bool = False):
    rule_loader = joinedload(KpiPayoutBatch.rule).load_only(KpiRule.id, KpiRule.metric_id)
    if include_rule_metric:
        rule_loader = rule_loader.joinedload(KpiRule.metric).load_only(
            KpiMetric.id,
            KpiMetric.bonus_adjustment_type_id,
            KpiMetric.penalty_adjustment_type_id,
        )
    return (
        *_payout_batch_brief_load_options(),
        rule_loader,
        selectinload(KpiPayoutBatch.items)
        .load_only(
            KpiPayoutItem.id,
            KpiPayoutItem.batch_id,
            KpiPayoutItem.user_id,
            KpiPayoutItem.restaurant_id,
            KpiPayoutItem.base_amount,
            KpiPayoutItem.bonus_amount,
            KpiPayoutItem.penalty_amount,
            KpiPayoutItem.bonus_enabled,
            KpiPayoutItem.penalty_enabled,
            KpiPayoutItem.manual,
            KpiPayoutItem.comment,
            KpiPayoutItem.calc_snapshot,
            KpiPayoutItem.bonus_adjustment_id,
            KpiPayoutItem.penalty_adjustment_id,
        )
        .joinedload(KpiPayoutItem.user)
        .load_only(
            User.id,
            User.username,
            User.first_name,
            User.last_name,
            User.staff_code,
        ),
    )


def _public_calc_snapshot(snapshot: Optional[dict]) -> Optional[dict]:
    if not isinstance(snapshot, dict):
        return None
    return {
        "hours_sum": snapshot.get("hours_sum"),
    }


def _public_calc_summary(snapshot: Optional[dict]) -> Optional[dict]:
    if not isinstance(snapshot, dict):
        return None
    return {
        "comparison_basis": snapshot.get("comparison_basis"),
        "plan_value": snapshot.get("plan_value"),
        "fact_value": snapshot.get("fact_value"),
        "comparison_value": snapshot.get("comparison_value"),
        "target_value": snapshot.get("target_value"),
        "bonus_condition": snapshot.get("bonus_condition"),
    }


def _batch_public(batch: KpiPayoutBatch, include_items: bool = False) -> KpiPayoutBatchPublic:
    items: list[KpiPayoutItemPublic] = []
    calc_summary: Optional[dict] = None
    if include_items:
        ordered_items = list(batch.items or [])
        if ordered_items:
            calc_summary = _public_calc_summary(ordered_items[0].calc_snapshot)
        for item in ordered_items:
            items.append(
                KpiPayoutItemPublic(
                    id=item.id,
                    user_id=item.user_id,
                    staff_code=getattr(item.user, "staff_code", None) if item.user else None,
                    full_name=_full_name(getattr(item, "user", None)),
                    base_amount=_decimal(item.base_amount),
                    amount=_resolve_item_amount(item),
                    bonus_amount=_decimal(item.bonus_amount),
                    penalty_amount=_decimal(item.penalty_amount),
                    bonus_enabled=bool(item.bonus_enabled),
                    penalty_enabled=bool(item.penalty_enabled),
                    manual=bool(item.manual),
                    comment=item.comment,
                    calc_snapshot=_public_calc_snapshot(item.calc_snapshot),
                )
            )
    return KpiPayoutBatchPublic(
        id=batch.id,
        rule_id=batch.rule_id,
        metric_id=batch.rule.metric_id,
        result_id=batch.result_id,
        restaurant_id=batch.restaurant_id,
        position_id=batch.position_id,
        period_start=batch.period_start,
        period_end=batch.period_end,
        status=batch.status,
        comment=batch.comment,
        created_at=batch.created_at,
        created_by_id=batch.created_by_id,
        posted_at=batch.posted_at,
        posted_by_id=batch.posted_by_id,
        calc_summary=calc_summary,
        items=items,
    )


def _build_payout_batch(
    *,
    db: Session,
    rule: KpiRule,
    restaurant_id: int,
    position_id: int,
    period_start: date,
    period_end: date,
    plan_value: Optional[Decimal],
    fact_value: Decimal,
    comment: Optional[str],
    current_user: User,
    result_id: Optional[int] = None,
    skip_if_no_employees: bool = False,
) -> Optional[KpiPayoutBatch]:
    position = (
        db.query(Position)
        .options(joinedload(Position.payment_format))
        .filter(Position.id == position_id)
        .first()
    )
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Должность не найдена")

    payment_mode = getattr(getattr(position, "payment_format", None), "calculation_mode", None)

    # Attendance rows may have missing restaurant_id/position_id (manual input).
    # For KPI payouts we map:
    # - restaurant_id NULL -> user's workplace_restaurant_id
    # - position_id NULL -> user's current position_id
    # This matches the "default workplace/position" behavior expected in payroll statements.
    rest_attendance_filter = or_(
        Attendance.restaurant_id == restaurant_id,
        and_(
            Attendance.restaurant_id.is_(None),
            User.workplace_restaurant_id == restaurant_id,
        ),
    )
    position_attendance_filter = or_(
        Attendance.position_id == position_id,
        and_(
            Attendance.position_id.is_(None),
            User.position_id == position_id,
        ),
    )

    attendance_rows = (
        db.query(
            Attendance.user_id.label("user_id"),
            func.sum(func.coalesce(Attendance.duration_minutes, 0)).label("total_minutes_sum"),
            func.sum(
                case(
                    (rest_attendance_filter, func.coalesce(Attendance.duration_minutes, 0)),
                    else_=0,
                )
            ).label("rest_minutes_sum"),
            func.sum(
                case(
                    (rest_attendance_filter, func.coalesce(Attendance.night_minutes, 0)),
                    else_=0,
                )
            ).label("rest_night_sum"),
            func.max(
                case(
                    (rest_attendance_filter, Attendance.rate),
                    else_=None,
                )
            ).label("rest_rate_value"),
        )
        .join(User, User.id == Attendance.user_id)
        .filter(Attendance.close_date.isnot(None))
        .filter(Attendance.open_date >= period_start)
        .filter(Attendance.open_date <= period_end)
        .filter(position_attendance_filter)
    )
    if rule.employee_id:
        attendance_rows = attendance_rows.filter(Attendance.user_id == rule.employee_id)
    attendance_rows = attendance_rows.group_by(Attendance.user_id).all()

    rest_minutes_map = {row.user_id: int(row.rest_minutes_sum or 0) for row in attendance_rows}
    rest_night_minutes_map = {row.user_id: int(row.rest_night_sum or 0) for row in attendance_rows}
    rest_rate_map = {row.user_id: _maybe_decimal(getattr(row, "rest_rate_value", None)) for row in attendance_rows}
    total_minutes_map = {row.user_id: int(row.total_minutes_sum or 0) for row in attendance_rows}
    attendance_user_ids = {
        row.user_id
        for row in attendance_rows
        if int(row.rest_minutes_sum or 0) > 0
    }

    restaurant_user_ids: set[int] = set()
    if not rule.employee_id:
        users_query = (
            db.query(User.id)
            .outerjoin(user_restaurants, user_restaurants.c.user_id == User.id)
            .filter(User.position_id == position_id)
            .filter(
                or_(
                    user_restaurants.c.restaurant_id == restaurant_id,
                    User.workplace_restaurant_id == restaurant_id,
                )
            )
        )

        if payment_mode == "fixed":
            # Для fixed сотрудника уволенного в текущем месяце оставляем в списке
            # (как в ведомостях) даже если смен может не быть.
            fired_in_period = and_(
                User.fired.is_(True),
                User.fire_date.isnot(None),
                User.fire_date >= period_start,
                User.fire_date <= period_end,
            )
            users_query = users_query.filter(or_(User.fired.is_(False), fired_in_period))
        else:
            users_query = users_query.filter(User.fired.is_(False))

        restaurant_user_ids = {row[0] for row in users_query.distinct().all()}

    if rule.employee_id:
        candidate_user_ids = {rule.employee_id}
    else:
        candidate_user_ids = set(attendance_user_ids) | set(restaurant_user_ids)

    if not candidate_user_ids:
        if skip_if_no_employees:
            return None
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет сотрудников для выплаты")

    users = (
        db.query(User)
        .options(joinedload(User.position))
        .filter(User.id.in_(candidate_user_ids))
        .all()
    )
    user_map = {user.id: user for user in users}

    comparison_basis = str(rule.comparison_basis)
    if comparison_basis in ("plan_percent", "plan_delta_percent") and (plan_value is None or plan_value == 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет планового значения для расчета",
        )
    plan_direction = str(getattr(rule.metric, "plan_direction", "higher_better") or "higher_better")
    comparison_value = _resolve_comparison_value(
        comparison_basis,
        plan_value,
        fact_value,
        plan_direction=plan_direction,
    )

    target_value = _decimal(rule.target_value)
    warning_value = _decimal(rule.warning_value if str(rule.threshold_type) == "dual" else rule.target_value)
    bonus_condition, penalty_condition = _resolve_metric_rule_conditions(rule)

    bonus_applies = (
        rule.bonus_type != "none"
        and comparison_value is not None
        and _compare_value(comparison_value, bonus_condition, target_value)
    )
    penalty_applies = (
        rule.penalty_type != "none"
        and comparison_value is not None
        and _compare_value(comparison_value, penalty_condition, warning_value)
    )
    if bonus_applies and penalty_applies:
        penalty_applies = False

    batch = KpiPayoutBatch(
        rule_id=rule.id,
        result_id=result_id,
        restaurant_id=restaurant_id,
        position_id=position_id,
        period_start=period_start,
        period_end=period_end,
        status="draft",
        comment=comment,
        created_by_id=current_user.id,
    )

    hours_per_shift = (
        _decimal(getattr(position, "hours_per_shift", None))
        if getattr(position, "hours_per_shift", None) is not None
        else None
    )
    monthly_shift_norm = (
        _decimal(getattr(position, "monthly_shift_norm", None))
        if getattr(position, "monthly_shift_norm", None) is not None
        else None
    )
    night_enabled = bool(getattr(position, "night_bonus_enabled", False))
    night_percent = _decimal(getattr(position, "night_bonus_percent", None))

    for user_id in candidate_user_ids:
        user = user_map.get(user_id)
        if not user:
            continue

        rest_minutes = rest_minutes_map.get(user_id, 0)
        rest_night_minutes = rest_night_minutes_map.get(user_id, 0)
        total_minutes = total_minutes_map.get(user_id, 0)
        hours_sum = Decimal(rest_minutes) / Decimal(60) if rest_minutes else Decimal("0")
        night_hours = Decimal(rest_night_minutes) / Decimal(60) if rest_night_minutes else Decimal("0")

        stats_rate = rest_rate_map.get(user_id)
        rate = _resolve_rate(user, position, payment_mode, stats_rate=stats_rate)
        base_amount = Decimal("0")
        fact_shifts = None
        night_bonus = Decimal("0")
        hours_total = Decimal("0")
        if payment_mode == "fixed":
            if total_minutes > 0:
                ratio = Decimal(rest_minutes) / Decimal(total_minutes)
                base_amount = _quantize_money(rate * ratio)
            else:
                # Если нет часов, используем полную ставку для фиксированной оплаты
                base_amount = _quantize_money(rate)
        else:
            base_calc, fact_shifts, night_bonus, hours_total = calc_payroll_amounts(
                rate=rate,
                payment_mode=payment_mode,
                fact_hours=hours_sum,
                hours_per_shift=hours_per_shift,
                monthly_shift_norm=monthly_shift_norm,
                night_hours=night_hours,
                night_bonus_enabled=night_enabled,
                night_bonus_percent=night_percent,
                salary_factor=Decimal("1"),
            )
            # В KPI базой считаем "Итого за часы" как в ведомостях (base + night bonus).
            base_amount = hours_total if hours_total is not None else base_calc

        # KPI начисления считаем от "Итого за часы" (как в ведомостях).
        effect_base = "salary"

        bonus_amount = (
            _calc_effect_amount(
                str(rule.bonus_type),
                _decimal(rule.bonus_value),
                effect_base,
                base_amount=base_amount,
                hours_sum=hours_sum,
                rate=rate,
            )
            if bonus_applies
            else Decimal("0")
        )
        penalty_amount = (
            _calc_effect_amount(
                str(rule.penalty_type),
                _decimal(rule.penalty_value),
                effect_base,
                base_amount=base_amount,
                hours_sum=hours_sum,
                rate=rate,
            )
            if penalty_applies
            else Decimal("0")
        )

        batch.items.append(
            KpiPayoutItem(
                user_id=user_id,
                restaurant_id=restaurant_id,
                base_amount=base_amount,
                bonus_amount=bonus_amount,
                penalty_amount=penalty_amount,
                bonus_enabled=bool(bonus_applies),
                penalty_enabled=bool(penalty_applies),
                manual=False,
                calc_snapshot={
                    "fact_value": float(fact_value) if fact_value is not None else None,
                    "plan_value": float(plan_value) if plan_value is not None else None,
                    "comparison_basis": comparison_basis,
                    "comparison_value": float(comparison_value) if comparison_value is not None else None,
                    "target_value": float(target_value),
                    "warning_value": float(warning_value),
                    "bonus_condition": bonus_condition,
                    "penalty_condition": penalty_condition,
                    "bonus_type": str(rule.bonus_type),
                    "penalty_type": str(rule.penalty_type),
                    "bonus_base": effect_base,
                    "penalty_base": effect_base,
                    "base_amount": float(base_amount),
                    "hours_sum": float(hours_sum),
                    "night_hours": float(night_hours),
                    "night_bonus": float(night_bonus),
                    "fact_shifts": float(fact_shifts) if fact_shifts is not None else None,
                    "rate": float(rate),
                    "stats_rate": float(stats_rate) if stats_rate is not None else None,
                    "rest_minutes": rest_minutes,
                    "rest_night_minutes": rest_night_minutes,
                    "total_minutes": total_minutes,
                    "payment_mode": payment_mode,
                },
            )
        )

    if not batch.items:
        if skip_if_no_employees:
            return None
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет сотрудников для выплаты")

    db.add(batch)
    db.commit()
    db.refresh(batch)
    batch = (
        db.query(KpiPayoutBatch)
        .options(*_payout_batch_detail_load_options())
        .filter(KpiPayoutBatch.id == batch.id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout batch not found after creation")
    return batch

@router.get("/metric-groups", response_model=KpiMetricGroupListResponse)
def list_metric_groups(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiMetricGroupListResponse:
    _ensure_metric_groups_view(current_user)

    def _load_groups() -> dict:
        items = db.query(KpiMetricGroup).order_by(KpiMetricGroup.name.asc()).all()
        response = KpiMetricGroupListResponse(total=len(items), items=[_metric_group_public(item) for item in items])
        return response.model_dump(mode="json")

    payload = cached_reference_data(
        KPI_METRIC_GROUPS_CACHE_SCOPE,
        "all",
        _load_groups,
        ttl_seconds=KPI_REFERENCE_CACHE_TTL_SECONDS,
    )
    return KpiMetricGroupListResponse.model_validate(payload)


@router.post("/metric-groups", response_model=KpiMetricGroupPublic, status_code=status.HTTP_201_CREATED)
def create_metric_group(
    payload: KpiMetricGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiMetricGroupPublic:
    _ensure_metric_groups_manage(current_user)
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Укажите название группы KPI")

    existing = db.query(KpiMetricGroup).filter(func.lower(KpiMetricGroup.name) == func.lower(name)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Группа KPI с таким названием уже существует")

    group_data = {
        "use_max_scale": payload.use_max_scale,
        "max_scale_value": payload.max_scale_value,
    }
    _normalize_metric_scale_fields(group_data)
    group = KpiMetricGroup(
        name=name,
        description=(payload.description or "").strip() or None,
        unit=(payload.unit or "").strip() or None,
        use_max_scale=group_data["use_max_scale"],
        max_scale_value=group_data.get("max_scale_value"),
        plan_direction=_normalize_plan_direction_value(payload.plan_direction),
        plan_target_percent=_normalize_metric_group_plan_target(payload.plan_target_percent),
        bonus_adjustment_type_id=payload.bonus_adjustment_type_id,
        penalty_adjustment_type_id=payload.penalty_adjustment_type_id,
    )
    _validate_metric_adjustment_types(
        db,
        bonus_adjustment_type_id=payload.bonus_adjustment_type_id,
        penalty_adjustment_type_id=payload.penalty_adjustment_type_id,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    invalidate_reference_scope(KPI_METRIC_GROUPS_CACHE_SCOPE)
    invalidate_reference_scope(KPI_METRICS_CACHE_SCOPE)
    return _metric_group_public(group)


@router.patch("/metric-groups/{group_id}", response_model=KpiMetricGroupPublic)
def update_metric_group(
    group_id: int,
    payload: KpiMetricGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiMetricGroupPublic:
    _ensure_metric_groups_manage(current_user)
    group = db.query(KpiMetricGroup).filter(KpiMetricGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Группа KPI не найдена")

    data = payload.dict(exclude_unset=True)
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Укажите название группы KPI")
        conflict = (
            db.query(KpiMetricGroup)
            .filter(func.lower(KpiMetricGroup.name) == func.lower(name), KpiMetricGroup.id != group.id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Группа KPI с таким названием уже существует",
            )
        group.name = name
    if "description" in data:
        group.description = (data.get("description") or "").strip() or None
    if "unit" in data:
        group.unit = (data.get("unit") or "").strip() or None
    if "use_max_scale" in data or "max_scale_value" in data:
        scale_data = {
            "use_max_scale": data.get("use_max_scale", group.use_max_scale),
            "max_scale_value": data.get("max_scale_value", group.max_scale_value),
        }
        _normalize_metric_scale_fields(
            scale_data,
            existing_use_max_scale=group.use_max_scale,
            existing_max_scale_value=group.max_scale_value,
        )
        group.use_max_scale = scale_data.get("use_max_scale", group.use_max_scale)
        group.max_scale_value = scale_data.get("max_scale_value")
    if "plan_direction" in data:
        group.plan_direction = _normalize_plan_direction_value(data.get("plan_direction"))
    if "plan_target_percent" in data:
        group.plan_target_percent = _normalize_metric_group_plan_target(data.get("plan_target_percent"))
    if "bonus_adjustment_type_id" in data or "penalty_adjustment_type_id" in data:
        _validate_metric_adjustment_types(
            db,
            bonus_adjustment_type_id=data.get("bonus_adjustment_type_id", group.bonus_adjustment_type_id),
            penalty_adjustment_type_id=data.get("penalty_adjustment_type_id", group.penalty_adjustment_type_id),
        )
    if "bonus_adjustment_type_id" in data:
        group.bonus_adjustment_type_id = data.get("bonus_adjustment_type_id")
    if "penalty_adjustment_type_id" in data:
        group.penalty_adjustment_type_id = data.get("penalty_adjustment_type_id")

    db.commit()
    db.refresh(group)
    invalidate_reference_scope(KPI_METRIC_GROUPS_CACHE_SCOPE)
    invalidate_reference_scope(KPI_METRICS_CACHE_SCOPE)
    return _metric_group_public(group)


@router.delete("/metric-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_metric_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _ensure_metric_groups_manage(current_user)
    group = db.query(KpiMetricGroup).filter(KpiMetricGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Группа KPI не найдена")

    db.delete(group)
    db.commit()
    invalidate_reference_scope(KPI_METRIC_GROUPS_CACHE_SCOPE)
    invalidate_reference_scope(KPI_METRICS_CACHE_SCOPE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/metrics", response_model=KpiMetricListResponse)
def list_metrics(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    is_active: Optional[bool] = Query(None),
) -> KpiMetricListResponse:
    _ensure_metrics_view(current_user)
    cache_key = (
        "all" if is_active is None else bool(is_active),
    )

    def _load_metrics() -> dict:
        query = db.query(KpiMetric).options(joinedload(KpiMetric.group))
        if is_active is not None:
            query = query.filter(KpiMetric.is_active == is_active)
        items = query.order_by(KpiMetric.name.asc()).all()
        response = KpiMetricListResponse(total=len(items), items=[_metric_public(item) for item in items])
        return response.model_dump(mode="json")

    payload = cached_reference_data(
        KPI_METRICS_CACHE_SCOPE,
        cache_key,
        _load_metrics,
        ttl_seconds=KPI_REFERENCE_CACHE_TTL_SECONDS,
    )
    return KpiMetricListResponse.model_validate(payload)


@router.post("/metrics", response_model=KpiMetricPublic, status_code=status.HTTP_201_CREATED)
def create_metric(
    payload: KpiMetricCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiMetricPublic:
    _ensure_metrics_manage(current_user)

    existing = (
        db.query(KpiMetric)
        .filter(func.lower(KpiMetric.code) == func.lower(payload.code))
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Metric code already exists")

    data = payload.dict()
    _validate_metric_adjustment_types(
        db,
        bonus_adjustment_type_id=data.get("bonus_adjustment_type_id"),
        penalty_adjustment_type_id=data.get("penalty_adjustment_type_id"),
    )
    _validate_metric_group_id(db, data.get("group_id"))
    if data.get("all_restaurants"):
        data["restaurant_ids"] = None
    elif "restaurant_ids" in data:
        data["restaurant_ids"] = _normalize_restaurant_ids(data.get("restaurant_ids"))
    _normalize_metric_scale_fields(data)

    metric = KpiMetric(**data)
    db.add(metric)
    db.commit()
    db.refresh(metric)
    invalidate_reference_scope(KPI_METRICS_CACHE_SCOPE)
    return _metric_public(metric)


@router.patch("/metrics/{metric_id}", response_model=KpiMetricPublic)
def update_metric(
    metric_id: int,
    payload: KpiMetricUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiMetricPublic:
    _ensure_metrics_manage(current_user)

    metric = db.query(KpiMetric).filter(KpiMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metric not found")

    data = payload.dict(exclude_unset=True)
    _validate_metric_adjustment_types(
        db,
        bonus_adjustment_type_id=data.get("bonus_adjustment_type_id"),
        penalty_adjustment_type_id=data.get("penalty_adjustment_type_id"),
    )
    if "group_id" in data:
        _validate_metric_group_id(db, data.get("group_id"))
    new_code = data.get("code")
    if new_code:
        conflict = (
            db.query(KpiMetric)
            .filter(func.lower(KpiMetric.code) == func.lower(new_code), KpiMetric.id != metric.id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Metric code already exists")

    if "all_restaurants" in data and data.get("all_restaurants"):
        data["restaurant_ids"] = None
    elif "restaurant_ids" in data:
        data["restaurant_ids"] = _normalize_restaurant_ids(data.get("restaurant_ids"))
    _normalize_metric_scale_fields(
        data,
        existing_use_max_scale=bool(metric.use_max_scale),
        existing_max_scale_value=_maybe_decimal(metric.max_scale_value),
    )

    for field, value in data.items():
        setattr(metric, field, value)

    db.commit()
    db.refresh(metric)
    invalidate_reference_scope(KPI_METRICS_CACHE_SCOPE)
    return _metric_public(metric)


@router.delete("/metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_metric(
    metric_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _ensure_metrics_manage(current_user)

    metric = db.query(KpiMetric).filter(KpiMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metric not found")

    db.delete(metric)
    db.commit()
    invalidate_reference_scope(KPI_METRICS_CACHE_SCOPE)
    invalidate_reference_scope(KPI_PLAN_PREFERENCES_CACHE_SCOPE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/plan-preferences", response_model=KpiPlanPreferenceListResponse)
def list_plan_preferences(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    metric_id: Optional[int] = Query(None),
) -> KpiPlanPreferenceListResponse:
    _ensure_metrics_view(current_user)
    cache_key = (
        int(metric_id) if metric_id is not None else "all",
    )

    def _load_preferences() -> dict:
        query = db.query(KpiPlanPreference)
        if metric_id is not None:
            query = query.filter(KpiPlanPreference.metric_id == metric_id)
        items = query.order_by(KpiPlanPreference.metric_id.asc()).all()
        response = KpiPlanPreferenceListResponse(
            total=len(items),
            items=[_plan_pref_public(item) for item in items],
        )
        return response.model_dump(mode="json")

    payload = cached_reference_data(
        KPI_PLAN_PREFERENCES_CACHE_SCOPE,
        cache_key,
        _load_preferences,
        ttl_seconds=KPI_REFERENCE_CACHE_TTL_SECONDS,
    )
    return KpiPlanPreferenceListResponse.model_validate(payload)


@router.put("/plan-preferences", response_model=KpiPlanPreferencePublic)
def upsert_plan_preference(
    payload: KpiPlanPreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiPlanPreferencePublic:
    _ensure_metrics_manage(current_user)

    metric = db.query(KpiMetric).filter(KpiMetric.id == payload.metric_id).first()
    if not metric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metric not found")

    data = payload.dict(exclude_unset=True)
    entry = db.query(KpiPlanPreference).filter(KpiPlanPreference.metric_id == payload.metric_id).first()
    if entry:
        for field, value in data.items():
            setattr(entry, field, value)
    else:
        entry = KpiPlanPreference(**data)
        db.add(entry)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to save plan preferences")

    db.refresh(entry)
    invalidate_reference_scope(KPI_PLAN_PREFERENCES_CACHE_SCOPE)
    return _plan_pref_public(entry)


@router.get("/metric-group-plan-preferences", response_model=KpiMetricGroupPlanPreferenceListResponse)
def list_metric_group_plan_preferences(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    group_id: Optional[int] = Query(None),
) -> KpiMetricGroupPlanPreferenceListResponse:
    _ensure_metric_groups_view(current_user)

    query = db.query(KpiMetricGroupPlanPreference)
    if group_id is not None:
        query = query.filter(KpiMetricGroupPlanPreference.group_id == group_id)
    items = query.order_by(KpiMetricGroupPlanPreference.group_id.asc()).all()
    return KpiMetricGroupPlanPreferenceListResponse(
        total=len(items),
        items=[_group_plan_pref_public(item) for item in items],
    )


@router.put("/metric-group-plan-preferences", response_model=KpiMetricGroupPlanPreferencePublic)
def upsert_metric_group_plan_preference(
    payload: KpiMetricGroupPlanPreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiMetricGroupPlanPreferencePublic:
    _ensure_metric_groups_manage(current_user)

    group = db.query(KpiMetricGroup).filter(KpiMetricGroup.id == payload.group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Группа KPI не найдена")

    data = payload.dict(exclude_unset=True)
    entry = db.query(KpiMetricGroupPlanPreference).filter(KpiMetricGroupPlanPreference.group_id == payload.group_id).first()
    if entry:
        for field, value in data.items():
            setattr(entry, field, value)
    else:
        entry = KpiMetricGroupPlanPreference(**data)
        db.add(entry)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to save group plan preferences")

    db.refresh(entry)
    return _group_plan_pref_public(entry)


@router.get("/plan-fact", response_model=KpiPlanFactListResponse)
def list_plan_facts(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    metric_id: int = Query(...),
    restaurant_id: int = Query(...),
    year: int = Query(..., ge=2000, le=2100),
) -> KpiPlanFactListResponse:
    _ensure_facts_view(current_user)

    items = (
        db.query(KpiPlanFact)
        .options(joinedload(KpiPlanFact.metric).joinedload(KpiMetric.group))
        .filter(
            KpiPlanFact.metric_id == metric_id,
            KpiPlanFact.restaurant_id == restaurant_id,
            KpiPlanFact.year == year,
        )
        .order_by(KpiPlanFact.month.asc())
        .all()
    )
    return KpiPlanFactListResponse(total=len(items), items=[_plan_fact_public(item) for item in items])


@router.get("/plan-fact/bulk", response_model=KpiPlanFactBulkResponse)
def list_plan_facts_bulk(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    year: int = Query(..., ge=2000, le=2100),
    restaurant_id: Optional[int] = Query(None),
    metric_id: Optional[int] = Query(None),
) -> KpiPlanFactBulkResponse:
    _ensure_facts_view(current_user)

    query = db.query(KpiPlanFact).filter(KpiPlanFact.year == year, KpiPlanFact.restaurant_id.isnot(None))
    if restaurant_id is not None:
        query = query.filter(KpiPlanFact.restaurant_id == restaurant_id)
    if metric_id is not None:
        query = query.filter(KpiPlanFact.metric_id == metric_id)

    items = query.order_by(
        KpiPlanFact.metric_id.asc(),
        KpiPlanFact.restaurant_id.asc(),
        KpiPlanFact.month.asc(),
    ).all()
    return KpiPlanFactBulkResponse(total=len(items), items=[KpiPlanFactBulkItem.from_orm(item) for item in items])


@router.put("/plan-fact", response_model=KpiPlanFactPublic)
def upsert_plan_fact(
    payload: KpiPlanFactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiPlanFactPublic:
    _ensure_facts_manage(current_user)

    fields_set = getattr(payload, "model_fields_set", set())
    if "plan_value" not in fields_set and "fact_value" not in fields_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет данных для обновления",
        )

    entry = (
        db.query(KpiPlanFact)
        .filter(
            KpiPlanFact.metric_id == payload.metric_id,
            KpiPlanFact.restaurant_id == payload.restaurant_id,
            KpiPlanFact.year == payload.year,
            KpiPlanFact.month == payload.month,
        )
        .first()
    )
    if entry:
        if "plan_value" in fields_set:
            entry.plan_value = payload.plan_value
        if "fact_value" in fields_set:
            entry.fact_value = payload.fact_value
    else:
        data = {
            "metric_id": payload.metric_id,
            "restaurant_id": payload.restaurant_id,
            "year": payload.year,
            "month": payload.month,
        }
        if "plan_value" in fields_set:
            data["plan_value"] = payload.plan_value
        if "fact_value" in fields_set:
            data["fact_value"] = payload.fact_value
        entry = KpiPlanFact(**data)
        db.add(entry)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to save plan/fact")

    db.refresh(entry)
    db.refresh(entry, attribute_names=["metric"])
    return _plan_fact_public(entry)


@router.put("/plan-fact/bulk", response_model=KpiPlanFactBulkResponse)
def upsert_plan_facts_bulk(
    payload: List[KpiPlanFactCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiPlanFactBulkResponse:
    _ensure_facts_manage(current_user)

    if not payload:
        return KpiPlanFactBulkResponse(total=0, items=[])

    normalized_items: list[tuple[tuple[int, int, int, int], KpiPlanFactCreate, set[str]]] = []
    dedupe_map: dict[tuple[int, int, int, int], int] = {}
    for item in payload:
        fields_set = set(getattr(item, "model_fields_set", set()))
        if "plan_value" not in fields_set and "fact_value" not in fields_set:
            continue
        key = (item.metric_id, item.restaurant_id, item.year, item.month)
        if key in dedupe_map:
            idx = dedupe_map[key]
            normalized_items[idx] = (key, item, fields_set)
        else:
            dedupe_map[key] = len(normalized_items)
            normalized_items.append((key, item, fields_set))

    if not normalized_items:
        return KpiPlanFactBulkResponse(total=0, items=[])

    keys = [item[0] for item in normalized_items]
    existing_rows = (
        db.query(KpiPlanFact)
        .filter(
            tuple_(
                KpiPlanFact.metric_id,
                KpiPlanFact.restaurant_id,
                KpiPlanFact.year,
                KpiPlanFact.month,
            ).in_(keys)
        )
        .all()
    )
    existing_by_key = {
        (row.metric_id, row.restaurant_id, row.year, row.month): row
        for row in existing_rows
    }

    for key, item, fields_set in normalized_items:
        entry = existing_by_key.get(key)
        if entry:
            if "plan_value" in fields_set:
                entry.plan_value = item.plan_value
            if "fact_value" in fields_set:
                entry.fact_value = item.fact_value
            continue

        data = {
            "metric_id": item.metric_id,
            "restaurant_id": item.restaurant_id,
            "year": item.year,
            "month": item.month,
        }
        if "plan_value" in fields_set:
            data["plan_value"] = item.plan_value
        if "fact_value" in fields_set:
            data["fact_value"] = item.fact_value
        entry = KpiPlanFact(**data)
        db.add(entry)
        existing_by_key[key] = entry

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to save plan/fact")

    upserted_items = [
        KpiPlanFactBulkItem(
            metric_id=key[0],
            restaurant_id=key[1],
            year=key[2],
            month=key[3],
            plan_value=existing_by_key[key].plan_value,
            fact_value=existing_by_key[key].fact_value,
        )
        for key, *_ in normalized_items
    ]
    return KpiPlanFactBulkResponse(total=len(upserted_items), items=upserted_items)


@router.get("/metric-group-plan-fact", response_model=KpiMetricGroupPlanFactListResponse)
def list_metric_group_plan_facts(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    group_id: int = Query(...),
    restaurant_id: int = Query(...),
    year: int = Query(..., ge=2000, le=2100),
) -> KpiMetricGroupPlanFactListResponse:
    _ensure_facts_view(current_user)

    items = (
        db.query(KpiMetricGroupPlanFact)
        .options(joinedload(KpiMetricGroupPlanFact.group))
        .filter(
            KpiMetricGroupPlanFact.group_id == group_id,
            KpiMetricGroupPlanFact.restaurant_id == restaurant_id,
            KpiMetricGroupPlanFact.year == year,
        )
        .order_by(KpiMetricGroupPlanFact.month.asc())
        .all()
    )
    return KpiMetricGroupPlanFactListResponse(total=len(items), items=[_group_plan_fact_public(item) for item in items])


@router.get("/metric-group-plan-fact/bulk", response_model=KpiMetricGroupPlanFactBulkResponse)
def list_metric_group_plan_facts_bulk(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    year: int = Query(..., ge=2000, le=2100),
    restaurant_id: Optional[int] = Query(None),
    group_id: Optional[int] = Query(None),
) -> KpiMetricGroupPlanFactBulkResponse:
    _ensure_facts_view(current_user)

    query = db.query(KpiMetricGroupPlanFact).filter(
        KpiMetricGroupPlanFact.year == year,
        KpiMetricGroupPlanFact.restaurant_id.isnot(None),
    )
    if restaurant_id is not None:
        query = query.filter(KpiMetricGroupPlanFact.restaurant_id == restaurant_id)
    if group_id is not None:
        query = query.filter(KpiMetricGroupPlanFact.group_id == group_id)

    items = query.order_by(
        KpiMetricGroupPlanFact.group_id.asc(),
        KpiMetricGroupPlanFact.restaurant_id.asc(),
        KpiMetricGroupPlanFact.month.asc(),
    ).all()
    return KpiMetricGroupPlanFactBulkResponse(
        total=len(items),
        items=[KpiMetricGroupPlanFactBulkItem.from_orm(item) for item in items],
    )


@router.put("/metric-group-plan-fact", response_model=KpiMetricGroupPlanFactPublic)
def upsert_metric_group_plan_fact(
    payload: KpiMetricGroupPlanFactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiMetricGroupPlanFactPublic:
    _ensure_facts_manage(current_user)

    fields_set = getattr(payload, "model_fields_set", set())
    if "plan_value" not in fields_set and "fact_value" not in fields_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет данных для обновления")

    entry = (
        db.query(KpiMetricGroupPlanFact)
        .filter(
            KpiMetricGroupPlanFact.group_id == payload.group_id,
            KpiMetricGroupPlanFact.restaurant_id == payload.restaurant_id,
            KpiMetricGroupPlanFact.year == payload.year,
            KpiMetricGroupPlanFact.month == payload.month,
        )
        .first()
    )
    if entry:
        if "plan_value" in fields_set:
            entry.plan_value = payload.plan_value
        if "fact_value" in fields_set:
            entry.fact_value = payload.fact_value
    else:
        data = {
            "group_id": payload.group_id,
            "restaurant_id": payload.restaurant_id,
            "year": payload.year,
            "month": payload.month,
        }
        if "plan_value" in fields_set:
            data["plan_value"] = payload.plan_value
        if "fact_value" in fields_set:
            data["fact_value"] = payload.fact_value
        entry = KpiMetricGroupPlanFact(**data)
        db.add(entry)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to save group plan/fact")

    db.refresh(entry)
    db.refresh(entry, attribute_names=["group"])
    return _group_plan_fact_public(entry)


@router.put("/metric-group-plan-fact/bulk", response_model=KpiMetricGroupPlanFactBulkResponse)
def upsert_metric_group_plan_facts_bulk(
    payload: List[KpiMetricGroupPlanFactCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiMetricGroupPlanFactBulkResponse:
    _ensure_facts_manage(current_user)

    if not payload:
        return KpiMetricGroupPlanFactBulkResponse(total=0, items=[])

    normalized_items: list[tuple[tuple[int, int, int, int], KpiMetricGroupPlanFactCreate, set[str]]] = []
    dedupe_map: dict[tuple[int, int, int, int], int] = {}
    for item in payload:
        fields_set = set(getattr(item, "model_fields_set", set()))
        if "plan_value" not in fields_set and "fact_value" not in fields_set:
            continue
        key = (item.group_id, item.restaurant_id, item.year, item.month)
        if key in dedupe_map:
            idx = dedupe_map[key]
            normalized_items[idx] = (key, item, fields_set)
        else:
            dedupe_map[key] = len(normalized_items)
            normalized_items.append((key, item, fields_set))

    if not normalized_items:
        return KpiMetricGroupPlanFactBulkResponse(total=0, items=[])

    existing = (
        db.query(KpiMetricGroupPlanFact)
        .filter(
            tuple_(
                KpiMetricGroupPlanFact.group_id,
                KpiMetricGroupPlanFact.restaurant_id,
                KpiMetricGroupPlanFact.year,
                KpiMetricGroupPlanFact.month,
            ).in_([key for key, *_ in normalized_items]),
        )
        .all()
    )
    existing_by_key = {
        (item.group_id, item.restaurant_id, item.year, item.month): item
        for item in existing
    }

    for key, item, fields_set in normalized_items:
        entry = existing_by_key.get(key)
        if entry:
            if "plan_value" in fields_set:
                entry.plan_value = item.plan_value
            if "fact_value" in fields_set:
                entry.fact_value = item.fact_value
            continue

        data = {
            "group_id": item.group_id,
            "restaurant_id": item.restaurant_id,
            "year": item.year,
            "month": item.month,
        }
        if "plan_value" in fields_set:
            data["plan_value"] = item.plan_value
        if "fact_value" in fields_set:
            data["fact_value"] = item.fact_value
        entry = KpiMetricGroupPlanFact(**data)
        db.add(entry)
        existing_by_key[key] = entry

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to save group plan/fact")

    upserted_items = [
        KpiMetricGroupPlanFactBulkItem(
            group_id=key[0],
            restaurant_id=key[1],
            year=key[2],
            month=key[3],
            plan_value=existing_by_key[key].plan_value,
            fact_value=existing_by_key[key].fact_value,
        )
        for key, *_ in normalized_items
    ]
    return KpiMetricGroupPlanFactBulkResponse(total=len(upserted_items), items=upserted_items)


@router.get("/rules", response_model=KpiRuleListResponse)
def list_rules(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    metric_id: Optional[int] = Query(None),
    restaurant_id: Optional[int] = Query(None),
    position_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    period_from: Optional[date] = Query(None),
    period_to: Optional[date] = Query(None),
) -> KpiRuleListResponse:
    _ensure_rules_view(current_user)

    query = (
        db.query(KpiRule)
        .options(joinedload(KpiRule.metric).joinedload(KpiMetric.group))
        .order_by(KpiRule.period_start.desc(), KpiRule.id.desc())
    )
    if metric_id:
        query = query.filter(KpiRule.metric_id == metric_id)
    if restaurant_id:
        query = query.filter(KpiRule.restaurant_id == restaurant_id)
    if position_id:
        query = query.filter(KpiRule.position_id == position_id)
    if employee_id:
        query = query.filter(KpiRule.employee_id == employee_id)
    if is_active is not None:
        query = query.filter(KpiRule.is_active == is_active)
    if period_from:
        query = query.filter(KpiRule.period_end >= period_from)
    if period_to:
        query = query.filter(KpiRule.period_start <= period_to)

    items = query.all()
    return KpiRuleListResponse(total=len(items), items=[_rule_public(item) for item in items])


def _ensure_rule_threshold(threshold_type: KpiThresholdType, warning_value: Optional[Decimal]) -> None:
    if threshold_type == KpiThresholdType.DUAL and warning_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="warning_value is required for dual threshold rules",
        )


@router.post("/rules", response_model=KpiRulePublic, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: KpiRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiRulePublic:
    _ensure_rules_assign(current_user)
    data = payload.dict()
    if data.get("threshold_type") == KpiThresholdType.DUAL and data.get("warning_value") is None:
        data["warning_value"] = data.get("target_value")
    _ensure_rule_threshold(data.get("threshold_type"), data.get("warning_value"))

    rule = KpiRule(**data)
    db.add(rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A rule already exists for this scope")
    db.refresh(rule)
    db.refresh(rule, attribute_names=["metric"])
    return _rule_public(rule)


def _validate_rule_update(rule: KpiRule, data: dict) -> None:
    period_start = data.get("period_start", rule.period_start)
    period_end = data.get("period_end", rule.period_end)
    if period_start and period_end and period_end < period_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_end must be >= period_start")
    threshold_type = data.get("threshold_type", rule.threshold_type)
    target_value = data.get("target_value", rule.target_value)
    warning_value = data.get("warning_value", rule.warning_value)
    if threshold_type == KpiThresholdType.DUAL and warning_value is None:
        warning_value = target_value
        data["warning_value"] = warning_value
    _ensure_rule_threshold(threshold_type, warning_value)


@router.patch("/rules/{rule_id}", response_model=KpiRulePublic)
def update_rule(
    rule_id: int,
    payload: KpiRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiRulePublic:
    _ensure_rules_assign(current_user)

    rule = (
        db.query(KpiRule)
        .options(joinedload(KpiRule.metric).joinedload(KpiMetric.group))
        .filter(KpiRule.id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    data = payload.dict(exclude_unset=True)
    if not data:
        return _rule_public(rule)

    _validate_rule_update(rule, data)

    for field, value in data.items():
        setattr(rule, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A rule already exists for this scope")
    db.refresh(rule)
    db.refresh(rule, attribute_names=["metric"])
    return _rule_public(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _ensure_rules_assign(current_user)

    rule = db.query(KpiRule).filter(KpiRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    db.delete(rule)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/group-rules", response_model=KpiMetricGroupRuleListResponse)
def list_group_rules(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    group_id: Optional[int] = Query(None),
    restaurant_id: Optional[int] = Query(None),
    position_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    period_from: Optional[date] = Query(None),
    period_to: Optional[date] = Query(None),
) -> KpiMetricGroupRuleListResponse:
    _ensure_rules_view(current_user)

    query = (
        db.query(KpiMetricGroupRule)
        .options(joinedload(KpiMetricGroupRule.group))
        .order_by(KpiMetricGroupRule.period_start.desc(), KpiMetricGroupRule.id.desc())
    )
    if group_id:
        query = query.filter(KpiMetricGroupRule.group_id == group_id)
    if restaurant_id:
        query = query.filter(KpiMetricGroupRule.restaurant_id == restaurant_id)
    if position_id:
        query = query.filter(KpiMetricGroupRule.position_id == position_id)
    if employee_id:
        query = query.filter(KpiMetricGroupRule.employee_id == employee_id)
    if is_active is not None:
        query = query.filter(KpiMetricGroupRule.is_active == is_active)
    if period_from:
        query = query.filter(KpiMetricGroupRule.period_end >= period_from)
    if period_to:
        query = query.filter(KpiMetricGroupRule.period_start <= period_to)

    items = query.all()
    return KpiMetricGroupRuleListResponse(total=len(items), items=[_metric_group_rule_public(item) for item in items])


def _validate_group_rule_update(rule: KpiMetricGroupRule, data: dict) -> None:
    period_start = data.get("period_start", rule.period_start)
    period_end = data.get("period_end", rule.period_end)
    if period_start and period_end and period_end < period_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_end must be >= period_start")
    threshold_type = data.get("threshold_type", rule.threshold_type)
    target_value = data.get("target_value", rule.target_value)
    warning_value = data.get("warning_value", rule.warning_value)
    if threshold_type == KpiThresholdType.DUAL and warning_value is None:
        warning_value = target_value
        data["warning_value"] = warning_value
    _ensure_rule_threshold(threshold_type, warning_value)


@router.post("/group-rules", response_model=KpiMetricGroupRulePublic, status_code=status.HTTP_201_CREATED)
def create_group_rule(
    payload: KpiMetricGroupRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiMetricGroupRulePublic:
    _ensure_rules_assign(current_user)
    _validate_metric_group_id(db, payload.group_id)
    data = payload.dict()
    if data.get("threshold_type") == KpiThresholdType.DUAL and data.get("warning_value") is None:
        data["warning_value"] = data.get("target_value")
    _ensure_rule_threshold(data.get("threshold_type"), data.get("warning_value"))

    rule = KpiMetricGroupRule(**data)
    db.add(rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A rule already exists for this scope")
    db.refresh(rule)
    db.refresh(rule, attribute_names=["group"])
    return _metric_group_rule_public(rule)


@router.patch("/group-rules/{rule_id}", response_model=KpiMetricGroupRulePublic)
def update_group_rule(
    rule_id: int,
    payload: KpiMetricGroupRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiMetricGroupRulePublic:
    _ensure_rules_assign(current_user)

    rule = (
        db.query(KpiMetricGroupRule)
        .options(joinedload(KpiMetricGroupRule.group))
        .filter(KpiMetricGroupRule.id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    data = payload.dict(exclude_unset=True)
    if not data:
        return _metric_group_rule_public(rule)
    if "group_id" in data:
        _validate_metric_group_id(db, data.get("group_id"))

    _validate_group_rule_update(rule, data)

    for field, value in data.items():
        setattr(rule, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A rule already exists for this scope")
    db.refresh(rule)
    db.refresh(rule, attribute_names=["group"])
    return _metric_group_rule_public(rule)


@router.delete("/group-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _ensure_rules_assign(current_user)

    rule = db.query(KpiMetricGroupRule).filter(KpiMetricGroupRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    db.delete(rule)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/results", response_model=KpiResultListResponse)
def list_results(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    metric_id: Optional[int] = Query(None),
    restaurant_id: Optional[int] = Query(None),
    position_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    status_filter: Optional[KpiResultStatus] = Query(None, alias="status"),
    period_from: Optional[date] = Query(None),
    period_to: Optional[date] = Query(None),
) -> KpiResultListResponse:
    _ensure_results_view(current_user)

    query = (
        db.query(KpiResult)
        .options(joinedload(KpiResult.metric).joinedload(KpiMetric.group))
        .order_by(KpiResult.period_start.desc(), KpiResult.id.desc())
    )
    if metric_id:
        query = query.filter(KpiResult.metric_id == metric_id)
    if restaurant_id:
        query = query.filter(KpiResult.restaurant_id == restaurant_id)
    if position_id:
        query = query.filter(KpiResult.position_id == position_id)
    if employee_id:
        query = query.filter(KpiResult.employee_id == employee_id)
    if status_filter:
        query = query.filter(KpiResult.status == status_filter)
    if period_from:
        query = query.filter(KpiResult.period_end >= period_from)
    if period_to:
        query = query.filter(KpiResult.period_start <= period_to)

    items = query.all()
    return KpiResultListResponse(total=len(items), items=[_result_public(item) for item in items])


def _validate_result_update(result: KpiResult, data: dict) -> None:
    period_start = data.get("period_start", result.period_start)
    period_end = data.get("period_end", result.period_end)
    if period_start and period_end and period_end < period_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_end must be >= period_start")


@router.post("/results", response_model=KpiResultPublic, status_code=status.HTTP_201_CREATED)
def create_result(
    payload: KpiResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiResultPublic:
    _ensure_facts_manage(current_user)

    data = payload.dict()
    data["recorded_by_id"] = data.get("recorded_by_id") or current_user.id

    result = KpiResult(**data)
    db.add(result)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Result already recorded for this scope")
    db.refresh(result)
    db.refresh(result, attribute_names=["metric"])
    return _result_public(result)


@router.patch("/results/{result_id}", response_model=KpiResultPublic)
def update_result(
    result_id: int,
    payload: KpiResultUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiResultPublic:
    _ensure_facts_manage(current_user)

    result = (
        db.query(KpiResult)
        .options(joinedload(KpiResult.metric).joinedload(KpiMetric.group))
        .filter(KpiResult.id == result_id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    data = payload.dict(exclude_unset=True)
    if not data:
        return _result_public(result)

    _validate_result_update(result, data)

    if "recorded_by_id" not in data:
        data["recorded_by_id"] = result.recorded_by_id or current_user.id

    for field, value in data.items():
        setattr(result, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Result already recorded for this scope")
    db.refresh(result)
    db.refresh(result, attribute_names=["metric"])
    return _result_public(result)


@router.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _ensure_facts_manage(current_user)

    result = db.query(KpiResult).filter(KpiResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    db.delete(result)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----- KPI payouts ------------------------------------------------------------


@router.get("/payouts", response_model=KpiPayoutBatchListResponse)
def list_payout_batches(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rule_id: Optional[int] = Query(None),
    result_id: Optional[int] = Query(None),
    restaurant_id: Optional[int] = Query(None),
    position_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    period_from: Optional[date] = Query(None),
    period_to: Optional[date] = Query(None),
) -> KpiPayoutBatchListResponse:
    _ensure_payouts_view(current_user)
    query = (
        db.query(KpiPayoutBatch)
        .options(
            *_payout_batch_brief_load_options(),
            joinedload(KpiPayoutBatch.rule).load_only(KpiRule.id, KpiRule.metric_id),
        )
        .order_by(KpiPayoutBatch.created_at.desc(), KpiPayoutBatch.id.desc())
    )
    if rule_id:
        query = query.filter(KpiPayoutBatch.rule_id == rule_id)
    if result_id:
        query = query.filter(KpiPayoutBatch.result_id == result_id)
    if restaurant_id:
        query = query.filter(KpiPayoutBatch.restaurant_id == restaurant_id)
    if position_id:
        query = query.filter(KpiPayoutBatch.position_id == position_id)
    if status_filter:
        query = query.filter(KpiPayoutBatch.status == status_filter)
    if period_from:
        query = query.filter(KpiPayoutBatch.period_end >= period_from)
    if period_to:
        query = query.filter(KpiPayoutBatch.period_start <= period_to)
    items = query.all()
    return KpiPayoutBatchListResponse(
        total=len(items),
        items=[_batch_public(item, include_items=False) for item in items],
    )


@router.get("/payouts/bulk", response_model=KpiPayoutBatchListResponse)
def list_payout_batches_bulk(
    ids: List[int] = Query(default_factory=list),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiPayoutBatchListResponse:
    _ensure_payouts_view(current_user)

    ordered_ids: list[int] = []
    seen_ids: set[int] = set()
    for raw_id in ids or []:
        try:
            batch_id = int(raw_id)
        except Exception:
            continue
        if batch_id <= 0 or batch_id in seen_ids:
            continue
        seen_ids.add(batch_id)
        ordered_ids.append(batch_id)

    if not ordered_ids:
        return KpiPayoutBatchListResponse(total=0, items=[])
    if len(ordered_ids) > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many batch ids")

    rows = (
        db.query(KpiPayoutBatch)
        .options(*_payout_batch_detail_load_options())
        .filter(KpiPayoutBatch.id.in_(ordered_ids))
        .all()
    )
    rows_by_id = {int(row.id): row for row in rows if row.id is not None}
    ordered_rows = [rows_by_id[batch_id] for batch_id in ordered_ids if batch_id in rows_by_id]

    return KpiPayoutBatchListResponse(
        total=len(ordered_rows),
        items=[_batch_public(item, include_items=True) for item in ordered_rows],
    )


@router.get("/payouts/{batch_id}", response_model=KpiPayoutBatchPublic)
def get_payout_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiPayoutBatchPublic:
    _ensure_payouts_view(current_user)
    batch = (
        db.query(KpiPayoutBatch)
        .options(*_payout_batch_detail_load_options())
        .filter(KpiPayoutBatch.id == batch_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout batch not found")
    return _batch_public(batch, include_items=True)


@router.delete("/payouts/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payout_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _ensure_payouts_manage(current_user)

    batch = db.query(KpiPayoutBatch).filter(KpiPayoutBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout batch not found")
    if batch.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Можно удалить только черновик")

    db.delete(batch)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/payouts/{batch_id}/items/{item_id}", response_model=KpiPayoutBatchPublic)
def delete_payout_item(
    batch_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiPayoutBatchPublic:
    _ensure_payouts_manage(current_user)

    batch = (
        db.query(KpiPayoutBatch)
        .options(*_payout_batch_detail_load_options())
        .filter(KpiPayoutBatch.id == batch_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout batch not found")
    if batch.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payout batch is not editable")

    item = next((row for row in batch.items if row.id == item_id), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout item not found")

    db.delete(item)
    db.commit()

    # Reload (relationship collections can be stale after deletion)
    batch = (
        db.query(KpiPayoutBatch)
        .options(*_payout_batch_detail_load_options())
        .filter(KpiPayoutBatch.id == batch_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout batch not found")

    return _batch_public(batch, include_items=True)


@router.post("/payouts/preview", response_model=KpiPayoutBatchPublic, status_code=status.HTTP_201_CREATED)
def create_payout_preview(
    payload: KpiPayoutPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiPayoutBatchPublic:
    _ensure_payouts_manage(current_user)

    rule = (
        db.query(KpiRule)
        .options(joinedload(KpiRule.metric).joinedload(KpiMetric.group))
        .filter(KpiRule.id == payload.rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    result: Optional[KpiResult] = None
    restaurant_id: Optional[int] = None
    position_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None

    plan_value: Optional[Decimal] = None
    fact_value: Optional[Decimal] = None

    if payload.result_id is not None:
        result = (
            db.query(KpiResult)
            .options(joinedload(KpiResult.metric).joinedload(KpiMetric.group))
            .filter(KpiResult.id == payload.result_id)
            .first()
        )
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

        if rule.metric_id != result.metric_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rule metric does not match result metric",
            )
        if rule.restaurant_id and result.restaurant_id and rule.restaurant_id != result.restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rule restaurant does not match result restaurant",
            )
        if rule.position_id and result.position_id and rule.position_id != result.position_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rule position does not match result position",
            )

        restaurant_id = result.restaurant_id or rule.restaurant_id
        position_id = result.position_id or rule.position_id
        period_start = result.period_start
        period_end = result.period_end
        fact_value = _decimal(result.fact_value)

        if restaurant_id is not None:
            period_marker = result.period_end or result.period_start
            if period_marker:
                plan_fact = (
                    db.query(KpiPlanFact)
                    .filter(
                        KpiPlanFact.metric_id == rule.metric_id,
                        KpiPlanFact.restaurant_id == restaurant_id,
                        KpiPlanFact.year == period_marker.year,
                        KpiPlanFact.month == period_marker.month,
                    )
                    .first()
                )
                if plan_fact:
                    if plan_fact.plan_value is not None:
                        plan_value = _decimal(plan_fact.plan_value)
                    if plan_fact.fact_value is not None:
                        fact_value = _decimal(plan_fact.fact_value)
    else:
        if payload.restaurant_id is None or payload.year is None or payload.month is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нужно выбрать ресторан, год и месяц",
            )
        if rule.restaurant_id and rule.restaurant_id != payload.restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ресторан правила не совпадает с выбранным рестораном",
            )

        restaurant_id = payload.restaurant_id
        position_id = rule.position_id
        if position_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для правила должна быть указана должность",
            )
        period_start = date(payload.year, payload.month, 1)
        period_end = date(payload.year, payload.month, monthrange(payload.year, payload.month)[1])

        plan_fact = (
            db.query(KpiPlanFact)
            .filter(
                KpiPlanFact.metric_id == rule.metric_id,
                KpiPlanFact.restaurant_id == restaurant_id,
                KpiPlanFact.year == payload.year,
                KpiPlanFact.month == payload.month,
            )
            .first()
        )
        if not plan_fact:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нет данных план/факт за выбранный период",
            )
        if plan_fact.plan_value is not None:
            plan_value = _decimal(plan_fact.plan_value)
        if plan_fact.fact_value is not None:
            fact_value = _decimal(plan_fact.fact_value)

    if restaurant_id is None or position_id is None:
        if position_id is None and rule.employee_id:
            employee = db.query(User).get(rule.employee_id)
            if employee and employee.position_id:
                position_id = employee.position_id
        if restaurant_id is None or position_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не указан ресторан или должность",
            )
    if period_start is None or period_end is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указан период для расчета",
        )

    if fact_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет фактического значения для расчета",
        )

    batch = _build_payout_batch(
        db=db,
        rule=rule,
        restaurant_id=int(restaurant_id),
        position_id=int(position_id),
        period_start=period_start,
        period_end=period_end,
        plan_value=plan_value,
        fact_value=fact_value,
        comment=payload.comment,
        current_user=current_user,
        result_id=result.id if result else None,
    )
    if not batch:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет сотрудников для выплаты")
    return _batch_public(batch, include_items=True)


@router.post(
    "/payouts/preview-metric",
    response_model=KpiPayoutBatchListResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payout_preview_by_metric(
    payload: KpiPayoutPreviewByMetricRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiPayoutBatchListResponse:
    _ensure_payouts_manage(current_user)

    metric = db.query(KpiMetric).filter(KpiMetric.id == payload.metric_id).first()
    if not metric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Показатель не найден")

    period_start = date(payload.year, payload.month, 1)
    period_end = date(payload.year, payload.month, monthrange(payload.year, payload.month)[1])

    plan_fact = (
        db.query(KpiPlanFact)
        .filter(
            KpiPlanFact.metric_id == payload.metric_id,
            KpiPlanFact.restaurant_id == payload.restaurant_id,
            KpiPlanFact.year == payload.year,
            KpiPlanFact.month == payload.month,
        )
        .first()
    )
    if not plan_fact:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет данных план/факт за выбранный период",
        )

    plan_value: Optional[Decimal] = None
    fact_value: Optional[Decimal] = None
    if plan_fact.plan_value is not None:
        plan_value = _decimal(plan_fact.plan_value)
    if plan_fact.fact_value is not None:
        fact_value = _decimal(plan_fact.fact_value)

    if fact_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет фактического значения для расчета",
        )

    rules = (
        db.query(KpiRule)
        .options(joinedload(KpiRule.metric).joinedload(KpiMetric.group))
        .filter(KpiRule.metric_id == payload.metric_id)
        .filter(KpiRule.is_active.is_(True))
        .filter(KpiRule.period_start <= period_end)
        .filter(KpiRule.period_end >= period_start)
        .order_by(KpiRule.id.asc())
        .all()
    )

    if not rules:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет активных правил для показателя")

    relevant_rules = [
        rule for rule in rules if (not rule.restaurant_id or rule.restaurant_id == payload.restaurant_id)
    ]
    if not relevant_rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет правил для выбранного ресторана",
        )

    needs_plan = any(
        str(rule.comparison_basis) in ("plan_percent", "plan_delta_percent") for rule in relevant_rules
    )
    if needs_plan and (plan_value is None or plan_value == 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет планового значения для расчета",
        )

    batches: list[KpiPayoutBatchPublic] = []
    employee_position_map: dict[int, int] = {}
    missing_position_employee_ids = {
        int(rule.employee_id)
        for rule in relevant_rules
        if rule.position_id is None and rule.employee_id is not None
    }
    if missing_position_employee_ids:
        employee_rows = (
            db.query(User.id, User.position_id)
            .filter(User.id.in_(missing_position_employee_ids))
            .all()
        )
        employee_position_map = {
            int(row.id): int(row.position_id)
            for row in employee_rows
            if row.position_id is not None
        }

    for rule in relevant_rules:
        position_id = rule.position_id
        if position_id is None and rule.employee_id:
            position_id = employee_position_map.get(int(rule.employee_id))
        if position_id is None:
            continue

        batch = _build_payout_batch(
            db=db,
            rule=rule,
            restaurant_id=payload.restaurant_id,
            position_id=position_id,
            period_start=period_start,
            period_end=period_end,
            plan_value=plan_value,
            fact_value=fact_value,
            comment=payload.comment,
            current_user=current_user,
            result_id=None,
            skip_if_no_employees=True,
        )
        if batch:
            batches.append(_batch_public(batch, include_items=True))

    if not batches:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет сотрудников для выплаты")

    return KpiPayoutBatchListResponse(total=len(batches), items=batches)


@router.patch("/payouts/{batch_id}/items/{item_id}", response_model=KpiPayoutBatchPublic)
def update_payout_item(
    batch_id: int,
    item_id: int,
    payload: KpiPayoutItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiPayoutBatchPublic:
    _ensure_payouts_manage(current_user)
    batch = (
        db.query(KpiPayoutBatch)
        .options(*_payout_batch_detail_load_options())
        .filter(KpiPayoutBatch.id == batch_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout batch not found")
    if batch.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payout batch is not editable")

    item = next((row for row in batch.items if row.id == item_id), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout item not found")

    fields_set = getattr(payload, "model_fields_set", set())
    if "amount" in fields_set and payload.amount is not None:
        amount = _quantize_money(_decimal(payload.amount))
        if amount < 0:
            item.bonus_amount = Decimal("0")
            item.penalty_amount = abs(amount)
            item.bonus_enabled = False
            item.penalty_enabled = True
        else:
            item.bonus_amount = abs(amount)
            item.penalty_amount = Decimal("0")
            item.bonus_enabled = True
            item.penalty_enabled = False
    if "bonus_enabled" in fields_set:
        item.bonus_enabled = bool(payload.bonus_enabled)
    if "penalty_enabled" in fields_set:
        item.penalty_enabled = bool(payload.penalty_enabled)
    if "bonus_amount" in fields_set and payload.bonus_amount is not None:
        item.bonus_amount = _quantize_money(_decimal(payload.bonus_amount))
    if "penalty_amount" in fields_set and payload.penalty_amount is not None:
        item.penalty_amount = _quantize_money(_decimal(payload.penalty_amount))
    if "comment" in fields_set:
        item.comment = payload.comment

    if fields_set:
        item.manual = True

    db.commit()
    db.refresh(batch)
    return _batch_public(batch, include_items=True)


@router.post("/payouts/{batch_id}/post", response_model=KpiPayoutBatchPublic)
def post_payout_batch(
    batch_id: int,
    payload: KpiPayoutPostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KpiPayoutBatchPublic:
    _ensure_payouts_manage(current_user)
    batch = (
        db.query(KpiPayoutBatch)
        .options(*_payout_batch_detail_load_options(include_rule_metric=True))
        .filter(KpiPayoutBatch.id == batch_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout batch not found")
    if batch.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payout batch is already posted")

    post_date = payload.date or batch.period_end
    comment = payload.comment or "KPI payout"

    # Новый режим: один тип операции + одна сумма в строке.
    if payload.adjustment_type_id is not None:
        adjustment_type = db.query(PayrollAdjustmentType).get(payload.adjustment_type_id)
        if not adjustment_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment type not found")

        for item in batch.items:
            amount = _resolve_item_amount(item)
            if amount == 0:
                continue
            adj = PayrollAdjustment(
                user_id=item.user_id,
                adjustment_type_id=adjustment_type.id,
                restaurant_id=item.restaurant_id or batch.restaurant_id,
                amount=_normalize_amount(amount, adjustment_type.kind),
                date=post_date,
                responsible_id=current_user.id,
                comment=comment,
            )
            db.add(adj)
            if adjustment_type.kind == "deduction":
                item.penalty_adjustment = adj
                item.bonus_adjustment = None
            else:
                item.bonus_adjustment = adj
                item.penalty_adjustment = None
    else:
        needs_bonus = any(_decimal(row.bonus_amount) > 0 for row in batch.items)
        needs_penalty = any(_decimal(row.penalty_amount) > 0 for row in batch.items)

        bonus_type = None
        penalty_type = None
        if payload.bonus_adjustment_type_id is not None:
            bonus_type = db.query(PayrollAdjustmentType).get(payload.bonus_adjustment_type_id)
            if not bonus_type:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bonus adjustment type not found")
            if bonus_type.kind != "accrual":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bonus adjustment type must be accrual")
        if payload.penalty_adjustment_type_id is not None:
            penalty_type = db.query(PayrollAdjustmentType).get(payload.penalty_adjustment_type_id)
            if not penalty_type:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Penalty adjustment type not found")
            if penalty_type.kind != "deduction":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Penalty adjustment type must be deduction")

        if needs_bonus and not bonus_type:
            metric = getattr(getattr(batch, "rule", None), "metric", None)
            metric_bonus_type_id = getattr(metric, "bonus_adjustment_type_id", None)
            if metric_bonus_type_id is not None:
                bonus_type = db.query(PayrollAdjustmentType).get(int(metric_bonus_type_id))
                if bonus_type and bonus_type.kind != "accrual":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Тип выплаты показателя должен быть начислением (accrual)",
                    )
            if not bonus_type:
                bonus_type = _find_adjustment_type(db, KPI_BONUS_ADJUSTMENT_NAME, "accrual")
            if not bonus_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="bonus_adjustment_type_id is required",
                )
        if needs_penalty and not penalty_type:
            metric = getattr(getattr(batch, "rule", None), "metric", None)
            metric_penalty_type_id = getattr(metric, "penalty_adjustment_type_id", None)
            if metric_penalty_type_id is not None:
                penalty_type = db.query(PayrollAdjustmentType).get(int(metric_penalty_type_id))
                if penalty_type and penalty_type.kind != "deduction":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Тип удержания показателя должен быть удержанием (deduction)",
                    )
            if not penalty_type:
                penalty_type = _find_adjustment_type(db, KPI_PENALTY_ADJUSTMENT_NAME, "deduction")
            if not penalty_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="penalty_adjustment_type_id is required",
                )

        for item in batch.items:
            if needs_bonus and bonus_type and _decimal(item.bonus_amount) > 0:
                adj = PayrollAdjustment(
                    user_id=item.user_id,
                    adjustment_type_id=bonus_type.id,
                    restaurant_id=item.restaurant_id or batch.restaurant_id,
                    amount=_normalize_amount(_decimal(item.bonus_amount), bonus_type.kind),
                    date=post_date,
                    responsible_id=current_user.id,
                    comment=comment,
                )
                db.add(adj)
                item.bonus_adjustment = adj
            if needs_penalty and penalty_type and _decimal(item.penalty_amount) > 0:
                adj = PayrollAdjustment(
                    user_id=item.user_id,
                    adjustment_type_id=penalty_type.id,
                    restaurant_id=item.restaurant_id or batch.restaurant_id,
                    amount=_normalize_amount(_decimal(item.penalty_amount), penalty_type.kind),
                    date=post_date,
                    responsible_id=current_user.id,
                    comment=comment,
                )
                db.add(adj)
                item.penalty_adjustment = adj

    batch.status = "posted"
    batch.posted_at = datetime.utcnow()
    batch.posted_by_id = current_user.id

    db.commit()
    db.refresh(batch)
    return _batch_public(batch, include_items=True)
