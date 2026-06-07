"""
Curriculum + Daily Plan orchestration (System Design Section G).

Deterministic: the learning order and gating come entirely from the prerequisite
DAG + the learner's mastery state (curriculum_planner). The graph decides the
curriculum; this service just loads state, runs the planner, and persists.
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import HTTPException

from app.models.curriculum import CurriculumPlan
from app.repositories.graph_repo import GraphRepository
from app.repositories.curriculum_repo import CurriculumRepository
from app.services import curriculum_planner as planner
from app.schemas.curriculum import CurriculumItemDTO, CurriculumDTO, DailyPlanDTO


class CurriculumService:
    def __init__(self, graph_repo: GraphRepository, curr_repo: CurriculumRepository):
        self.graph = graph_repo
        self.repo = curr_repo

    async def _load_items(self, user_id: str, book_id: str):
        if not await self.graph.is_enrolled(user_id, book_id):
            raise HTTPException(status_code=404, detail="Book not found in your library.")
        gv = await self.graph.active_graph_version(book_id)
        if gv is None:
            raise HTTPException(status_code=409, detail="Knowledge graph not built for this book yet.")
        concepts = await self.graph.concepts(book_id, gv)
        edges = await self.graph.prerequisite_edges(book_id, gv)
        states = await self.graph.node_states(user_id, book_id)
        masteries = {cid: score for cid, (score, _lr) in (await self.graph.masteries(user_id, book_id)).items()}

        concept_dicts = [
            {
                "id": str(c.id), "title": c.name, "estimated_minutes": c.estimated_minutes,
                "subtopics": (c.metadata_ or {}).get("subtopics", []) if isinstance(c.metadata_, dict) else [],
            }
            for c in concepts
        ]
        edge_tuples = [(str(e.from_concept_id), str(e.to_concept_id)) for e in edges]
        items = planner.build_curriculum(concept_dicts, edge_tuples, states, masteries)
        return items

    @staticmethod
    def _item_dto(it: planner.CurriculumItem) -> CurriculumItemDTO:
        return CurriculumItemDTO(
            conceptId=it.concept_id, title=it.title, orderIndex=it.order_index,
            state=it.state, mastery=it.mastery, estimatedMinutes=it.estimated_minutes,
            unmetPrerequisites=it.unmet_prerequisites, subtopics=it.subtopics,
        )

    async def generate_curriculum(self, user_id: str, book_id: str) -> CurriculumDTO:
        items = await self._load_items(user_id, book_id)
        version = await self.repo.next_version(user_id, book_id)
        assessment_id = await self.repo.latest_assessment_id(user_id, book_id)
        curriculum_json = [asdict(it) for it in items]
        await self.repo.create_plan(CurriculumPlan(
            user_id=user_id, book_id=book_id, version=version,
            curriculum_json=curriculum_json, generated_from_assessment=assessment_id,
        ))
        return self._to_dto(book_id, version, items)

    async def get_curriculum(self, user_id: str, book_id: str) -> CurriculumDTO:
        plan = await self.repo.latest_plan(user_id, book_id)
        if plan is None:
            # Generate-on-read so the course view always has data post-assessment.
            return await self.generate_curriculum(user_id, book_id)
        items = [
            planner.CurriculumItem(
                concept_id=i["concept_id"], title=i["title"], order_index=i["order_index"],
                state=i["state"], mastery=i["mastery"], estimated_minutes=i["estimated_minutes"],
                unmet_prerequisites=i.get("unmet_prerequisites", []),
            )
            for i in plan.curriculum_json
        ]
        return self._to_dto(book_id, plan.version, items)

    async def get_daily_plan(self, user_id: str, book_id: str) -> DailyPlanDTO:
        items = await self._load_items(user_id, book_id)  # live state
        by_id = {it.concept_id: it for it in items}
        cap = await self.repo.daily_new_node_cap(user_id)

        # Due reviews are always live. The "learn" set is frozen for the day
        # (soft focus): we persist today's chosen concepts and only regenerate a
        # fresh batch once every one of them has been mastered.
        due = [it for it in items if it.state == "DUE"]
        today = await self.repo.get_today_plan(user_id, book_id)

        learn_items = []
        if today is not None:
            for cid in (today.learn_concept_ids or []):
                it = by_id.get(cid)
                if it and it.state in ("AVAILABLE", "IN_PROGRESS"):
                    learn_items.append(it)   # still pending → keep in today's focus

        if not learn_items:
            # No saved plan, or every item in it is done → regenerate a fresh batch.
            available = [it for it in items if it.state in ("AVAILABLE", "IN_PROGRESS")]
            learn_items = available[: max(0, cap)]
            await self.repo.save_today_plan(user_id, book_id, [it.concept_id for it in learn_items])

        if not due and not learn_items:
            mode = "all_caught_up"
        elif due and not learn_items:
            mode = "revise_only"
        elif learn_items and not due:
            mode = "learn_only"
        else:
            mode = "both"
        minutes = sum(it.estimated_minutes for it in due) + sum(it.estimated_minutes for it in learn_items)

        return DailyPlanDTO(
            bookId=book_id, mode=mode,
            revise=[self._item_dto(it) for it in due],
            learn=[self._item_dto(it) for it in learn_items],
            totalDue=len(due), totalNew=len(learn_items),
            estimatedMinutes=minutes,
        )

    def _to_dto(self, book_id: str, version: int, items) -> CurriculumDTO:
        mastered = sum(1 for it in items if it.state == "MASTERED")
        return CurriculumDTO(
            bookId=book_id, version=version, totalConcepts=len(items),
            masteredConcepts=mastered, items=[self._item_dto(it) for it in items],
        )
