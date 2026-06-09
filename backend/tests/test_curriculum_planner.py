"""Unit tests for the deterministic curriculum + daily-plan logic."""
from app.services import curriculum_planner as planner

# Variables -> Functions -> Recursion ; Variables -> Loops
CONCEPTS = [
    {"id": "V", "title": "Variables", "estimated_minutes": 10},
    {"id": "F", "title": "Functions", "estimated_minutes": 15},
    {"id": "R", "title": "Recursion", "estimated_minutes": 20},
    {"id": "L", "title": "Loops", "estimated_minutes": 10},
]
EDGES = [("V", "F"), ("F", "R"), ("V", "L")]


from app.services.assessment_walk import topological_order

def mock_topo():
    return topological_order([c["id"] for c in CONCEPTS], EDGES)

def test_curriculum_order_respects_prerequisites():
    items = planner.build_curriculum(CONCEPTS, EDGES, states={}, masteries={}, neo4j_topological_order=mock_topo())
    order = [it.concept_id for it in items]
    assert order.index("V") < order.index("F") < order.index("R")
    assert order.index("V") < order.index("L")


def test_default_states_root_available_dependents_locked():
    items = {it.concept_id: it for it in planner.build_curriculum(CONCEPTS, EDGES, {}, {}, mock_topo())}
    assert items["V"].state == "AVAILABLE"      # root
    assert items["F"].state == "LOCKED"         # needs Variables
    assert items["F"].unmet_prerequisites == ["Variables"]


def test_locked_reason_clears_when_prereq_mastered():
    states = {"V": "MASTERED", "F": "AVAILABLE", "R": "LOCKED", "L": "AVAILABLE"}
    masteries = {"V": 0.9}
    items = {it.concept_id: it for it in planner.build_curriculum(CONCEPTS, EDGES, states, masteries, mock_topo())}
    assert items["F"].unmet_prerequisites == []   # Variables mastered
    assert items["R"].unmet_prerequisites == ["Functions"]


def test_daily_plan_learn_only():
    states = {"V": "AVAILABLE", "F": "LOCKED", "R": "LOCKED", "L": "AVAILABLE"}
    items = planner.build_curriculum(CONCEPTS, EDGES, states, {}, mock_topo())
    dp = planner.build_daily_plan(items, daily_new_cap=10)
    assert dp.mode == "learn_only"
    assert {it.concept_id for it in dp.learn} == {"V", "L"}


def test_daily_plan_both_and_cap():
    states = {"V": "DUE", "F": "AVAILABLE", "R": "AVAILABLE", "L": "AVAILABLE"}
    items = planner.build_curriculum(CONCEPTS, EDGES, states, {}, mock_topo())
    dp = planner.build_daily_plan(items, daily_new_cap=1)
    assert dp.mode == "both"
    assert len(dp.revise) == 1            # V is due
    assert len(dp.learn) == 1             # capped to 1 new


def test_daily_plan_all_caught_up():
    states = {"V": "MASTERED", "F": "MASTERED", "R": "MASTERED", "L": "MASTERED"}
    items = planner.build_curriculum(CONCEPTS, EDGES, states, {}, mock_topo())
    dp = planner.build_daily_plan(items, daily_new_cap=10)
    assert dp.mode == "all_caught_up"
