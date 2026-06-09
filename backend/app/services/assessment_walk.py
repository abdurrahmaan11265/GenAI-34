"""
Deterministic placement logic for the adaptive assessment.

This module is PURE: no DB, no LLM, no I/O. It implements Section D of
docs/architecture/system_design.md — the top-down topological DAG walk with
per-node tier escalation (MCQ -> theory -> applied) and branch-stop.

Keeping it pure makes the critical placement rules (branch-stop, scoring,
graph reveal states) unit-testable without infrastructure.

Backend owns truth (AGENT.md): every decision here is deterministic. The LLM
only generates and grades question *language*; it never decides state.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

# Tier progression for a single concept. Index 0 is the "easy" tier whose
# failure triggers branch-stop into all dependents.
TIER_SEQUENCE: List[str] = ["MCQ", "SHORT_ANSWER", "SCENARIO"]

TIER_DIFFICULTY: Dict[str, str] = {
    "MCQ": "beginner",
    "SHORT_ANSWER": "intermediate",
    "SCENARIO": "advanced",
}
TIER_BLOOM: Dict[str, str] = {
    "MCQ": "understand",
    "SHORT_ANSWER": "apply",
    "SCENARIO": "analyze",
}
TIER_DIFFICULTY_LEVEL: Dict[str, int] = {
    "MCQ": 2,
    "SHORT_ANSWER": 3,
    "SCENARIO": 4,
}

# tiers_passed -> (mastery_estimate, placement_state, mastery_state)
# tiers_passed == 3 means all three tiers cleared.
_TIER_OUTCOME: Dict[int, Tuple[float, str, str]] = {
    3: (0.90, "MASTERED", "MASTERED"),
    2: (0.70, "READY", "PRACTICING"),
    1: (0.45, "LEARNING", "LEARNING"),
    0: (0.15, "WEAK", "LEARNING"),
}
# Untested (skipped because a prerequisite branch was unknown).
_UNTESTED_OUTCOME: Tuple[float, str, str] = (0.0, "UNKNOWN", "UNKNOWN")


@dataclass
class Response:
    concept_id: str
    question_type: str  # the tier: MCQ | SHORT_ANSWER | SCENARIO
    is_correct: bool


@dataclass
class NextQuestion:
    concept_id: str
    tier: str  # one of TIER_SEQUENCE


@dataclass
class ConceptOutcome:
    concept_id: str
    tested: bool
    tiers_passed: int  # 0..3 (0 also used for untested)
    mastery_estimate: float
    placement_state: str  # MASTERED | READY | LEARNING | WEAK | UNKNOWN
    mastery_state: str     # MASTERED | PRACTICING | LEARNING | UNKNOWN
    node_state: str        # MASTERED | AVAILABLE | LOCKED


def topological_order(concept_ids: Sequence[str],
                      prereq_edges: Sequence[Tuple[str, str]]) -> List[str]:
    """Kahn's algorithm. Roots (no prerequisites) first, toward leaves.

    Edges are (from_id, to_id) where from_id is a prerequisite of to_id.
    Any nodes left over (would indicate a cycle, which the ingestion pipeline
    already rejects) are appended in stable order so we never drop a concept.
    """
    ids = list(concept_ids)
    id_set = set(ids)
    indegree: Dict[str, int] = {cid: 0 for cid in ids}
    adj: Dict[str, List[str]] = defaultdict(list)

    for src, dst in prereq_edges:
        if src in id_set and dst in id_set:
            adj[src].append(dst)
            indegree[dst] += 1

    queue = deque([cid for cid in ids if indegree[cid] == 0])
    order: List[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nxt in adj[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(order) < len(ids):  # defensive: cycle remnant
        order.extend(cid for cid in ids if cid not in set(order))
    return order


def _group_responses(responses: Sequence[Response]) -> Dict[str, List[Response]]:
    grouped: Dict[str, List[Response]] = defaultdict(list)
    for r in responses:
        grouped[r.concept_id].append(r)
    return grouped


def failed_mcq(grouped: Dict[str, List[Response]]) -> Set[str]:
    """Concepts that failed the easy (MCQ) tier — these trigger branch-stop."""
    failed: Set[str] = set()
    for cid, rs in grouped.items():
        if rs and rs[0].question_type == "MCQ" and not rs[0].is_correct:
            failed.add(cid)
    return failed


def _concept_progress(rs: List[Response]) -> Tuple[bool, int]:
    """Return (resolved, tiers_passed) for a concept given its responses
    in chronological tier order. Resolved means no further question is needed.

    tiers_passed = number of consecutive correct answers from the easy tier.
    """
    tiers_passed = 0
    for r in rs:
        if r.is_correct:
            tiers_passed += 1
        else:
            return True, tiers_passed  # failed a tier -> resolved
    if tiers_passed >= len(TIER_SEQUENCE):
        return True, tiers_passed       # cleared all tiers -> resolved
    return False, tiers_passed          # still escalating


def next_question(concept_ids: Sequence[str],
                  prereq_edges: Sequence[Tuple[str, str]],
                  responses: Sequence[Response],
                  blocked: Set[str]) -> Optional[NextQuestion]:
    """The next (concept, tier) to ask, or None when the walk is complete.

    Walks concepts in topological order; skips blocked (presumed-unknown)
    concepts; for each remaining concept asks the next un-answered tier.
    """
    order = topological_order(concept_ids, prereq_edges)
    grouped = _group_responses(responses)

    for cid in order:
        if cid in blocked:
            continue
        rs = grouped.get(cid, [])
        resolved, tiers_passed = _concept_progress(rs)
        if resolved:
            continue
        return NextQuestion(concept_id=cid, tier=TIER_SEQUENCE[tiers_passed])
    return None


def compute_outcomes(concept_ids: Sequence[str],
                     prereq_edges: Sequence[Tuple[str, str]],
                     responses: Sequence[Response],
                     blocked: Set[str]) -> List[ConceptOutcome]:
    """Final per-concept placement after the walk completes.

    Every concept lands in a known state (Section D output contract): tested
    concepts are scored by tiers passed; skipped concepts are UNKNOWN. node_state
    implements the graph reveal (Section E): MASTERED, else AVAILABLE when all
    direct prerequisites are mastered, else LOCKED.
    """
    grouped = _group_responses(responses)

    direct_prereqs: Dict[str, List[str]] = defaultdict(list)
    for src, dst in prereq_edges:
        direct_prereqs[dst].append(src)

    # First pass: mastery + placement per concept.
    placement: Dict[str, Tuple[float, str, str, bool, int]] = {}
    for cid in concept_ids:
        rs = grouped.get(cid, [])
        if cid in blocked or not rs:
            est, place, mstate = _UNTESTED_OUTCOME
            placement[cid] = (est, place, mstate, False, 0)
        else:
            _, tiers_passed = _concept_progress(rs)
            est, place, mstate = _TIER_OUTCOME[min(tiers_passed, 3)]
            placement[cid] = (est, place, mstate, True, tiers_passed)

    mastered: Set[str] = {cid for cid, p in placement.items() if p[1] == "MASTERED"}

    outcomes: List[ConceptOutcome] = []
    for cid in concept_ids:
        est, place, mstate, tested, tiers_passed = placement[cid]
        if place == "MASTERED":
            node_state = "MASTERED"
        else:
            prereqs = direct_prereqs.get(cid, [])
            all_prereqs_mastered = all(p in mastered for p in prereqs)
            node_state = "AVAILABLE" if all_prereqs_mastered else "LOCKED"
        outcomes.append(ConceptOutcome(
            concept_id=cid,
            tested=tested,
            tiers_passed=tiers_passed,
            mastery_estimate=est,
            placement_state=place,
            mastery_state=mstate,
            node_state=node_state,
        ))
    return outcomes
