"""
Deterministic curriculum + daily-plan logic (System Design Section G).

Pure: no DB, no LLM. AGENT.md principle #7 — "Graph decides curriculum; AI
explains curriculum." The learning ORDER and gating here are fully deterministic
(topological over the prerequisite DAG, filtered by the learner's mastery
state). Any natural-language explanation is a separate, optional LLM step.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from app.services.assessment_walk import topological_order
from app.services.mastery_engine import MASTERY_THRESHOLD

# Default minutes per item when a concept has no estimate (UI time hints).
DEFAULT_MINUTES = 10


@dataclass
class CurriculumItem:
    concept_id: str
    title: str
    order_index: int
    state: str                  # LOCKED | AVAILABLE | IN_PROGRESS | MASTERED | DUE
    mastery: float
    estimated_minutes: int
    unmet_prerequisites: List[str] = field(default_factory=list)  # titles, for "complete X first"
    subtopics: List[str] = field(default_factory=list)            # sub-topics within the concept


def build_curriculum(concepts: Sequence[dict],
                     prereq_edges: Sequence[Tuple[str, str]],
                     states: Dict[str, str],
                     masteries: Dict[str, float],
                     neo4j_topological_order: List[str]) -> List[CurriculumItem]:
    """Ordered learning path for one book.

    `concepts` are dicts: {id, title, estimated_minutes}. `states` maps
    concept_id -> node_state; `masteries` maps concept_id -> score. Concepts
    with no recorded state default to AVAILABLE (root) / LOCKED (has prereqs).
    The topological order is provided by Neo4j's Cypher resolution.
    """
    by_id = {c["id"]: c for c in concepts}
    order = list(neo4j_topological_order)
    
    # Defensive: Ensure all concepts exist in the topological order
    for cid in by_id.keys():
        if cid not in order:
            order.append(cid)

    direct_prereqs: Dict[str, List[str]] = defaultdict(list)
    for src, dst in prereq_edges:
        direct_prereqs[dst].append(src)

    mastered = {cid for cid in by_id if states.get(cid) == "MASTERED"
                or (cid not in states and masteries.get(cid, 0.0) >= MASTERY_THRESHOLD)}

    items: List[CurriculumItem] = []
    for idx, cid in enumerate(order):
        c = by_id[cid]
        if cid in states:
            state = states[cid]
        else:
            state = "AVAILABLE" if not direct_prereqs.get(cid) else "LOCKED"
        unmet = [by_id[p]["title"] for p in direct_prereqs.get(cid, []) if p not in mastered]
        items.append(CurriculumItem(
            concept_id=cid,
            title=c["title"],
            order_index=idx,
            state=state,
            mastery=round(float(masteries.get(cid, 0.0)), 4),
            estimated_minutes=int(c.get("estimated_minutes") or DEFAULT_MINUTES),
            unmet_prerequisites=unmet,
            subtopics=list(c.get("subtopics") or []),
        ))
    return items


@dataclass
class DailyPlan:
    mode: str                    # revise_only | learn_only | both | all_caught_up
    revise: List[CurriculumItem]
    learn: List[CurriculumItem]
    estimated_minutes: int


def build_daily_plan(items: Sequence[CurriculumItem], daily_new_cap: int) -> DailyPlan:
    """One of: revise_only / learn_only / both / all_caught_up (Section G #29)."""
    due = [it for it in items if it.state == "DUE"]
    available = [it for it in items if it.state in ("AVAILABLE", "IN_PROGRESS")]
    learn = available[:max(0, daily_new_cap)]

    if not due and not learn:
        mode = "all_caught_up"
    elif due and not learn:
        mode = "revise_only"
    elif learn and not due:
        mode = "learn_only"
    else:
        mode = "both"

    minutes = sum(it.estimated_minutes for it in due) + sum(it.estimated_minutes for it in learn)
    return DailyPlan(mode=mode, revise=due, learn=learn, estimated_minutes=minutes)
