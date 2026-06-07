"""
Progress engine — one of the two allowed writers of the learner model
(AGENT.md: Assessment Engine + Progress Engine only).

PR4 scope: record concept completion from a finished lesson (mastery -> MASTERED,
node state -> MASTERED) and re-evaluate the DAG to unlock newly-available
dependents (System Design F#26). PR5 extends this with FSRS scheduling and
review-grade updates.
"""
from __future__ import annotations

from collections import defaultdict
from typing import List

from app.repositories.graph_repo import GraphRepository
from app.repositories.assessment_repo import AssessmentRepository

MASTERY_ON_LESSON_COMPLETE = 0.9
MASTERED_THRESHOLD = 0.85


class ProgressService:
    def __init__(self, graph_repo: GraphRepository, assess_repo: AssessmentRepository):
        self.graph = graph_repo
        self.repo = assess_repo

    async def complete_concept(self, user_id: str, book_id: str, concept_id: str,
                               source: str = "LESSON") -> List[str]:
        """Mark a concept mastered and unlock dependents whose prerequisites are
        now all mastered. Returns the titles of newly-unlocked concepts."""
        gv = await self.graph.active_graph_version(book_id)
        if gv is None:
            return []

        # Write mastery + node state for the completed concept.
        await self.repo.upsert_concept_mastery(user_id, concept_id, MASTERY_ON_LESSON_COMPLETE, "MASTERED", source=source)
        await self.repo.upsert_node_state(user_id, concept_id, gv, "MASTERED")

        # Recompute the mastered set and unlock dependents.
        concepts = await self.graph.concepts(book_id, gv)
        edges = await self.graph.prerequisite_edges(book_id, gv)
        states = await self.graph.node_states(user_id, book_id)
        masteries = {cid: score for cid, (score, _lr) in (await self.graph.masteries(user_id, book_id)).items()}

        direct_prereqs = defaultdict(list)
        for e in edges:
            direct_prereqs[str(e.to_concept_id)].append(str(e.from_concept_id))

        mastered = {str(c.id) for c in concepts
                    if states.get(str(c.id)) == "MASTERED"
                    or masteries.get(str(c.id), 0.0) >= MASTERED_THRESHOLD}
        mastered.add(concept_id)

        unlocked: List[str] = []
        for c in concepts:
            cid = str(c.id)
            cur = states.get(cid)
            if cur in (None, "LOCKED"):
                prereqs = direct_prereqs.get(cid, [])
                if all(p in mastered for p in prereqs):  # roots (no prereqs) included
                    await self.repo.upsert_node_state(user_id, cid, gv, "AVAILABLE")
                    if cur == "LOCKED":
                        unlocked.append(c.name)
        return unlocked
