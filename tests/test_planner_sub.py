import pytest


pytestmark = pytest.mark.skip(reason="v1 planner/langgraph is legacy; v2 Braid uses LCM knot processing")


def test_planner_sub_updates_route_and_planned_tools() -> None:
    # skipped
    return


