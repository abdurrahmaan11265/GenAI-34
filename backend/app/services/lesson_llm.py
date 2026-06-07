"""
Gemini wrapper for the learning layer: lesson generation, Socratic tutoring,
and progressive hints (pls2 #7, pls3 #10/#11). Async-friendly (runs the
synchronous google-genai client in a thread).
"""
from __future__ import annotations

import os
import json
import time
import asyncio
import logging
from typing import Any, List

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.llm import LessonOutput, TutorOutput, HintOutput

logger = logging.getLogger(__name__)
PROMPT_VERSION = "v1"


class LessonLLM:
    def __init__(self, model_name: str | None = None):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured.")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-2.5-flash-lite"
        self.prompts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../prompts"))

    def _load(self, filename: str) -> str:
        with open(os.path.join(self.prompts_dir, filename), "r", encoding="utf-8") as f:
            return f.read()

    def _call_sync(self, prompt: str, schema: Any, temperature: float) -> Any:
        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        )
        for attempt in range(3):
            try:
                resp = self.client.models.generate_content(
                    model=self.model_name, contents=prompt, config=config)
                if resp.parsed is None:
                    raise ValueError(f"Empty structured output. Raw: {resp.text}")
                return resp.parsed
            except Exception as e:  # noqa: BLE001
                if attempt == 2:
                    logger.error("LessonLLM call failed: %s", e)
                    raise
                wait = (20 if ("429" in str(e) or "quota" in str(e).lower()) else 4) * (attempt + 1)
                time.sleep(wait)

    async def _call(self, prompt: str, schema: Any, temperature: float) -> Any:
        return await asyncio.to_thread(self._call_sync, prompt, schema, temperature)

    async def generate_lesson(self, concept_name: str, concept_summary: str, source_text: str,
                              mastery: float, misconceptions: List[str], target_bloom: str) -> LessonOutput:
        prompt = (
            self._load("lesson_generator.md")
            .replace("{{CONCEPT_NAME}}", concept_name)
            .replace("{{CONCEPT_SUMMARY}}", concept_summary or "")
            .replace("{{SOURCE_TEXT}}", source_text or "(no source text available)")
            .replace("{{MASTERY}}", f"{mastery:.2f}")
            .replace("{{MISCONCEPTIONS}}", json.dumps(misconceptions or []))
            .replace("{{TARGET_BLOOM}}", target_bloom)
        )
        return await self._call(prompt, LessonOutput, temperature=0.5)

    async def tutor_turn(self, concept_name: str, concept_summary: str, source_text: str,
                         mastery: float, conversation_history: str, hint_level: int,
                         student_message: str) -> TutorOutput:
        prompt = (
            self._load("socratic_tutor.md")
            .replace("{{CONCEPT_NAME}}", concept_name)
            .replace("{{CONCEPT_SUMMARY}}", concept_summary or "")
            .replace("{{SOURCE_TEXT}}", source_text or "(no source text available)")
            .replace("{{MASTERY}}", f"{mastery:.2f}")
            .replace("{{CONVERSATION_HISTORY}}", conversation_history or "(start of conversation)")
            .replace("{{HINT_LEVEL}}", str(hint_level))
            .replace("{{STUDENT_MESSAGE}}", student_message)
        )
        return await self._call(prompt, TutorOutput, temperature=0.6)

    async def generate_hint(self, concept_name: str, question: str, hint_level: int,
                            previous_hints: List[str]) -> HintOutput:
        prompt = (
            self._load("hint_generator.md")
            .replace("{{CONCEPT_NAME}}", concept_name)
            .replace("{{QUESTION}}", question)
            .replace("{{HINT_LEVEL}}", str(hint_level))
            .replace("{{PREVIOUS_HINTS}}", json.dumps(previous_hints or []))
        )
        return await self._call(prompt, HintOutput, temperature=0.4)
