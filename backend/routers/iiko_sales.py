from __future__ import annotations

from fastapi import APIRouter

from backend.schemas.iiko_sales import (
    SyncIikoSalesRequest,
)
from backend.routers.iiko_sales_routes.finance import router as finance_router
from backend.routers.iiko_sales_routes.layouts import router as layouts_router
from backend.routers.iiko_sales_routes.reports import router as reports_router
from backend.routers.iiko_sales_routes.sync import (
    router as sync_router,
    sync_iiko_sales,
)
from backend.routers.iiko_sales_routes.turnover import router as turnover_router
from backend.services.iiko_sales_sync_runtime import (
    build_sync_source_conflict_map as _build_sync_source_conflict_map,
    build_sync_source_groups as _build_sync_source_groups,
    parse_sales_sync_application_name as _parse_sales_sync_application_name,
    restaurant_iiko_source_key as _restaurant_iiko_source_key,
    sync_sales_orders_and_items_resilient as _sync_sales_orders_and_items_resilient,
)

router = APIRouter(prefix="/iiko-sales", tags=["iiko-sales"])

router.include_router(sync_router, tags=["iiko-sales"])
router.include_router(layouts_router, tags=["iiko-sales"])
router.include_router(turnover_router, tags=["iiko-sales"])
router.include_router(finance_router, tags=["iiko-sales"])
router.include_router(reports_router, tags=["iiko-sales"])
