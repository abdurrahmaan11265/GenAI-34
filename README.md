# Lexis AI

Lexis AI is an adaptive educational platform that transforms static textbooks into interactive, personalized learning graphs. It ingests educational material, extracts topological knowledge dependencies, and utilizes spaced repetition (FSRS) and Socratic tutoring to dynamically generate adaptive curriculums based on real-time learner mastery.

---

# Problem Statement

Traditional educational texts are strictly linear, assuming every learner starts with identical baseline knowledge and acquires understanding at the same rate. This linear progression is inefficient because learners often encounter prerequisite gaps—missing foundational concepts required to understand advanced topics—which leads to compounding confusion. Conversely, forcing learners to read material they have already mastered wastes time. Adaptive learning solves this by mapping the domain into a dependency graph, continuously measuring the learner's true retention, and dynamically routing them only to the optimal next concept.

---

# Solution Overview

Lexis AI replaces the linear book lifecycle with a dynamic, graph-driven learning engine.

```text
Upload Book
    │
    ▼
Knowledge Graph Extraction (Concepts & Prerequisites)
    │
    ▼
Diagnostic Assessment (Measure Baseline)
    │
    ▼
Curriculum Generation (Topological Sort)
    │
    ▼
Socratic Tutor (Active Learning)
    │
    ▼
Mastery Check (Quiz)
    │
    ▼
FSRS Spaced Repetition (Retention Tracking)
    │
    ▼
(Loop back to Curriculum Generation)
```

1. Books are converted into a structured Knowledge Graph of concepts and prerequisites.
2. Learners take an initial assessment to define their baseline mastery.
3. The engine generates a daily curriculum using a topological walk of unmastered graph nodes.
4. Learners interact with a Socratic Tutor anchored strictly to the book's text.
5. Mastery is validated via quizzes, updating the FSRS engine to track long-term retention decay.

---

# Core Features

## Book Ingestion
- **Purpose**: Converts raw PDF files into atomic text chunks.
- **Inputs**: PDF binary file.
- **Outputs**: Parsed text chunks stored in Postgres.
- **Key Technologies**: PyMuPDF.
- **Current Status**: Implemented and verified.

## Knowledge Graph Construction
- **Purpose**: Uses LLMs to extract concepts and their prerequisite relationships from chunks.
- **Inputs**: Text chunks.
- **Outputs**: Raw concepts, canonical concepts, and relationship edges.
- **Key Technologies**: Gemini 2.5 Flash, Postgres.
- **Current Status**: Implemented. Uses batching and resumable checkpoints (`raw_concepts` table lineage).

## Graph Validation
- **Purpose**: Ensures the generated knowledge graph is a valid Directed Acyclic Graph (DAG) for traversal.
- **Inputs**: Candidate relationships.
- **Outputs**: Validated graph with cycle-breaking repair.
- **Key Technologies**: Kahn's Algorithm.
- **Current Status**: Implemented. Formally detects and resolves cyclic dependencies.

## Adaptive Assessment
- **Purpose**: Calibrates the learner's baseline knowledge.
- **Inputs**: Graph topology, learner responses.
- **Outputs**: `LearningDNA` baseline, seeded `ConceptMastery` scores.
- **Key Technologies**: Gemini.
- **Current Status**: Implemented. Traverses the DAG dynamically based on right/wrong answers.

## Mastery Tracking
- **Purpose**: Maintains the true cognitive state of the learner per concept.
- **Inputs**: Assessment results, quiz completions, review outcomes.
- **Outputs**: Mastery scores (0.0 - 1.0) and retention decay models.
- **Key Technologies**: FSRS (Free Spaced Repetition Scheduler).
- **Current Status**: Implemented. Integrates heavily with the FSRS algorithm.

## Curriculum Generation
- **Purpose**: Determines exactly what the learner should study next.
- **Inputs**: Graph prerequisites, current mastery states.
- **Outputs**: A deterministic, topologically sorted `DailyPlan`.
- **Key Technologies**: Neo4j (Cypher traversals), Postgres.
- **Current Status**: Implemented. Generates isolated daily focuses based on strict prerequisite clearance.

## Socratic Tutor
- **Purpose**: Facilitates active learning without passively giving away answers.
- **Inputs**: Source chunks, user queries, concept context.
- **Outputs**: Interrogative hints and guided explanations.
- **Key Technologies**: Gemini 2.5 Flash, RAG.
- **Current Status**: Implemented. Employs 4-level hint generation and persistent sessions.

