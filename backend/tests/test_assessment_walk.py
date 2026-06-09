"""
Unit tests for the deterministic placement logic (Section D of the system design).

Covers the critical, infrastructure-free rules:
  - topological walk order (roots first)
  - tier escalation (MCQ -> SHORT_ANSWER -> SCENARIO)
  - branch-stop (failing the easy tier skips all dependents)
  - per-concept scoring + graph-reveal node states
"""
from app.services import assessment_walk as walk
from app.services.assessment_walk import Response

# Graph:  A -> B -> C  and  A -> D   (X -> Y means X is a prerequisite of Y)
A, B, C, D = "A", "B", "C", "D"
CONCEPTS = [A, B, C, D]
EDGES = [(A, B), (B, C), (A, D)]


def mock_blocked(edges, responses):
    grouped = walk._group_responses(responses)
    failed = walk.failed_mcq(grouped)
    
    from collections import defaultdict
    adj = defaultdict(list)
    for src, dst in edges:
        adj[src].append(dst)
        
    blocked = set()
    for f in failed:
        stack = list(adj[f])
        while stack:
            cur = stack.pop()
            blocked.add(cur)
            stack.extend(adj[cur])
    return blocked

def test_topological_order_roots_first():
    order = walk.topological_order(CONCEPTS, EDGES)
    assert order.index(A) < order.index(B)
    assert order.index(A) < order.index(D)
    assert order.index(B) < order.index(C)


def test_first_question_is_a_root_mcq():
    nxt = walk.next_question(CONCEPTS, EDGES, [], set())
    assert nxt is not None
    assert nxt.concept_id == A
    assert nxt.tier == "MCQ"


def test_tier_escalation_on_pass():
    # Pass MCQ on A -> should escalate to SHORT_ANSWER on the same concept.
    rs = [Response(A, "MCQ", True)]
    nxt = walk.next_question(CONCEPTS, EDGES, rs, mock_blocked(EDGES, rs))
    assert nxt.concept_id == A and nxt.tier == "SHORT_ANSWER"

    # Pass SHORT_ANSWER too -> SCENARIO.
    rs.append(Response(A, "SHORT_ANSWER", True))
    nxt = walk.next_question(CONCEPTS, EDGES, rs, mock_blocked(EDGES, rs))
    assert nxt.concept_id == A and nxt.tier == "SCENARIO"


def test_mastered_concept_advances_to_next_in_topo_order():
    rs = [
        Response(A, "MCQ", True),
        Response(A, "SHORT_ANSWER", True),
        Response(A, "SCENARIO", True),
    ]
    nxt = walk.next_question(CONCEPTS, EDGES, rs, mock_blocked(EDGES, rs))
    # A is fully cleared; the next testable concept is B (a dependent of A).
    assert nxt.concept_id == B and nxt.tier == "MCQ"


def test_branch_stop_skips_all_dependents():
    # Fail the easy (MCQ) tier on root A.
    rs = [Response(A, "MCQ", False)]
    blocked = mock_blocked(EDGES, rs)
    assert blocked == {B, C, D}

    # With A resolved (failed) and B/C/D blocked, the walk is complete.
    assert walk.next_question(CONCEPTS, EDGES, rs, blocked) is None


def test_failing_later_tier_does_not_branch_stop():
    # Pass MCQ (easy tier) but fail SHORT_ANSWER -> dependents must NOT be blocked.
    rs = [Response(A, "MCQ", True), Response(A, "SHORT_ANSWER", False)]
    assert mock_blocked(EDGES, rs) == set()
    nxt = walk.next_question(CONCEPTS, EDGES, rs, set())
    assert nxt.concept_id == B  # descend continues into dependents


def test_outcomes_scoring_and_node_states():
    rs = [
        # A: cleared all three tiers -> MASTERED
        Response(A, "MCQ", True),
        Response(A, "SHORT_ANSWER", True),
        Response(A, "SCENARIO", True),
        # B: passed MCQ, failed SHORT_ANSWER -> tiers_passed 1 -> LEARNING
        Response(B, "MCQ", True),
        Response(B, "SHORT_ANSWER", False),
        # D: failed MCQ -> WEAK
        Response(D, "MCQ", False),
    ]
    outcomes = {o.concept_id: o for o in walk.compute_outcomes(CONCEPTS, EDGES, rs, mock_blocked(EDGES, rs))}

    assert outcomes[A].placement_state == "MASTERED"
    assert outcomes[A].node_state == "MASTERED"

    assert outcomes[B].placement_state == "LEARNING"
    # B's only prerequisite (A) is mastered -> available to learn.
    assert outcomes[B].node_state == "AVAILABLE"

    assert outcomes[D].placement_state == "WEAK"
    assert outcomes[D].node_state == "AVAILABLE"  # prereq A mastered

    # C was never reached (B not mastered) -> untested, unknown, locked.
    assert outcomes[C].tested is False
    assert outcomes[C].placement_state == "UNKNOWN"
    assert outcomes[C].node_state == "LOCKED"


def test_confident_failure_marks_branch_for_learning():
    # Two independent roots; failing one must not block the other.
    concepts = ["R1", "R2", "X"]
    edges = [("R1", "X")]  # R1 prereq of X; R2 independent
    rs = [Response("R1", "MCQ", False)]
    blocked = mock_blocked(edges, rs)
    assert blocked == {"X"}
    nxt = walk.next_question(concepts, edges, rs, blocked)
    assert nxt is not None and nxt.concept_id == "R2"
