from fastapi import status

from . import common as c


router = c.APIRouter()

router.add_api_route(
    "/results",
    c.list_results,
    methods=["GET"],
    response_model=c.KpiResultListResponse,
)
router.add_api_route(
    "/results",
    c.create_result,
    methods=["POST"],
    response_model=c.KpiResultPublic,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/results/{result_id}",
    c.update_result,
    methods=["PATCH"],
    response_model=c.KpiResultPublic,
)
router.add_api_route(
    "/results/{result_id}",
    c.delete_result,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)
