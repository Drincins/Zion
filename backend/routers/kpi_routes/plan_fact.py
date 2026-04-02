from . import common as c


router = c.APIRouter()

router.add_api_route(
    "/plan-fact",
    c.list_plan_facts,
    methods=["GET"],
    response_model=c.KpiPlanFactListResponse,
)
router.add_api_route(
    "/plan-fact/bulk",
    c.list_plan_facts_bulk,
    methods=["GET"],
    response_model=c.KpiPlanFactBulkResponse,
)
router.add_api_route(
    "/plan-fact",
    c.upsert_plan_fact,
    methods=["PUT"],
    response_model=c.KpiPlanFactPublic,
)
router.add_api_route(
    "/plan-fact/bulk",
    c.upsert_plan_facts_bulk,
    methods=["PUT"],
    response_model=c.KpiPlanFactBulkResponse,
)

router.add_api_route(
    "/metric-group-plan-fact",
    c.list_metric_group_plan_facts,
    methods=["GET"],
    response_model=c.KpiMetricGroupPlanFactListResponse,
)
router.add_api_route(
    "/metric-group-plan-fact/bulk",
    c.list_metric_group_plan_facts_bulk,
    methods=["GET"],
    response_model=c.KpiMetricGroupPlanFactBulkResponse,
)
router.add_api_route(
    "/metric-group-plan-fact",
    c.upsert_metric_group_plan_fact,
    methods=["PUT"],
    response_model=c.KpiMetricGroupPlanFactPublic,
)
router.add_api_route(
    "/metric-group-plan-fact/bulk",
    c.upsert_metric_group_plan_facts_bulk,
    methods=["PUT"],
    response_model=c.KpiMetricGroupPlanFactBulkResponse,
)
