from fastapi import APIRouter

from backend.routers import employees_card as legacy_employees_card
from backend.routers.staff_employee_routes import common as common_routes
from backend.routers.staff_employee_routes.admin import router as admin_router
from backend.routers.staff_employee_routes.detail import router as detail_router
from backend.routers.staff_employee_routes.listing import (
    list_staff_employees_compact as list_staff_employees_compact_handler,
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
router.add_api_route(
    "/compact",
    list_staff_employees_compact_handler,
    methods=["GET"],
    response_model=common_routes.StaffEmployeeListCompactResponse,
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
    include_in_schema=False,
)

# Compatibility aliases for legacy /api/employees/{id}/... endpoints.
router.add_api_route(
    "/{user_id}/card",
    legacy_employees_card.get_employee_card,
    methods=["GET"],
    response_model=legacy_employees_card.EmployeeCardPublic,
    include_in_schema=False,
)
router.add_api_route(
    "/{user_id}/attendances",
    legacy_employees_card.get_employee_attendances,
    methods=["GET"],
    response_model=legacy_employees_card.AttendanceRangeResponse,
    include_in_schema=False,
)
router.add_api_route(
    "/{user_id}/attendances",
    legacy_employees_card.create_employee_attendance,
    methods=["POST"],
    response_model=legacy_employees_card.AttendancePublic,
    status_code=legacy_employees_card.status.HTTP_201_CREATED,
    include_in_schema=False,
)
router.add_api_route(
    "/{user_id}/attendances/{attendance_id}",
    legacy_employees_card.update_employee_attendance,
    methods=["PATCH"],
    response_model=legacy_employees_card.AttendancePublic,
    include_in_schema=False,
)
router.add_api_route(
    "/{user_id}/attendances/{attendance_id}",
    legacy_employees_card.delete_employee_attendance,
    methods=["DELETE"],
    status_code=legacy_employees_card.status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
router.add_api_route(
    "/{user_id}/attendances/recalculate-night",
    legacy_employees_card.recalculate_employee_attendance_night,
    methods=["POST"],
    response_model=legacy_employees_card.AttendanceRangeResponse,
    include_in_schema=False,
)

router.include_router(listing_router)
router.include_router(admin_router)
router.include_router(detail_router)
router.include_router(mutations_router)
