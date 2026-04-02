from fastapi import status

from . import common as c


router = c.APIRouter()

router.add_api_route(
    "/rules",
    c.list_rules,
    methods=["GET"],
    response_model=c.KpiRuleListResponse,
)
router.add_api_route(
    "/rules",
    c.create_rule,
    methods=["POST"],
    response_model=c.KpiRulePublic,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/rules/{rule_id}",
    c.update_rule,
    methods=["PATCH"],
    response_model=c.KpiRulePublic,
)
router.add_api_route(
    "/rules/{rule_id}",
    c.delete_rule,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)

router.add_api_route(
    "/group-rules",
    c.list_group_rules,
    methods=["GET"],
    response_model=c.KpiMetricGroupRuleListResponse,
)
router.add_api_route(
    "/group-rules",
    c.create_group_rule,
    methods=["POST"],
    response_model=c.KpiMetricGroupRulePublic,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/group-rules/{rule_id}",
    c.update_group_rule,
    methods=["PATCH"],
    response_model=c.KpiMetricGroupRulePublic,
)
router.add_api_route(
    "/group-rules/{rule_id}",
    c.delete_group_rule,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)