## FSRS Spaced Repetition
- **Purpose**: Schedules reviews to interrupt the forgetting curve.
- **Inputs**: Time elapsed, mastery scores, review difficulty.
- **Outputs**: Next optimal review date, updated retention probability.
- **Key Technologies**: FSRS algorithm in Python.
- **Current Status**: Implemented. Determines `DUE` states in the learning graph overlay.

## Analytics
- **Purpose**: Quantifies learning momentum and consistency.
- **Inputs**: Daily completions, session logs.
- **Outputs**: Global streaks, book-specific streaks, daily activity metrics.
- **Key Technologies**: Postgres (aggregation queries).
- **Current Status**: Implemented.

---

# System Architecture

The system utilizes a modular monolith Backend supported by asynchronous worker processes, heavily decoupled databases, and a modern React Frontend.

```text
┌─────────────────┐       ┌─────────────────┐
│                 │       │                 │
│  Next.js 15 UI  │◄─────►│   FastAPI API   │
│                 │  HTTP │                 │
└─────────────────┘       └───────┬─────────┘
                                  │
                  ┌───────────────┼─────────────────┐
                  │               │                 │
                  ▼               ▼                 ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │              │ │              │ │              │
          │  PostgreSQL  │ │    Neo4j     │ │ Gemini LLM   │
          │ (Record SoR) │ │ (Projection) │ │ (Extraction) │
          │              │ │              │ │              │
          └───────▲──────┘ └──────────────┘ └──────────────┘
                  │
          ┌───────┴──────┐
          │              │
          │ Async Worker │ (Graph Build Pipeline)
          │              │
          └──────────────┘
```

- **Frontend**: Handles interactive routing, state management, and real-time LLM streaming.
- **Backend**: API gateway handling business logic, graph traversal math, and mastery routing.
- **Postgres**: System of Record (SoR) for all truth, telemetry, and source data.
- **Neo4j**: Read-optimized runtime projection for topological sorting and curriculum resolution.
- **Gemini**: Extraction engine for building the graph and driving the Socratic tutor.
- **Background Workers**: Orchestrates the multi-stage, resumable background ingestion pipeline.

---

# Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Next.js 15, TypeScript | UI rendering, client state, server-side data fetching |
| **Styling** | TailwindCSS, shadcn/ui | Component design system |
| **Backend API** | FastAPI (Python) | High-performance async HTTP routing |
| **Validation** | Pydantic v2 | Strict DTO and schema boundary enforcement |
| **Database** | PostgreSQL | System of Record for all relational and transactional data |
| **ORM** | SQLAlchemy (Async) | Database access and migration schema modeling |
| **Graph DB** | Neo4j | Runtime graph engine for topological DAG traversals |
| **LLM Engine** | Google Gemini 2.5 Flash | Concept extraction, assessments, and tutor dialogue |
| **Infrastructure**| Docker, Docker Compose | Containerization and deterministic orchestration |

---

# Repository Structure

```text
.
├── backend/                  # Python API and Workers
│   ├── app/                  # Core application logic
│   │   ├── api/              # FastAPI route controllers
│   │   ├── core/             # Configuration, DB connection lifecycle
│   │   ├── models/           # SQLAlchemy ORM definitions
│   │   ├── prompts/          # Standalone Markdown LLM prompts
│   │   ├── repositories/     # Data access layer (Postgres + Neo4j)
│   │   ├── schemas/          # Pydantic validation DTOs
│   │   ├── services/         # Business logic (Mastery, Curriculum, FSRS)
│   │   └── workers/          # Background orchestration for graph builds
│   ├── db/                   # Raw SQL schema definition (schema.sql)
│   ├── evals/                # Golden datasets and prompt evaluations
│   ├── migrations/           # Alembic migration scripts
│   └── tests/                # Unit and integration test suites
├── docs/                     # TRDs, Architecture, OpenAPI specs
├── frontend/                 # Next.js Application
│   ├── src/
│   │   ├── app/              # App router pages
│   │   ├── components/       # Shared UI components
│   │   └── lib/              # API clients, utilities, types
├── docker-compose.yml        # Orchestration topology
└── PROJECT_STATUS.md         # Handover status and release checklist
```

---

# Database Architecture

Lexis AI employs a Command Query Responsibility Segregation (CQRS) inspired polyglot database architecture.

**PostgreSQL (System of Record)**
Postgres is the absolute source of truth. It stores users, book source text, the canonical graph structure, raw completion events, and telemetry. If Neo4j crashes or is wiped, the entire system can be fully recovered from Postgres.

