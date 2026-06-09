# Lexis — Project Status & Handover

Last updated: **2026-06-07**  
Branch: **`main`** (all work merged and pushed)  
**38 pure unit tests pass; all 9 GenAI prompt evals meet PEOS targets; frontend builds and has been manually QA'd end-to-end.**

---

## ✅ Done & Working End-to-End

### Foundation (pre-existing, fully verified)
- **Auth** — `/auth/register`, `/auth/login` (bcrypt + JWT); NextAuth session forwards the bearer token.
- **PostgreSQL schema** — `backend/db/schema.sql` (26 tables + materialized views); SQLAlchemy async ORM; typed ENUM mappings; `update_updated_at_column()` trigger.
- **Library + 2-step upload** — `POST /books` → `POST /books/{id}/upload` → background ingestion worker; status polling via SSE.
- **API dual-session bug fixed** — all `books.py` endpoints now use a single shared `AsyncSession` (removed the anti-pattern of injecting both a `Service`-owned session and a route-level session simultaneously, which caused silent no-op commits).

---

### Ingestion Pipeline — Fully Checkpointed & Resumable ✅
Previously: monolithic pipeline, single giant transaction, O(n²) LLM calls, no recovery on crash.

**Now (as of `eb03625`):**

| Stage | Status |
|---|---|
| PARSING | ✅ |
| CHUNKING | ✅ Batched (20/commit), idempotent on conflict |
| EXTRACTING_CONCEPTS | ✅ Per-chunk, skips already-done chunks via `raw_concepts` table |
| CANONICALIZING | ✅ Load from `raw_concepts`, single commit; resumes if concepts already exist |
| EXTRACTING_RELATIONSHIPS | ✅ Pairs written to `relationship_candidates` once; only `PENDING` rows call LLM (50/commit) |
| VALIDATING | ✅ GraphValidator rules |
| REPAIRING | ✅ Cycle-break via GraphRepair |
| PUBLISHING | ✅ `KG_BUILT`, source file cleanup |

**Key architectural decisions:**
- `raw_concepts` table — per-chunk extraction checkpoint. Crash after chunk 5 of 300 = resume from chunk 6, zero LLM re-calls.
- `relationship_candidates` table — candidate pairs generated once, processed incrementally. Crash mid-relationship-extraction = resume from next `PENDING` row.
- `evaluated_pairs` table — clean audit log (`EDGE_CREATED` / `NO_RELATIONSHIP` / `FAILED`). The **graph model stays clean** — no `NONE` dummy edges polluting `concept_edges`.
- `graph_build_jobs` extended with `current_stage`, `current_offset`, `retry_count`, `last_error`, `next_retry_at`.
- **Worker retry policy**: exponential backoff (30s → 60s → 120s, cap 10 min), max 3 attempts. After 3 failures the job stays `FAILED` and requires manual re-queue.

---

### Learner-Model Engines (PR #2 — merged)
Each engine is contract-first (types → schema → API → logic), unit-tested where it has pure logic, wired to the UI.

- **Assessment + Learning DNA** — adaptive topological DAG walk (MCQ → theory → applied, branch-stop, confidence calibration); atomic `/complete` seeds `concept_mastery` + `user_concept_state` and generates Gemini DNA. `/api/v1/assessments` (start/resume, responses, complete, results).
- **Graph reveal** — per-user four-state overlay (LOCKED / AVAILABLE / IN_PROGRESS / MASTERED / DUE). `GET /books/{id}/knowledge-graph`.
- **Curriculum + Daily Plan — fixed** — deterministic (graph-decided, topological order); **persisted "today's focus"** (frozen per day, regenerates when the set is mastered); concept **sub-topics** surfaced as chips.
  - **Bug fixed**: `get_curriculum` was silently dropping `subtopics` on cached reads (missing field in deserializer).
  - **Bug fixed**: `save_today_plan` was not persisting JSONB list mutations — added `flag_modified()` so SQLAlchemy tracks the dirty field.
  - `/books/{id}/curriculum`, `/books/{id}/daily-plan`.
