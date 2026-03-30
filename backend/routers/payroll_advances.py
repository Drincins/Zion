from fastapi import APIRouter

from backend.routers.payroll_advance_routes import common as c
from backend.routers.payroll_advance_routes import consolidated, items, listing, statements, workflow


router = APIRouter(prefix="/payroll/advances", tags=["Payroll advances"])

router.add_api_route(
    "",
    listing.list_statements,
    methods=["GET"],
    response_model=c.PayrollAdvanceListResponse,
    include_in_schema=False,
)
router.add_api_route(
    "",
    statements.create_statement,
    methods=["POST"],
    response_model=c.PayrollAdvanceStatementPublic,
    status_code=201,
    include_in_schema=False,
)
router.include_router(listing.router)
router.include_router(consolidated.router)
router.include_router(statements.router)
router.include_router(items.router)
router.include_router(workflow.router)