**Neo4j (Runtime Graph Engine)**
Neo4j exists exclusively as an asynchronous read projection. 
- **Why both exist**: Postgres is terrible at deep recursive hierarchical querying (e.g., "Find all unmastered nodes whose prerequisites are fully mastered"). Neo4j handles unbounded path traversal effortlessly.
- **Why Neo4j is not the SoR**: Graph schemas mutate often during extraction; relational integrity is better strictly guarded in Postgres.

**Graph Projection Architecture**:
Edges are resolved and evaluated in Postgres. Once a graph build is formally completed and validated (`KG_BUILT`), a sync worker projects the canonical concepts and edges into Neo4j via Cypher commands. The `curriculum_service.py` natively delegates topological sorting directly to Neo4j.

---

# Knowledge Graph Pipeline

The pipeline runs as an asynchronous, resumable background job.

1. **Upload & Parse**: The PDF is uploaded and parsed into raw text using PyMuPDF.
2. **Chunking**: Text is split into overlapping chunks, batched and committed safely.
3. **Concept Extraction**: Gemini extracts `RawConcepts` from chunks. Chunks are logged in `raw_concepts` to provide LLM lineage and allow resuming.
4. **Canonicalization**: Similar raw concepts are merged into distinct canonical `Concepts`.
5. **Relationship Extraction**: Potential concept pairs are generated into `relationship_candidates`. Gemini evaluates them, writing to an `evaluated_pairs` audit table.
6. **Validation**: Kahn's Algorithm validates the generated edges to ensure a strict Directed Acyclic Graph (DAG).
7. **Repair**: If cycles are detected, they are automatically broken.
8. **Publication**: The graph status transitions to `KG_BUILT`.
9. **Neo4j Sync**: The finalized concepts and prerequisite edges are projected into the Neo4j cluster.

**Failure Handling**: The pipeline orchestrator tracks `current_stage` and `current_offset`. It uses exponential backoff (up to 3 retries). If the worker crashes, the pipeline safely resumes from the exact offset of the current stage without wasting LLM calls.

---

# Learning Engine

The core cognitive loop of Lexis AI:

**Assessments**: 
Upon starting a book, an adaptive DAG walk quizzes the user. Right answers jump forward in the hierarchy; wrong answers drill down to find the exact prerequisite gap.

**Mastery Engine**:
Concept mastery is a float `[0.0, 1.0]`. Completing a lesson does *not* grant mastery; mastery is exclusively earned by passing isolated quizzes.

**FSRS (Retention Tracking)**:
Mastery triggers FSRS scheduling. The engine calculates the `retrievability` probability over time. Once `retrievability` drops below a threshold, the concept transitions to a `DUE` state for review.

**Unlock Logic & Curriculum Planning**:
A concept is `AVAILABLE` only if all its direct `PREREQUISITE_OF` parents possess a mastery score > `0.85`. The Curriculum Planner asks Neo4j for a topological sort of `AVAILABLE` concepts to generate a static `DailyPlan`. 

**State Transitions**:
`LOCKED` → `AVAILABLE` → `IN_PROGRESS` → `MASTERED` ↔ `DUE`

---

# Tutor System

The Socratic Tutor actively avoids giving users direct answers.

**Retrieval**: When a user queries the tutor during a lesson, the backend retrieves the precise canonical `ConceptChunk` definitions associated with the current lesson node.
**Grounding**: Gemini is strictly prompted to anchor responses exclusively within the provided chunk context to minimize hallucinations.
**Execution**: The tutor analyzes the user's intent and replies with leading questions or hints (levels 1-4).
**Limitations**: The tutor operates via synchronous API calls. Long context windows on complex concepts may incur higher latency and cost overhead.

---

# API Overview

- **Auth**: `/auth/register`, `/auth/login` (Bcrypt + JWT)
- **Books**: Uploads, ingestion status polling (SSE), curriculum fetching.
- **Graphs**: Knowledge graph reveal overlays (Neo4j projections).
- **Assessments**: Diagnostic starts, responses, and `LearningDNA` completion generation.
- **Mastery**: Direct updates to `ConceptMastery` bounds, quiz grading.
- **Lessons**: Session creation, Socratic tutor chat message endpoints.
- **Users**: Dashboard aggregations, daily activity, and streak tracking.

---

# Local Development Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local scripts)
- Node.js 20+ (for local UI)

### Environment Variables
Create a single `.env` file at the root of the repository:
```bash
cp backend/.env.example .env
```
Ensure you add a valid `GEMINI_API_KEY` to the `.env` file.

### Docker Compose Setup
The entire stack is containerized. Spin up Postgres, Neo4j, FastAPI, and Next.js in one command:
```bash
docker compose up --build -d
```

