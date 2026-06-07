"""
Assessment engine orchestration.

Ties together the pure placement logic (assessment_walk), the Gemini wrapper
(assessment_llm), and persistence (assessment_repo). Implements Section D of
the system design and the atomic /complete workflow from AGENT.md:

    score -> seed concept_mastery -> seed user_concept_state
          -> generate Learning DNA -> store DNA -> return.

The caller (API layer) owns the DB transaction boundary: it commits on success
and rolls back on any exception, giving /complete its all-or-nothing guarantee.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from app.models.assessment import Assessment, AssessmentResponse
from app.models.question import GeneratedQuestion
from app.models.learner import LearningDNA
from app.repositories.assessment_repo import AssessmentRepository
from app.services.assessment_llm import AssessmentLLM, PROMPT_VERSION
from app.services import assessment_walk as walk
from app.schemas.assessment import (
    QuestionDTO, ProgressDTO, StartAssessmentResponse,
    SubmitResponseRequest, SubmitResponseResponse, ResponseResultDTO,
    AssessmentResultDTO, AssessmentSummaryDTO, OutcomeDTO,
)

logger = logging.getLogger(__name__)

# Free-text correctness >= this counts as a tier pass for escalation.
PASS_THRESHOLD = 0.6


class AssessmentService:
    def __init__(self, repo: AssessmentRepository, llm: AssessmentLLM | None = None):
        self.repo = repo
        self.llm = llm or AssessmentLLM()

    # ---- helpers ------------------------------------------------------------

    @staticmethod
    def _bloom_for(concept, tier: str) -> str:
        meta = getattr(concept, "metadata_", None) or {}
        if isinstance(meta, dict) and meta.get("bloom_level"):
            return str(meta["bloom_level"])
        if isinstance(meta, dict) and meta.get("bloom_target"):
            return str(meta["bloom_target"])
        return walk.TIER_BLOOM[tier]

    async def _generate_and_store_question(self, concept, tier: str) -> GeneratedQuestion:
        qtype = tier  # tiers map 1:1 onto question_type enum values
        difficulty = walk.TIER_DIFFICULTY[tier]
        bloom = self._bloom_for(concept, tier)
        out = await self.llm.generate_question(
            concept_name=concept.name,
            concept_summary=concept.summary,
            difficulty=difficulty,
            bloom_level=bloom,
            question_type=qtype,
        )
        answer_key = {
            "options": out.options or [],
            "correct_option": out.correct_option,
            "expected_answer": out.expected_answer,
            "hints": out.hints or [],
            "bloom_level": bloom,
        }
        question = GeneratedQuestion(
            concept_id=concept.id,
            question_type=qtype,
            question_source="GENERATED",
            difficulty_level=walk.TIER_DIFFICULTY_LEVEL[tier],
            question_text=out.question,
            answer_key=answer_key,
            explanation=out.explanation or "",
            generation_model=self.llm.model_name,
            generation_version=PROMPT_VERSION,
        )
        await self.repo.create_question(question)
        return question

    @staticmethod
    def _question_dto(question: GeneratedQuestion, concept) -> QuestionDTO:
        ak = question.answer_key or {}
        return QuestionDTO(
            id=str(question.id),
            concept_id=str(question.concept_id),
            concept_name=concept.name,
            question_type=question.question_type,
            difficulty_level=question.difficulty_level,
            bloom_level=str(ak.get("bloom_level", "")),
            question_text=question.question_text,
            options=list(ak.get("options") or []),
        )

    @staticmethod
    def _progress(concept_total: int, responses) -> ProgressDTO:
        resolved = len({r.concept_id for r in responses})
        return ProgressDTO(
            concepts_total=concept_total,
            concepts_resolved=resolved,
            questions_answered=len(responses),
        )

    async def _load_graph(self, book_id: str):
        gv = await self.repo.get_active_graph_version(book_id)
        if gv is None:
            raise HTTPException(status_code=409, detail="Knowledge graph not built for this book yet.")
        concepts = await self.repo.get_concepts(book_id, gv)
        if not concepts:
            raise HTTPException(status_code=409, detail="No concepts found for this book's graph.")
        edges = await self.repo.get_prerequisite_edges(book_id, gv)
        edge_tuples = [(str(e.from_concept_id), str(e.to_concept_id)) for e in edges]
        return gv, concepts, edge_tuples

    @staticmethod
    def _to_walk_responses(db_responses, qtype_by_id):
        return [
            walk.Response(
                concept_id=str(r.concept_id),
                question_type=qtype_by_id[str(r.question_id)],
                is_correct=r.is_correct,
            )
            for r in db_responses
        ]

    # ---- public API ---------------------------------------------------------

    async def start_assessment(self, user_id: str, book_id: str) -> StartAssessmentResponse:
        if not await self.repo.is_enrolled(user_id, book_id):
            raise HTTPException(status_code=404, detail="Book not found in your library.")

        _gv, concepts, edges = await self._load_graph(book_id)
        concept_ids = [str(c.id) for c in concepts]
        by_id = {str(c.id): c for c in concepts}

        assessment = Assessment(
            user_id=user_id,
            book_id=book_id,
            assessment_type="INITIAL",
            status="IN_PROGRESS",
            started_at=datetime.now(timezone.utc),
        )
        await self.repo.create_assessment(assessment)

        nxt = walk.next_question(concept_ids, edges, [])
        if nxt is None:
            # Empty/degenerate graph — nothing to ask.
            return StartAssessmentResponse(
                assessment_id=str(assessment.id),
                question=None,
                progress=self._progress(len(concept_ids), []),
                completed=True,
            )

        concept = by_id[nxt.concept_id]
        question = await self._generate_and_store_question(concept, nxt.tier)
        return StartAssessmentResponse(
            assessment_id=str(assessment.id),
            question=self._question_dto(question, concept),
            progress=self._progress(len(concept_ids), []),
            completed=False,
        )

    async def submit_response(self, user_id: str, assessment_id: str,
                              req: SubmitResponseRequest) -> SubmitResponseResponse:
        assessment = await self.repo.get_assessment(assessment_id)
        if not assessment or str(assessment.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Assessment not found.")
        if assessment.status != "IN_PROGRESS":
            raise HTTPException(status_code=409, detail="Assessment is not in progress.")

        question = await self.repo.get_question(req.question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found.")

        # Idempotency: one response per question. Re-answering would corrupt the
        # tier count (and therefore placement), so reject duplicates.
        existing = await self.repo.get_responses(assessment_id)
        if any(str(r.question_id) == req.question_id for r in existing):
            raise HTTPException(status_code=409, detail="This question has already been answered.")

        _gv, concepts, edges = await self._load_graph(str(assessment.book_id))
        by_id = {str(c.id): c for c in concepts}
        concept = by_id.get(str(question.concept_id))
        if concept is None:
            raise HTTPException(status_code=409, detail="Question does not belong to this book's graph.")

        # --- grade ----------------------------------------------------------
        ak = question.answer_key or {}
        is_correct, correctness, score, feedback = await self._grade(question, concept, req.answer, ak)

        await self.repo.create_response(AssessmentResponse(
            assessment_id=assessment.id,
            concept_id=concept.id,
            question_id=question.id,
            confidence_level=req.confidence_level,
            response={"answer": req.answer},
            is_correct=is_correct,
            response_time_seconds=req.response_time_seconds,
        ))

        branch_stopped = (question.question_type == "MCQ" and not is_correct)

        # --- compute next ----------------------------------------------------
        db_responses = await self.repo.get_responses(assessment_id)
        qids = {str(r.question_id) for r in db_responses}
        qtype_by_id = {req.question_id: question.question_type}
        for qid in qids:
            if qid not in qtype_by_id:
                q = await self.repo.get_question(qid)
                if q:
                    qtype_by_id[qid] = q.question_type
        walk_responses = self._to_walk_responses(db_responses, qtype_by_id)

        concept_ids = [str(c.id) for c in concepts]
        nxt = walk.next_question(concept_ids, edges, walk_responses)

        mcq_option = ak.get("correct_option")
        result = ResponseResultDTO(
            is_correct=is_correct,
            correctness=correctness,
            score=score,
            feedback=feedback,
            explanation=question.explanation or "",
            correct_answer=str(ak.get("expected_answer", "")),
            correct_option=mcq_option if (question.question_type == "MCQ" and isinstance(mcq_option, int)) else None,
            branch_stopped=branch_stopped,
        )
        progress = self._progress(len(concept_ids), db_responses)

        if nxt is None:
            return SubmitResponseResponse(result=result, next_question=None,
                                          progress=progress, completed=True)

        next_concept = by_id[nxt.concept_id]
        next_q = await self._generate_and_store_question(next_concept, nxt.tier)
        return SubmitResponseResponse(
            result=result,
            next_question=self._question_dto(next_q, next_concept),
            progress=progress,
            completed=False,
        )

    async def _grade(self, question, concept, answer: str, ak: dict):
        """Returns (is_correct, correctness, score, feedback)."""
        if question.question_type == "MCQ":
            correct_idx = ak.get("correct_option")
            try:
                chosen = int(str(answer).strip())
            except (TypeError, ValueError):
                chosen = -1
            is_correct = (correct_idx is not None and chosen == int(correct_idx))
            return (
                is_correct,
                "correct" if is_correct else "incorrect",
                1.0 if is_correct else 0.0,
                question.explanation or "",
            )
        # Free-text: LLM evaluation with deterministic fallback.
        try:
            ev = await self.llm.evaluate_answer(
                concept_name=concept.name,
                question=question.question_text,
                expected_answer=str(ak.get("expected_answer", "")),
                student_answer=answer,
            )
            is_correct = ev.correctness == "correct" or ev.score >= PASS_THRESHOLD
            return is_correct, ev.correctness, float(ev.score), ev.feedback or ""
        except Exception as e:  # noqa: BLE001
            logger.warning("Evaluator failed, using deterministic fallback: %s", e)
            expected = str(ak.get("expected_answer", "")).strip().lower()
            is_correct = bool(expected) and answer.strip().lower() == expected
            return (
                is_correct,
                "correct" if is_correct else "incorrect",
                1.0 if is_correct else 0.0,
                "",
            )

    async def complete_assessment(self, user_id: str, assessment_id: str) -> AssessmentResultDTO:
        assessment = await self.repo.get_assessment(assessment_id)
        if not assessment or str(assessment.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Assessment not found.")
        if assessment.status == "COMPLETED":
            return await self.get_results(user_id, assessment_id)
        if assessment.status != "IN_PROGRESS":
            raise HTTPException(status_code=409, detail="Assessment cannot be completed.")

        gv, concepts, edges = await self._load_graph(str(assessment.book_id))
        by_id = {str(c.id): c for c in concepts}
        concept_ids = [str(c.id) for c in concepts]

        db_responses = await self.repo.get_responses(assessment_id)
        qtype_by_id = {}
        for r in db_responses:
            qid = str(r.question_id)
            if qid not in qtype_by_id:
                q = await self.repo.get_question(qid)
                qtype_by_id[qid] = q.question_type if q else "MCQ"
        walk_responses = self._to_walk_responses(db_responses, qtype_by_id)

        outcomes = walk.compute_outcomes(concept_ids, edges, walk_responses)

        # 1-2. Seed assessment_outcomes + concept_mastery + user_concept_state.
        for o in outcomes:
            await self.repo.upsert_outcome(
                str(assessment.id), o.concept_id, o.mastery_estimate, o.placement_state)
            await self.repo.upsert_concept_mastery(
                user_id, o.concept_id, o.mastery_estimate, o.mastery_state)
            await self.repo.upsert_node_state(
                user_id, o.concept_id, gv, o.node_state)

        # 3. Best-effort Neo4j projection (Postgres is source of truth; a Neo4j
        #    outage must not break completion — eventually consistent per AGENT.md).
        try:
            from app.services.neo4j_projection import project_book_graph, project_user_state
            concept_dicts = [{"id": str(c.id), "name": c.name, "difficulty": c.difficulty_level}
                             for c in concepts]
            await project_book_graph(str(assessment.book_id), concept_dicts, edges)
            await project_user_state(
                user_id,
                [{"concept_id": o.concept_id, "score": o.mastery_estimate, "state": o.placement_state}
                 for o in outcomes],
                [],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Neo4j projection skipped at assessment complete: %s", e)

        # 4-5. Generate + store Learning DNA (deterministic fallback on failure).
        dna_data = await self._build_dna(user_id, assessment, by_id, outcomes, db_responses)
        next_version = await self.repo.next_dna_version(user_id)
        await self.repo.deactivate_active_dna(user_id)
        await self.repo.create_dna(LearningDNA(
            user_id=user_id,
            dna_version=next_version,
            dna_data=dna_data,
            is_active=True,
        ))

        # Finalize the assessment record.
        total = len(db_responses)
        mastered = sum(1 for o in outcomes if o.placement_state == "MASTERED")
        score_pct = round(100.0 * mastered / len(outcomes), 2) if outcomes else 0.0
        assessment.status = "COMPLETED"
        assessment.completed_at = datetime.now(timezone.utc)
        # chk_total_questions requires NULL or > 0 (0 answers is a valid early complete).
        assessment.total_questions = total if total > 0 else None
        assessment.score_percentage = score_pct

        return self._result_dto(assessment, by_id, outcomes, dna_data)

    async def _build_dna(self, user_id, assessment, by_id, outcomes, db_responses) -> dict:
        results = [
            {
                "concept": by_id[o.concept_id].name if o.concept_id in by_id else o.concept_id,
                "mastery_estimate": o.mastery_estimate,
                "placement_state": o.placement_state,
            }
            for o in outcomes
        ]
        confident_wrong = sum(
            1 for r in db_responses
            if (r.confidence_level or 0) >= 4 and not r.is_correct
        )
        confidence_summary = (
            f"{confident_wrong} concept(s) answered confidently but incorrectly "
            f"(high-value revision targets)."
        )
        book_title = ""  # not required by the prompt; results carry concept names
        try:
            out = await self.llm.generate_dna(book_title, results, confidence_summary)
            data = out.model_dump()
            data["schema_version"] = "1.0.0"
            data["prompt_version"] = PROMPT_VERSION
            data["generated_at"] = datetime.now(timezone.utc).isoformat()
            return data
        except Exception as e:  # noqa: BLE001
            logger.warning("DNA generation failed, using deterministic fallback: %s", e)
            return self._fallback_dna(by_id, outcomes, confidence_summary)

    @staticmethod
    def _fallback_dna(by_id, outcomes, confidence_summary) -> dict:
        strengths, weaknesses = [], []
        for o in outcomes:
            name = by_id[o.concept_id].name if o.concept_id in by_id else o.concept_id
            if o.mastery_estimate >= 0.85:
                strengths.append({"area": name, "evidence": f"mastery {o.mastery_estimate:.2f}"})
            elif o.mastery_estimate < 0.45:
                weaknesses.append({"area": name, "evidence": f"mastery {o.mastery_estimate:.2f}"})
        return {
            "schema_version": "1.0.0",
            "prompt_version": PROMPT_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "misconceptions": [],
            "recommended_focus_areas": [
                {"area": w["area"], "reason": "low placement mastery"} for w in weaknesses[:5]
            ],
            "confidence_profile": confidence_summary,
            "learning_path_explanation": (
                "Generated from placement scores: focus first on the weakest concepts, "
                "then unlock dependents as prerequisites are mastered."
            ),
            "fallback": True,
        }

    async def get_results(self, user_id: str, assessment_id: str) -> AssessmentResultDTO:
        assessment = await self.repo.get_assessment(assessment_id)
        if not assessment or str(assessment.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Assessment not found.")

        _gv, concepts, _edges = await self._load_graph(str(assessment.book_id))
        by_id = {str(c.id): c for c in concepts}

        db_outcomes = await self.repo.get_outcomes(assessment_id)
        outcomes = [
            walk.ConceptOutcome(
                concept_id=str(o.concept_id), tested=True, tiers_passed=0,
                mastery_estimate=float(o.mastery_estimate),
                placement_state=o.placement_state,
                mastery_state="", node_state="",
            )
            for o in db_outcomes
        ]
        active_dna = await self.repo.get_active_dna(user_id)
        dna_data = active_dna.dna_data if active_dna else None
        return self._result_dto(assessment, by_id, outcomes, dna_data)

    @staticmethod
    def _result_dto(assessment, by_id, outcomes, dna_data) -> AssessmentResultDTO:
        summary = AssessmentSummaryDTO()
        out_dtos = []
        for o in outcomes:
            ps = o.placement_state
            if ps == "MASTERED":
                summary.mastered += 1
            elif ps == "READY":
                summary.ready += 1
            elif ps == "LEARNING":
                summary.learning += 1
            elif ps == "WEAK":
                summary.weak += 1
            else:
                summary.unknown += 1
            if getattr(o, "node_state", "") == "LOCKED":
                summary.locked += 1
            out_dtos.append(OutcomeDTO(
                concept_id=o.concept_id,
                concept_name=by_id[o.concept_id].name if o.concept_id in by_id else o.concept_id,
                mastery_estimate=float(o.mastery_estimate),
                placement_state=ps,
            ))
        score = float(assessment.score_percentage) if assessment.score_percentage is not None else None
        return AssessmentResultDTO(
            assessment_id=str(assessment.id),
            status=assessment.status,
            score_percentage=score,
            summary=summary,
            outcomes=out_dtos,
            dna=dna_data,
        )