- **Lessons + Socratic Tutor + Hints** — Gemini lessons grounded in source chunks; tutor teaches by questioning (0% answer-leakage in evals); captures `user_asked` questions; **persistent/resumable** sessions. `/api/v1/lessons/...`.
- **Mastery is earned, not declared** — finishing a lesson does **not** master a concept; a **mastery-check quiz** (3 questions) gates mastery + dependency unlock. `/lessons/{id}/quiz` + `/quiz/grade`.
- **Mastery + FSRS + Revision** — canonical mastery engine + FSRS scheduler; due detection, review grading, MASTERED ↔ DUE transitions. `GET /books/{id}/revision`, `POST /books/{id}/concepts/{cid}/review`.
- **Dashboard / Stats / Streaks** — aggregation + activity-derived streaks; real notifications (no longer a `[]` stub). `GET /dashboard`, `GET /notifications`.
- **Neo4j projection** — best-effort `PREREQUISITE_OF` / `HAS_MASTERY` / `CURRENTLY_LEARNING` (Postgres is source of truth). `POST /books/{id}/graph/sync-neo4j`.

---

### Frontend (fully wired to real backend)
`src/lib/api.ts` maps every screen to `/api/v1`. Library, upload/processing, **graph verify**, **assessment** (intro/question/results), **course/graph map**, **daily plan**, **lesson + tutor + quiz**, **revision**, **dashboard/progress**, settings, notifications. Markdown/code rendering for AI text. ~10 UX bugs found during QA and fixed.

---

### Architecture Debt & Blockers Resolved ✅
- **FSRS & Mastery Engine Unification**: Removed frontend-side magic number mocking (`0.9`). The backend's `progress_service.py` now correctly channels lesson completions through `mastery_engine.update_mastery` and respects the engine's routing and retention scores natively.
- **Kahn's Algorithm & Lineage**: The `graph_validator.py` completely deprecated naive DFS for formal Kahn's algorithm cycle detection. Ingestion orchestration now actively persists `raw_concepts.canonical_concept_id` linking extracted text chunks back to their canonical models for full LLM lineage tracking.
- **Neo4j Read Utilization**: Neo4j is no longer a write-only phantom. `curriculum_service.py` natively delegates graph topological sorting to Neo4j via Cypher queries (`get_topological_order`), honoring its purpose as the runtime Graph Engine.
- **API Boundary Type Mismatches**: Aligned `difficultyTier` into explicit string literals (`"beginner"`, `"intermediate"`, `"advanced"`) across Python Enum / Pydantic schema / Typescript boundary. Cleaned up `UserDTO.name` aliasing gaps.

---

### End-to-End Containerization ✅
The application was fully Dockerized allowing 1-click execution:
- **Pruned Dependencies**: Ripped out 200+ polluted packages from `requirements.txt` via AST static analysis, leaving only 16 absolute essentials.
- **Dockerfiles**: Crafted lightweight multi-stage builds (`python:3.11-slim` and `node:20-alpine`) utilizing Next.js standalone execution.
- **Docker Compose Orchestration**: Unified configuration behind a singular root `.env`. Enforced deterministic spin-ups utilizing shell-native healthchecks (`curl`, `pg_isready`, `cypher-shell`) and `depends_on: condition: service_healthy` across all 4 cluster nodes (Postgres, Neo4j, Backend, Frontend).

---

### Quality
- **Eval harness** — `backend/evals/` golden datasets + scorers + `python -m evals.run_evals` (concept extraction, relationship, merge, assessment-gen, assessment-eval, DNA, lesson, tutor, hint). LLM-as-judge fallback for concept purity. All 9 targets met.
- **38 unit tests** — assessment walk, curriculum planner, mastery engine, FSRS, streaks, eval scorers, chunking.

---

## 🗄️ Database & Migration Notes

### Alembic (now the canonical migration tool)
- **All new schema changes go through Alembic** — `backend/migrations/versions/`.
- **`alembic upgrade head`** applies all pending migrations.
- **`backend/migrations/env.py`** is now fully configured:
  - Imports all ORM models via `import app.models`.
  - `include_object` hook prevents autogenerate from generating spurious `DROP TABLE` for tables in `schema.sql` that are not yet ported to ORM models.