### Manual Setup (Alternative)

**Backend Startup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend Startup**
```bash
cd frontend
npm install
npm run dev
```

**Database Setup & Migrations**
To manually setup the database (assuming a running local Postgres instance):
```bash
cd backend
alembic upgrade head
```

**Verification**
Check the backend health:
```bash
curl http://localhost:8000/api/v1/health
```

---

# Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Postgres asyncpg connection string |
| `NEO4J_URI` | Yes | Bolt URI for Neo4j database |
| `NEO4J_USER` | Yes | Neo4j cluster username |
| `NEO4J_PASSWORD` | Yes | Neo4j cluster password |
| `JWT_SECRET` | Yes | Secret key for signing Auth tokens |
| `GEMINI_API_KEY` | Yes | Google Gemini LLM API token |
| `ENVIRONMENT` | No | `development` or `production` |

---

# Testing

### Backend Tests
The backend contains 38 pure logic unit tests written in `pytest`.
```bash
cd backend
export PYTHONPATH="."
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
pytest tests/
```

### AI Evaluation Harness
Prompt outputs are evaluated programmatically via an LLM-as-a-Judge eval suite.
```bash
cd backend
python -m evals.run_evals
```

---

# Deployment

**Current Recommended Deployment Topology**:
- **Frontend**: Vercel (Next.js standalone build).
- **Backend API**: Render or Railway (Docker container deployment).
- **Database (Postgres)**: Supabase or AWS RDS.
- **Graph Engine (Neo4j)**: Neo4j AuraDB (Cloud managed).

For single-node VPS deployment, the provided `docker-compose.yml` serves as a production-ready baseline.

---

# Observability & Debugging

**Logs**: The backend uses basic standard Python `logging`. Currently, request correlation IDs and structured logging (e.g., `structlog`) are absent.
**Workers**: Background jobs (ingestion) failures are recorded in the `graph_build_jobs` table under the `last_error` column.
**Common Failure Points**:
- **Neo4j Sync Issues**: If graph overlays return empty, ensure `POST /books/{id}/graph/sync-neo4j` has executed successfully.
- **Gemini Issues**: 429 Rate Limits on the free tier. The background worker exponentially backs off automatically, but interactive lessons may drop.
- **Assessment Issues**: If an assessment hangs, ensure the Neo4j topological read was successful and the graph is fully connected.

---

# Security Considerations

- **Authentication**: JWT-based bearer tokens issued via NextAuth.
- **Authorization**: Extracted from `get_current_user_id` dependency injections.
- **Tenant Isolation**: Books are globally shared entities. User progress, streaks, and mastery are heavily isolated via `user_id` foreign key relations.
- **File Upload Security**: Uploads are accepted only as PDFs. Files are processed locally and purged after the `KG_BUILT` phase to prevent malicious execution.
- **Prompt Injection**: Learner chat inputs to the Socratic tutor are strictly bounded by RAG context windows, but adversarial injection remains a potential vulnerability against Gemini.

---

# Known Limitations

- **File Storage Constraints**: Uploads currently utilize a stateful `LocalStorageProvider` written to the container's `/uploads` directory. A container restart will lose pending unprocessed PDFs. S3 integration is required.
- **Observability Deficit**: Lack of `structlog` and APM integration makes tracing distributed LLM latency difficult.
- **Gemini Costs**: Real-time interactions in the Socratic Tutor are synchronous API calls, subject to latency spikes and quota exhaustion on free tiers.

---

# Roadmap

- **S3 File Storage**: Transition from local disk caching to a persistent `S3StorageProvider`.
- **Integration Test Suite**: Build API-level system integration tests (currently relies on pure unit tests and manual QA).

---

# Documentation Index

| Document | Purpose |
|---|---|
| `AGENT.md` | Core agent instructions, architectural rules, and project ethos |
| `PROJECT_STATUS.md` | Handover checklists, recent bug fixes, and exact completion states |
| `docs/architecture/system_design.md` | Deep dive into system CQRS patterns and backend layers |
| `docs/architecture/ingestion_pipeline.md` | Detailed explanation of the 8-stage graph orchestration pipeline |
| `docs/prompts/*.md` | Isolated LLM system prompts (Tutor, extraction, assessments) |
| `backend/db/schema.sql` | The absolute source of truth for the Postgres relational schema |

---

# Acknowledgements

Built with FastAPI, Next.js, Neo4j, PostgreSQL, and Google Gemini. Spaced repetition powered by the open-source FSRS algorithm.
