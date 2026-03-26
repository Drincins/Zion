from __future__ import annotations

from fastapi import APIRouter

from backend.routers.inventory_routes.balance import router as balance_router
from backend.routers.inventory_routes.catalog import router as catalog_router
from backend.routers.inventory_routes.items import router as items_router
from backend.routers.inventory_routes.movements import router as movements_router
from backend.routers.inventory_routes.records import router as records_router
from backend.routers.inventory_routes.settings import router as settings_router

router = APIRouter(prefix="/inventory", tags=["Inventory"])

router.include_router(catalog_router, tags=["Inventory"])
router.include_router(settings_router, tags=["Inventory"])
router.include_router(items_router, tags=["Inventory"])
router.include_router(movements_router, tags=["Inventory"])
router.include_router(records_router, tags=["Inventory"])
router.include_router(balance_router, tags=["Inventory"])
