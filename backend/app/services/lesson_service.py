"""
Learning layer orchestration: lesson generation, Socratic tutoring, hints, and
lesson completion (System Design Section F).

Lessons are grounded in the concept's source chunks. The tutor never decides
mastery — completion routes through the Progress engine (AGENT.md writer rule).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from app.models.lesson import LessonSession, TutorInteraction
from app.repositories.lesson_repo import LessonRepository
from app.repositories.graph_repo import GraphRepository
from app.repositories.assessment_repo import AssessmentRepository
from app.services.lesson_llm import LessonLLM, PROMPT_VERSION
from app.services.progress_service import ProgressService
from app.schemas.lesson import (
    LessonContentDTO, LessonSessionDTO, TurnDTO,
    TutorResponseDTO, HintDTO, CompleteLessonDTO,
)

CONVERSATION_TURN_WINDOW = 8  # recent turns sent to the tutor for context


class LessonService:
    def __init__(self, repo: LessonRepository, graph_repo: GraphRepository,
                 assess_repo: AssessmentRepository, llm: LessonLLM | None = None):
        self.repo = repo
        self.graph = graph_repo
        self.assess = assess_repo
        self.llm = llm or LessonLLM()

    @staticmethod
    def _content_dto(content: dict) -> LessonContentDTO:
        return LessonContentDTO(
            introduction=content.get("introduction", ""),
            mentalModel=content.get("mental_model", ""),
            coreExplanation=content.get("core_explanation", ""),
            analogy=content.get("analogy", ""),
            workedExamples=content.get("worked_examples", []),
            commonMistakes=content.get("common_mistakes", []),
            practiceExercises=content.get("practice_exercises", []),
            summary=content.get("summary", ""),
            keyTakeaways=content.get("key_takeaways", []),
        )

    @staticmethod
    def _bloom_target(concept) -> str:
        meta = getattr(concept, "metadata_", None) or {}
        if isinstance(meta, dict) and (meta.get("bloom_target") or meta.get("bloom_level")):
            return str(meta.get("bloom_target") or meta.get("bloom_level"))
        return "apply"

    async def start_lesson(self, user_id: str, book_id: str, concept_id: str) -> LessonSessionDTO:
        if not await self.repo.is_enrolled(user_id, book_id):
            raise HTTPException(status_code=404, detail="Book not found in your library.")
        concept = await self.repo.get_concept(concept_id)
        if not concept or str(concept.book_id) != book_id:
            raise HTTPException(status_code=404, detail="Concept not found for this book.")

        source_text = await self.repo.get_source_text(concept_id)
        mastery = await self.repo.get_mastery(user_id, concept_id)
        lesson = await self.llm.generate_lesson(
            concept_name=concept.name, concept_summary=concept.summary,
            source_text=source_text, mastery=mastery, misconceptions=[],
            target_bloom=self._bloom_target(concept),
        )
        content = lesson.model_dump()
        sess = await self.repo.create_session(LessonSession(
            user_id=user_id, concept_id=concept_id, status="IN_PROGRESS",
            generated_content=content,
            generation_metadata={"model": self.llm.model_name, "prompt_version": PROMPT_VERSION,
                                 "graph_version": await self.graph.active_graph_version(book_id)},
            started_at=datetime.now(timezone.utc),
        ))
        gv = await self.graph.active_graph_version(book_id)
        if gv is not None:
            await self.assess.upsert_node_state(user_id, concept_id, gv, "IN_PROGRESS")

        return LessonSessionDTO(
            sessionId=str(sess.id), conceptId=concept_id, conceptTitle=concept.name,
            status=sess.status, content=self._content_dto(content), transcript=[],
        )

    async def _load_session_owned(self, user_id: str, session_id: str) -> LessonSession:
        sess = await self.repo.get_session(session_id)
        if not sess or str(sess.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Lesson session not found.")
        return sess

    async def get_lesson(self, user_id: str, session_id: str) -> LessonSessionDTO:
        sess = await self._load_session_owned(user_id, session_id)
        concept = await self.repo.get_concept(str(sess.concept_id))
        turns = await self.repo.get_turns(session_id)
        return LessonSessionDTO(
            sessionId=str(sess.id), conceptId=str(sess.concept_id),
            conceptTitle=concept.name if concept else "",
            status=sess.status, content=self._content_dto(sess.generated_content or {}),
            transcript=[TurnDTO(turnIndex=t.turn_index, userMessage=t.user_message,
                                assistantMessage=t.assistant_message, hintLevel=t.hint_level)
                        for t in turns],
        )

    async def tutor_turn(self, user_id: str, session_id: str, message: str,
                         hint_level: int, is_question: bool) -> TutorResponseDTO:
        sess = await self._load_session_owned(user_id, session_id)
        concept = await self.repo.get_concept(str(sess.concept_id))
        source_text = await self.repo.get_source_text(str(sess.concept_id))
        mastery = await self.repo.get_mastery(user_id, str(sess.concept_id))

        turns = await self.repo.get_turns(session_id)
        history = "\n".join(
            f"Student: {t.user_message}\nTutor: {t.assistant_message}"
            for t in turns[-CONVERSATION_TURN_WINDOW:]
        )
        out = await self.llm.tutor_turn(
            concept_name=concept.name, concept_summary=concept.summary,
            source_text=source_text, mastery=mastery,
            conversation_history=history, hint_level=hint_level, student_message=message,
        )

        question_id = None
        if is_question and message.strip():
            question_id = await self.repo.create_user_asked_question(str(sess.concept_id), message.strip())

        turn_index = len(turns)
        await self.repo.create_turn(TutorInteraction(
            lesson_session_id=sess.id, turn_index=turn_index,
            user_message=message, assistant_message=out.tutor_response,
            hint_level=hint_level, question_id=question_id, model_name=self.llm.model_name,
        ))
        return TutorResponseDTO(
            turnIndex=turn_index, tutorResponse=out.tutor_response,
            followUpQuestion=out.follow_up_question, hint=out.hint,
            reasoningPrompt=out.reasoning_prompt,
            misconceptionsDetected=out.misconceptions_detected,
            questionCaptured=question_id is not None,
        )

    async def hint(self, user_id: str, session_id: str, question: str, hint_level: int) -> HintDTO:
        sess = await self._load_session_owned(user_id, session_id)
        concept = await self.repo.get_concept(str(sess.concept_id))
        prev = [t.assistant_message for t in await self.repo.get_turns(session_id) if t.hint_level > 0]
        out = await self.llm.generate_hint(concept.name, question, hint_level, prev)
        return HintDTO(hintLevel=out.hint_level or hint_level, hint=out.hint, reason=out.reason)

    async def complete_lesson(self, user_id: str, session_id: str) -> CompleteLessonDTO:
        sess = await self._load_session_owned(user_id, session_id)
        if sess.status == "COMPLETED":
            # idempotent
            return CompleteLessonDTO(status="COMPLETED", unlockedConcepts=[])
        concept = await self.repo.get_concept(str(sess.concept_id))
        sess.status = "COMPLETED"
        sess.completed_at = datetime.now(timezone.utc)

        progress = ProgressService(self.graph, self.assess)
        unlocked = await progress.complete_concept(user_id, str(concept.book_id), str(sess.concept_id), source="LESSON")
        return CompleteLessonDTO(status="COMPLETED", unlockedConcepts=unlocked)
