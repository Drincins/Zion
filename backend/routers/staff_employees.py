from fastapi import APIRouter

from backend.routers.staff_employee_routes import common as common_routes
from backend.routers.staff_employee_routes.admin import router as admin_router
from backend.routers.staff_employee_routes.detail import router as detail_router
from backend.routers.staff_employee_routes.listing import (
    list_staff_employees as list_staff_employees_handler,
    router as listing_router,
)
from backend.routers.staff_employee_routes.mutations import router as mutations_router

router = APIRouter(prefix="/staff/employees", tags=["Staff employees"])

# Compatibility alias for clients that call /api/staff/employees without a trailing slash.
router.add_api_route(
    "",
    list_staff_employees_handler,
    methods=["GET"],
    response_model=common_routes.StaffEmployeeListResponse,
    include_in_schema=False,
)

router.include_router(listing_router)
router.include_router(admin_router)
router.include_router(detail_router)
router.include_router(mutations_router)
