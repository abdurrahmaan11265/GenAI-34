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

from sqlalchemy import text

from app.repositories.graph_repo import GraphRepository
from app.repositories.assessment_repo import AssessmentRepository
from app.repositories.fsrs_repo import FsrsRepository
from app.services import fsrs as fsrs_engine
from app.services import mastery_engine




class ProgressService:
    def __init__(self, graph_repo: GraphRepository, assess_repo: AssessmentRepository,
                 fsrs_repo: FsrsRepository | None = None):
        self.graph = graph_repo
        self.repo = assess_repo
        self.fsrs = fsrs_repo or FsrsRepository(graph_repo.session)

    async def complete_concept(self, user_id: str, book_id: str, concept_id: str,
                               source: str = "LESSON") -> List[str]:
        """Mark a concept mastered and unlock dependents whose prerequisites are
        now all mastered. Returns the titles of newly-unlocked concepts."""
        gv = await self.graph.active_graph_version(book_id)
        if gv is None:
            return []

        # 1. Deduplication Guard: Check content_completions
        bonus_awarded = False
        row = await self.fsrs.session.execute(
            text("""
                SELECT 1 FROM content_completions 
                WHERE user_id = :u AND content_type = 'concept' 
                  AND content_id = :c AND content_version = :v
            """),
            {"u": user_id, "c": concept_id, "v": gv}
        )
        if row.first():
            bonus_awarded = True

        # 2. Get prior state
        prev_m, prev_r = await self._current_state(user_id, concept_id)

        # 3. Call Mastery Engine
        event_name = "lesson_complete" if source == "LESSON" else "quiz_complete"
        result = mastery_engine.update_mastery(
            mastery=prev_m,
            retention=prev_r,
            event=event_name,
            hint_used=False,
            bonus_eligible=not bonus_awarded
        )

        # 4. Persist Bonus if awarded
        if result.bonus_awarded:
            await self.fsrs.session.execute(
                text("""
                    INSERT INTO content_completions (user_id, content_type, content_id, content_version)
                    VALUES (:u, 'concept', :c, :v)
                    ON CONFLICT DO NOTHING
                """),
                {"u": user_id, "c": concept_id, "v": gv}
            )

        # 5. Routing -> Node State
        if result.routing == "unlock_dependents":
            mastery_state = "MASTERED"
            node_state = "MASTERED"
        elif result.routing in ("practice", "continue"):
            mastery_state = "PRACTICING" if result.routing == "practice" else "LEARNING"
            node_state = "IN_PROGRESS"
        else:
            mastery_state = "LEARNING"
            node_state = "AVAILABLE"

        await self.repo.upsert_concept_mastery(
            user_id, concept_id, result.mastery, mastery_state, 
            source=source, retention_score=result.retention
        )
        await self.repo.upsert_node_state(user_id, concept_id, gv, node_state)

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
                    or masteries.get(str(c.id), 0.0) >= mastery_engine.MASTERY_THRESHOLD}
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

        # Enter the spaced-repetition cycle: first successful review schedules
        # the concept for future revision (only if not already tracked).
        if await self.fsrs.get_state(user_id, concept_id) is None:
            state, interval = fsrs_engine.review(fsrs_engine.init_state(), fsrs_engine.GRADE_GOOD)
            await self.fsrs.upsert_state(user_id, concept_id, state, interval)
        return unlocked

    async def record_review(self, user_id: str, book_id: str, concept_id: str, grade: int) -> dict:
        """Grade a spaced-repetition review: update FSRS schedule + mastery, and
        flip the node back to MASTERED on success (System Design G#31)."""
        gv = await self.graph.active_graph_version(book_id)
        before_row = await self.fsrs.get_state(user_id, concept_id)
        before = fsrs_engine.FsrsState(
            stability=before_row.stability, difficulty=before_row.difficulty,
            retrievability=before_row.retrievability,
            repetitions=before_row.repetitions, lapses=before_row.lapses,
        ) if before_row else fsrs_engine.init_state()

        after, interval = fsrs_engine.review(before, grade)
        await self.fsrs.upsert_state(user_id, concept_id, after, interval)
        await self.fsrs.log_review(user_id, concept_id, grade, before, after, source="REVISION")

        # Mastery update via the canonical mastery engine.
        prev_m, prev_r = await self._current_state(user_id, concept_id)
        event = "correct" if grade >= fsrs_engine.GRADE_GOOD else "wrong"
        result = mastery_engine.update_mastery(prev_m, prev_r, event)
        
        if result.routing == "unlock_dependents":
            mastery_state = "MASTERED"
            node_state = "MASTERED"
        elif result.routing in ("practice", "continue"):
            mastery_state = "PRACTICING" if result.routing == "practice" else "LEARNING"
            node_state = "IN_PROGRESS" if grade >= fsrs_engine.GRADE_GOOD else "DUE"
        else:
            mastery_state = "LEARNING"
            node_state = "DUE"

        await self.repo.upsert_concept_mastery(
            user_id, concept_id, result.mastery, mastery_state, 
            source="REVISION", retention_score=result.retention
        )
        await self.fsrs.log_mastery_event(
            user_id, concept_id, "REVISION", prev_m, result.mastery,
            f"revision grade {grade}"
        )

        # Node state updated based on routing.
        if gv is not None:
            await self.repo.upsert_node_state(user_id, concept_id, gv, node_state)

        return {
            "concept_id": concept_id, "grade": grade,
            "mastery": round(result.mastery, 4), "interval_days": interval,
            "stability": after.stability, "difficulty": after.difficulty,
        }

    async def _current_state(self, user_id: str, concept_id: str) -> tuple[float, float]:
        row = await self.fsrs.session.execute(
            text("SELECT mastery_score, retention_score FROM concept_mastery WHERE user_id = :u AND concept_id = :c"),
            {"u": user_id, "c": concept_id})
        r = row.first()
        return (float(r[0]), float(r[1])) if r else (0.0, 0.0)
