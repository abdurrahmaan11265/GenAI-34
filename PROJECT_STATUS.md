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

## 🎭 Mocked (Working UI, Simulated Backend)
- **PDF Upload & Knowledge Graph Pipeline**: 
  - *Reality*: No real PDF text extraction, chunking, or LLM calls are happening yet.
- **Notifications**:
  - `GET /api/v1/notifications` exists but returns a static `[]` to allow the React `Promise.all` on the Library page to succeed without crashing.

## 🚧 Incomplete / In Progress
- **Neo4j Integration**: 
  - Basic connector exists (`app/core/neo4j.py`), but the actual Knowledge Graph querying and writing is pending implementation by the other developer.
  - **File Storage**:
  - Uploaded PDFs are currently received by FastAPI but discarded in memory. They need to be stored locally or pushed to an S3-compatible storage bucket.

## 📝 Untouched / Needs to be Done (Roadmap)
- **Assessment Engine (PR 4)**:
  - Generate quizzes (multiple choice, true/false) based on the user's current node in the Knowledge Graph.
  - Store assessment results in the database.
- **Mastery Engine & FSRS (PR 5)**:
  - Calculate "Due Today" reviews using the Free Spaced Repetition Scheduler algorithm.
  - Track confidence intervals and knowledge decay for individual nodes.
- **Gemini Tutor Chat**:
  - The interactive sidebar where a user can ask questions and the AI responds using Retrieval-Augmented Generation (RAG) over the Neo4j Knowledge Graph.
- **Graph Verification UI**:
  - The screen where users review the AI-extracted knowledge graph (nodes and edges) and approve it before studying.
