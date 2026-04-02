from fastapi import status

from . import common as c


router = c.APIRouter()

router.add_api_route(
    "/metric-groups",
    c.list_metric_groups,
    methods=["GET"],
    response_model=c.KpiMetricGroupListResponse,
)
router.add_api_route(
    "/metric-groups",
    c.create_metric_group,
    methods=["POST"],
    response_model=c.KpiMetricGroupPublic,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/metric-groups/{group_id}",
    c.update_metric_group,
    methods=["PATCH"],
    response_model=c.KpiMetricGroupPublic,
)
router.add_api_route(
    "/metric-groups/{group_id}",
    c.delete_metric_group,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)

router.add_api_route(
    "/metrics",
    c.list_metrics,
    methods=["GET"],
    response_model=c.KpiMetricListResponse,
)
router.add_api_route(
    "/metrics",
    c.create_metric,
    methods=["POST"],
    response_model=c.KpiMetricPublic,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/metrics/{metric_id}",
    c.update_metric,
    methods=["PATCH"],
    response_model=c.KpiMetricPublic,
)
router.add_api_route(
    "/metrics/{metric_id}",
    c.delete_metric,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)

router.add_api_route(
    "/plan-preferences",
    c.list_plan_preferences,
    methods=["GET"],
    response_model=c.KpiPlanPreferenceListResponse,
)
router.add_api_route(
    "/plan-preferences",
    c.upsert_plan_preference,
    methods=["PUT"],
    response_model=c.KpiPlanPreferencePublic,
)
router.add_api_route(
    "/metric-group-plan-preferences",
    c.list_metric_group_plan_preferences,
    methods=["GET"],
    response_model=c.KpiMetricGroupPlanPreferenceListResponse,
)
router.add_api_route(
    "/metric-group-plan-preferences",
    c.upsert_metric_group_plan_preference,
    methods=["PUT"],
    response_model=c.KpiMetricGroupPlanPreferencePublic,
)
