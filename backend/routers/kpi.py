from fastapi import APIRouter

from backend.routers.kpi_routes import metrics, plan_fact, payouts, results, rules


router = APIRouter(prefix="/kpi", tags=["KPI"])

router.include_router(metrics.router)
router.include_router(plan_fact.router)
router.include_router(rules.router)
router.include_router(results.router)
router.include_router(payouts.router)