### Applied Migrations (in order)
| Revision | Description |
|---|---|
| `762017ca7505` | Add `name` column to `users` table (baseline) |
| `de54f380a89e` | Ingestion batching: `raw_concepts`, `relationship_candidates`, `evaluated_pairs` tables; `graph_build_jobs` resilience columns; `graph_build_status` enum extended |

### Fresh DB Setup
```bash
# Option A — full schema (no migration history)
psql -U postgres -d lexis -f backend/db/schema.sql
alembic stamp head   # tell Alembic the DB is at head

# Option B — incremental (already have a DB from schema.sql)
alembic upgrade head
```

### Schema vs ORM Gap (✅ Closed)
`schema.sql` remains the source-of-truth documentation for the full schema. However, **all tables** have now been ported to SQLAlchemy ORM models (as of this commit).
- `backend/migrations/env.py` no longer uses an exclusion hook.
- Alembic `autogenerate` is now fully authoritative across the entire database.

### 🛑 Critical Developer Instructions for Schema Modifications
To prevent future drift between the database and SQLAlchemy ORM models, **all contributors must follow this strict workflow**:
1. **Source of Truth**: `backend/db/schema.sql` is the absolute source of truth. Always design your schema changes there first.
2. **Manual ORM Synchronization**: Do NOT rely on Alembic `--autogenerate` to build your ORM classes. After updating `schema.sql`, manually update the SQLAlchemy models (in `backend/app/models/`) to perfectly mirror the DB schema.
   - Pay strict attention to `__table_args__` for exact `Index`, `UniqueConstraint`, and `CheckConstraint` mappings.
   - Ensure explicit alignment of `server_default` and column types (e.g. `Integer` vs `BigInteger`).
3. **Validation (The Acid Test)**: Use `alembic revision --autogenerate` purely as a *validation tool*.
   - **Before committing**, always run: `alembic revision --autogenerate -m "verify_alignment"`
   - If Alembic detects *any* unexpected schema modifications (dropped columns, missing constraints), **do not commit**. Your ORM models are drifting from the database. Fix the ORM models until the autogenerate diff is empty.

---

## 🚧 Known Limitations / Remaining Work

### Must-Fix Before Production
- **File storage is local disk** (`uploads/`) behind a `StorageProvider` interface. The `LocalStorageProvider` is stateful — any container restart or multi-node deploy will lose uploaded PDFs. **Add an `S3StorageProvider`** (factory already in place in `storage.py`).
- **No structured logging / request correlation IDs** — currently `logging.basicConfig(INFO)`. Add `structlog` + request middleware before scaling.

### Good Next Tasks (in priority order)
1. **Graph editing via chat** ✅ *Done* — Users can now correct edges/concepts via a chat interface before the graph is locked.
2. **Ingestion batching for huge books** ✅ *Done* — see above. The pipeline is now resumable and rate-limit safe.
3. **Curriculum + Daily Plan reliability** ✅ *Fixed* — subtopics and JSON mutation bugs resolved.
4. **Dashboard / Streaks / Real Notifications** — currently functional but needs UX revision and edge-case hardening.
5. **API-level integration tests** — coverage gap; unit tests + evals + manual QA is not enough for CI/CD confidence.
6. **Gemini cost optimization** — each interactive lesson/tutor step is a live call. Consider pre-generation or caching for demos on the free tier (≈15 RPM).

---

## 📌 Handover Checklist
- [x] Ingestion pipeline E2E — parse → chunk → extract → canonicalize → edge → validate → publish.
- [x] Ingestion pipeline — fully checkpointed and resumable (as of `eb03625`).
- [x] Assessment engine + Learning DNA (PR #2 merged).
- [x] Curriculum / Daily Plan bugs fixed.
- [x] Worker retry with exponential backoff.
- [x] Alembic configured; `env.py` fixed; migration `de54f380a89e` applied.
- [x] Schema vs ORM Gap closed: all `schema.sql` tables now have SQLAlchemy ORM models.
- [x] 38 unit tests passing; 9 eval harness targets met.
- [x] All 7 Production Release Blockers resolved (Mastery unification, Kahn's algorithm, API types, Neo4j topological).
- [x] Full Docker Containerization and orchestration (`docker-compose.yml`) + Single Root `.env`.
- [x] Graph editing via chat — completed.
- [ ] S3 file storage — not yet implemented.
