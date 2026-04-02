from fastapi import status

from . import common as c


router = c.APIRouter()

router.add_api_route(
    "/payouts",
    c.list_payout_batches,
    methods=["GET"],
    response_model=c.KpiPayoutBatchListResponse,
)
router.add_api_route(
    "/payouts/bulk",
    c.list_payout_batches_bulk,
    methods=["GET"],
    response_model=c.KpiPayoutBatchListResponse,
)
router.add_api_route(
    "/payouts/{batch_id}",
    c.get_payout_batch,
    methods=["GET"],
    response_model=c.KpiPayoutBatchPublic,
)
router.add_api_route(
    "/payouts/{batch_id}",
    c.delete_payout_batch,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)
router.add_api_route(
    "/payouts/{batch_id}/items/{item_id}",
    c.delete_payout_item,
    methods=["DELETE"],
    response_model=c.KpiPayoutBatchPublic,
)
router.add_api_route(
    "/payouts/preview",
    c.create_payout_preview,
    methods=["POST"],
    response_model=c.KpiPayoutBatchPublic,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/payouts/preview-metric",
    c.create_payout_preview_by_metric,
    methods=["POST"],
    response_model=c.KpiPayoutBatchListResponse,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/payouts/{batch_id}/items/{item_id}",
    c.update_payout_item,
    methods=["PATCH"],
    response_model=c.KpiPayoutBatchPublic,
)
router.add_api_route(
    "/payouts/{batch_id}/post",
    c.post_payout_batch,
    methods=["POST"],
    response_model=c.KpiPayoutBatchPublic,
)
