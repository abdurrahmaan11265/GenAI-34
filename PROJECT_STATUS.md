# Lexis - Project Status Tracking

This document maintains the current state of the Lexis Adaptive Book Learning Platform. It is broken down into what is fully complete, what is mocked, what is partially complete, and what remains untouched.

## ✅ E2E Done & Working Perfectly
- **Authentication System**: 
  - FastAPI backend endpoints (`/auth/register`, `/auth/login`) with robust `bcrypt` password hashing.
  - Next.js frontend integration using NextAuth, securely storing and forwarding the FastAPI JWT token via `Authorization: Bearer` headers.
- **Database Core (PostgreSQL)**: 
  - Complete schema setup via `schema.sql`.
  - SQLAlchemy Async engine and session management.
  - Fully mapped models for `User`, `LearnerProfile`, `Book`, `UserBook`, `GraphVersion`, and `GraphBuildJob`.
  - Fixed PostgreSQL strictly-typed custom `ENUM` mappings for SQLAlchemy.
- **Library Dashboard**: 
  - The UI accurately retrieves the user's real books from PostgreSQL (`GET /api/v1/books`).
  - NextAuth correctly protects routes and automatically redirects unauthenticated users.
- **Book Upload & Background Processing**:
  - Split upload into two steps: Metadata Creation (`POST /books`) -> File Upload (`POST /books/{id}/upload`).
  - Resolved SQLAlchemy -> PostgreSQL mismatch errors by adding missing `visibility` and `updated_at` columns.
  - Dropped the `NOT NULL` constraint on `file_url` via `psql` to allow 2-step inserts.
  - The React frontend successfully polls `/api/v1/books/{book_id}/status`, correctly reflecting the `PARSING` -> `EXTRACTING_CONCEPTS` -> `BUILDING_GRAPH` -> `COMPLETED` pipeline.
- **Pre-AI Basic CRUD & Profile Management**:
  - Global standardized error handling (DTO) for `StarletteHTTPException` and `RequestValidationError`.
  - Added a `GET /health` endpoint for infrastructure checks.
  - Added full Profile Management logic (`GET /api/v1/users/me` and `PATCH /api/v1/users/me`) mirroring the frontend `UserDTO`.
  - Restructured DB layout to merge standard profile settings directly into the `users` table instead of an arbitrary relation.
  - Implemented `GET /api/v1/books/{id}` and `DELETE /api/v1/books/{id}` with strict library ownership validation.
- **PDF Upload & Knowledge Graph Pipeline (Real LLM Extraction)**:
  - Background ingestion worker correctly claims jobs.
  - PyMuPDF text extraction with intelligent chunking.
  - Real Gemini (via `google-genai`) integration for extracting Concept nodes and Prerequisite edges.
  - Idempotent database insertion with advanced conflict handling (`ON CONFLICT DO NOTHING`) across `source_chunks`, `concepts`, and `concept_edges`.
  - Frontend properly polls and displays the real generated Knowledge Graph (D3.js).

## ✅ Learner-Model Backend (branch `feat/assessment-engine`)
The full P0 learner-model pipeline is implemented backend-to-DB, each engine
contract-first with unit tests and a golden-dataset eval harness (39 tests pass;
all 9 GenAI prompt tasks meet their PEOS targets).
- **Assessment Engine + Learning DNA**: adaptive topological DAG walk (MCQ→theory→applied, branch-stop, confidence), atomic `/complete` seeding `concept_mastery` + `user_concept_state` + Gemini DNA. (`/api/v1/assessments`)
- **Graph Reveal**: per-user four-state graph overlay. (`GET /books/{id}/knowledge-graph`)
- **Curriculum + Daily Plan**: deterministic, graph-decided; revise/learn/both. (`/books/{id}/curriculum`, `/daily-plan`)
- **Lesson + Socratic Tutor + Hints**: Gemini lessons grounded in source chunks; tutor with 0% answer-leakage + misconception capture; completion unlocks dependents via the Progress engine. (`/api/v1/lessons/...`)
- **Mastery + FSRS + Revision**: canonical mastery engine (`mastery_engine.md`) + FSRS scheduler; due detection + review grading. (`GET /books/{id}/revision`, `POST /books/{id}/concepts/{cid}/review`)
- **Dashboard / Stats / Streaks**: aggregation + activity-derived streaks. (`GET /dashboard`)
- **Notifications**: now derived live from learner state (no longer a `[]` stub).
- **Neo4j projection**: Postgres→Neo4j `PREREQUISITE_OF` / `HAS_MASTERY` / `CURRENTLY_LEARNING` (best-effort). (`POST /books/{id}/graph/sync-neo4j`)
- **Eval harness**: `backend/evals/` golden datasets + scorers + `python -m evals.run_evals`.

## 🚧 Incomplete / In Progress
- **File Storage**: uploaded PDFs stored on local disk (`uploads/`); needs S3 for prod.
- **Ingestion edge inference is O(n²) Gemini calls** — fine for small books, needs batching before large books.
- **Frontend** for the new engines (assessment, course view, lesson/tutor, revision, dashboard, graph verification, settings) — APIs are ready to wire.

## 📝 Known issues for the team
- **`schema.sql` lines 2154–2176** use escaped quotes (`\'PENDING\'`) → `upload_status` enum + `book_uploads` fail on a fresh apply (patched in dev DB only).
- **No Alembic migrations yet** — schema changes are manual SQL; this caused dev-DB drift.
