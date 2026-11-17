from planner.config.schema import load_scenario
from planner.domain.segment import derived_segment, discrepancy
from planner.tests.conftest import account


def test_segment_boundaries():
    cfg = load_scenario("baseline")
    assert derived_segment(0, cfg) == "Commercial"
    assert derived_segment(199, cfg) == "Commercial"
    assert derived_segment(200, cfg) == "Mid-Market"
    assert derived_segment(999, cfg) == "Mid-Market"
    assert derived_segment(1000, cfg) == "Enterprise"
    assert derived_segment(50000, cfg) == "Enterprise"


def test_missing_headcount_is_unknown():
    cfg = load_scenario("baseline")
    assert derived_segment(None, cfg) == "Unknown"


def test_stale_mm_to_ent():
    cfg = load_scenario("baseline")
    acc = account(employee_count=1200, crm_segment="Mid-Market")
    derived = derived_segment(acc.employee_count, cfg)
    assert derived == "Enterprise"
    assert discrepancy(acc, derived) == "Mid-Market → Enterprise"
