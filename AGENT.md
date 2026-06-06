# AGENTS.md

# READ THIS FIRST

This document is the single source of truth for Lexis AI.

Every human contributor, AI coding agent, Claude Code session, Cursor agent, Copilot agent, OpenHands session, reviewer, and maintainer must follow this document.

The purpose of AGENTS.md is to prevent:

* Scope creep
* Architecture drift
* Duplicate implementations
* Conflicting systems
* AI-generated nonsense
* Overengineering
* Last-minute redesigns

If AGENTS.md conflicts with implementation:

AGENTS.md wins.

If AGENTS.md conflicts with personal preference:

AGENTS.md wins.

If AGENTS.md conflicts with "cool ideas":

AGENTS.md wins.

---

# PROJECT MISSION

Lexis AI is a learner intelligence platform.

It is NOT:

* ChatGPT for education
* LMS
* Course marketplace
* Roadmap generator
* RAG chatbot

The system exists to answer:

* What does this learner know?
* What does this learner not know?
* Why are they struggling?
* What should they learn next?
* How should they learn it?

The product is NOT educational content.

The product is the learner model.

Lessons are generated.

Curriculum is generated.

Tutor responses are generated.

The learner model persists.

The learner model is the product.

---

# PROJECT VISION

Most educational systems know:

* What course a learner completed

They do NOT know:

* Why the learner struggles
* What misconceptions exist
* What concepts are weak
* What concepts are mastered
* What should be learned next

Lexis AI maintains:

* Mastery
* Memory
* Misconceptions
* Knowledge Graph Position
* Curriculum State
* Learning History

The goal is understanding the learner.

Not generating content.

---

# ARCHITECTURE FREEZE

The following decisions are frozen.

No contributor may change them without unanimous team approval.

---

## Domain

Frozen:

Uploaded PDF Textbooks (Adaptive Book-Learning)

Not:

* Hardcoded DSA Curriculum
* Static video courses
* Pre-written syllabi


---

## AI Provider

Frozen:

Gemini 2.5 Flash

Not:

* OpenAI
* Claude
* DeepSeek
* Multi-model orchestration

---

## Graph Database

Frozen:

Neo4j

---

## Relational Database

Frozen:

PostgreSQL

---

## Frontend

Frozen:

Next.js 15 + TypeScript + TailwindCSS + shadcn/ui

---

## Backend

Frozen:

FastAPI (Python)

Modular Monolith

---

## Architecture Style

Frozen:

Modular Monolith

Not:

Microservices

---

## Core Features

Frozen:

* Assessment
* Learning DNA
* Knowledge Graph
* Curriculum Generator
* Lesson Generator
* Socratic Tutor
* Learner Memory
* Dashboard
* Dynamic Curriculum Replanning

---

# THINGS WE EXPLICITLY REFUSE TO BUILD

The following are permanently rejected.

Do not suggest.

Do not implement.

Do not create issues.

---

Voice Tutor

Reason:

No impact on learner modeling.

---

Emotion Detection

Reason:

Impossible to validate.

---

Video Generation

Reason:

Not core to personalization.

---

AI Avatar

Reason:

Demo fluff.

---

AR / VR

Reason:

Massive scope increase.

---

Blockchain

Reason:

Solves no problem.

---

Fine-Tuning

Reason:

No dataset.
No timeline.

---

RLHF

Reason:

No infrastructure.

---

Multi-Agent Swarms

Reason:

Single Gemini model is sufficient.

---

Custom LLMs

Reason:

Not required.

---

Pre-Written Syllabi

Reason:

Curriculum must be dynamically generated from the uploaded book's knowledge graph.

---

# NON NEGOTIABLE PRINCIPLES

1. The learner model is the product.

2. AI is never the source of truth.

3. Graph state is deterministic.

4. Personalization beats feature count.

5. Reliability beats sophistication.

6. Demo reliability beats architectural purity.

7. Graph decides curriculum.

8. AI explains curriculum.

9. Every recommendation must be explainable.

10. Every learner should receive a unique experience.

11. No duplicated ownership.

12. No hidden state.

13. Prompts are code.

14. All prompts are versioned.

15. Simplicity wins.

16. Working systems beat theoretical systems.

17. Scope reduction is allowed.

18. Scope expansion is forbidden.

19. Backend owns truth.

20. AI generates language only.

---

# DOCUMENT PRECEDENCE

1. docs/architecture/system_design.md
2. docs/architecture/ingestion_pipeline.md
3. docs/architecture/mastery_engine.md
4. schema.sql
5. docs/prompts/*

Rule:

If two documents conflict,
higher-precedence document wins.

Always.

---

# SYSTEM PHILOSOPHY

Deterministic Systems Own Truth.

AI Systems Generate Content.

Never reverse this relationship.

---

## AI MAY

Generate:

* Lessons
* Exercises
* Quizzes
* Hints
* Explanations
* Summaries
* Learning DNA narrative
* Recommendation explanations

---

## AI MAY NOT

Update:

* Mastery
* Retention
* Graph State
* Curriculum State
* Database Records
* User State

AI never decides system state.

---

# TEAM OWNERSHIP MODEL

## Student 1

AI + Prompt Layer

Owns:

* Prompt Library
* Assessment Prompts
* DNA Prompts
* Lesson Prompts
* Quiz Prompts
* Tutor Prompts

Cannot Modify:

* Database Schema
* Graph Schema

---

## Student 2

Backend + Auth + Database

Owns:

* APIs
* PostgreSQL
* Authentication
* Validation

Cannot Modify:

* Prompt Logic
* Neo4j Schema

---

## Student 3

Graph + Curriculum

Owns:

* Neo4j
* Concept Graph
* Recommendation Engine
* Curriculum Engine

Cannot Modify:

* Authentication
* Frontend

---

## Student 4

Frontend + UX

Owns:

* Dashboard
* Assessment UI
* Tutor UI
* Curriculum UI

Cannot Modify:

* Backend Logic

Note: Tutor requires an active lesson session.

---

## Student 5

Integration + Testing + Deployment

Owns:

* Testing
* Deployment
* CI/CD
* Graph Visualization
* Cross-system Integration

Cannot Modify:

Core Architecture.

---

# LEARNER MODEL CONTRACT

The learner model is the most important object in the system.

Structure:

Mastery

Retention

Misconceptions

Bloom

History

Preferences

Curriculum State

---

Allowed Readers

Assessment

Curriculum

Tutor

Dashboard

Lesson Generator

Recommendation Engine

---

Allowed Writers

Assessment Engine

Progress Engine

Only.

---

Forbidden Writers

Gemini

Frontend

Tutor

Lesson Generator

Recommendation Engine

---

# KNOWLEDGE GRAPH CONTRACT

Node Types

Concept

Student

Error

CurriculumPath

Lesson

Question

---

Relationships

PREREQUISITE_OF

HAS_MASTERY

STRUGGLES_WITH
(Note: STRUGGLES_WITH edges are idempotent per {student_id, concept_id, error_type})

CURRENTLY_LEARNING

CONTAINS

---

Graph Invariants

No cycles.

No self references.

No orphan concepts.

Every concept must be reachable.

Every recommendation must be explainable.

---

# DATA OWNERSHIP

PostgreSQL owns:

* Users
* Sessions
* Assessments
* Quiz Attempts
* Mastery
* Retention
* Memory

Neo4j owns:

* Concepts
* Dependencies
* Graph State
* Traversals
* Recommendations

Concept Mapping Contract:
Ingestion Pipeline `difficulty_level` -> concepts `difficulty`
Ingestion Pipeline `bloom_level` -> concepts `bloom_target`
Ingestion Pipeline `estimated_duration` -> concepts `estimated_minutes`

Concept ID Namespace Constraint:
Concept IDs come ONLY from the Document Ingestion Pipeline extraction. Both Postgres and Neo4j are populated dynamically per book.

Atomic Assessment Workflow: 
`/assessments/{id}/complete` is synchronous. Steps: (1) Score responses, (2) Initialize concept_mastery, (3) Initialize HAS_MASTERY edges in Neo4j, (4) Generate DNA via Gemini, (5) Store DNA, (6) Return DNA. If any step fails, rollback and return error.

Mastery Update Race Condition Mitigation:
Progress engine must update Postgres first. Neo4j update is eventually consistent within the same request. If Neo4j write fails, log the failure and retry.

Parallel Schema Modifications:
All schema changes go through Student 2. Student 3 submits schema change requests as SQL PRs.

Demo Rate Limiting Strategy:
Gemini Free Tier is ~15 RPM for Flash. For live demos, implement response caching or pre-generate and cache one complete learner journey to avoid hitting limits.

Gemini owns:

Nothing.

Gemini stores nothing.

Gemini is stateless.

---

# FORBIDDEN PATTERNS

Never:

Store graph state in PostgreSQL.

Store mastery inside prompts.

Store curriculum inside Gemini.

Allow AI to update database.

Create duplicate recommendation systems.

Create duplicate mastery systems.

Create duplicate graph structures.

Introduce a second AI provider.

Introduce a second database.

---

# PROMPT ENGINEERING RULES

Prompts are code.

Prompts must:

* Have version numbers
* Have schemas
* Have validation
* Have failure handling
* Have observability

---

Forbidden:

Inline prompt strings.

Copy-pasted prompts.

Prompt duplication.

Unversioned prompts.

---

All prompts belong in:

/prompts

---

# API DESIGN RULES

All APIs:

* RESTful
* Typed
* Validated
* All API endpoints are prefixed with `/api/v1`.

Session Management:
* JWT expiry = 24h. No refresh token in MVP. Users re-login after expiry.

Validation:

Backend: Pydantic v2
Frontend: Zod

Required.

---

Error Format

{
success:false,
error:{
code:"",
message:""
}
}

---

No raw errors returned.

---

# DATABASE RULES

Every schema change:

Requires migration via Alembic (Python) or explicit SQL migration scripts.
No manual `schema.sql` mutations in production. Rollback plans must be included for every migration.

Quiz score (0-100) is for display only. Mastery updates are driven by per-question events (0.0-1.0).

---

Every table:

Requires primary key.

---

Every foreign key:

Must be explicit.

---

Every frequently queried field:

Must be indexed.

---

No schema changes without review.

---

# FRONTEND RULES

State Management:

Zustand

---

Components:

Reusable

Composable

Typed

---

Every screen requires:

Loading State

Error State

Empty State

Success State

---

Accessibility required.

---

# TESTING RULES

Required:

Unit Tests

Integration Tests

---

Critical Flows:

Must be tested.

Assessment

DNA

Curriculum

Tutor

Dashboard

---

No merge without tests.

---

# AI AGENT RULES

AI-generated code is untrusted.

Before merging:

Read it.

Understand it.

Test it.

---

"Claude generated it"

is never an excuse.

---

# AGENT AUTHORITY LEVELS

Agents may:

* Create components
* Create APIs
* Create prompts
* Create tests

Agents may NOT:

* Change architecture
* Change databases
* Change AI providers
* Change ownership boundaries

Without approval.

---

# CONTRACT FIRST DEVELOPMENT

Always build in this order:

1. Types
2. Schemas
3. API Contracts
4. Database Contracts
5. Business Logic
6. UI

Never reverse.

---

# FEATURE PROPOSAL GATE

Before adding any feature answer:

1. Does it improve learner modeling?

2. Does it improve personalization?

3. Does it improve curriculum adaptation?

4. Does it improve learner understanding?

5. Can it be demonstrated?

If fewer than 3 answers are YES:

Reject the feature.

---

# DEMO CRITICAL PATH

P0

Must Work

* Assessment
* Learning DNA
* Knowledge Graph
* Curriculum Generation
* Lesson Generation
* Tutor
* Dashboard

---

P1

Important

* Error Taxonomy
* Memory
* Replanning

---

P2

Optional

* Retention
* Bloom Analytics
* Advanced Metrics

---

# EMERGENCY SCOPE REDUCTION

If behind schedule:

Remove in order:

1. Bloom Tracking
2. Retention Engine
3. Learning Velocity
4. Advanced Analytics

Never remove:

1. Assessment
2. Learning DNA
3. Knowledge Graph
4. Curriculum
5. Tutor
6. Dashboard

---

# VIVA CRITICAL KNOWLEDGE

Why Neo4j?

Educational dependencies form graphs.

---

Why Gemini?

Fast.
Cheap.
Good enough.

---

Why PDF Book Ingestion?

Allows infinite scaling across any domain by generating graphs dynamically.

---

Why Knowledge Graph?

Explainable curriculum generation.

---

Why Socratic Tutor?

Promotes reasoning instead of answer dumping.

---

Why Personalization?

Different learners have different knowledge states.

---

Why Adaptive Assessment?

Builds learner model instead of generating scores.

---

# DECISION FRAMEWORK

Before every major decision ask:

Does it improve learner understanding?

Does it improve personalization?

Does it improve curriculum adaptation?

Does it improve demo quality?

Does it respect architecture?

If not:

Reject.

---

# DEFINITION OF DONE

Feature Done:

* Implemented
* Tested
* Documented
* Reviewed

---

Prompt Done:

* Versioned
* Validated
* Logged
* Tested

---

API Done:

* Typed
* Validated
* Tested

---

UI Done:

* Responsive
* Accessible
* Handles loading
* Handles errors

---

# FINAL PRINCIPLE

If forced to choose between:

A technically elegant feature

and

A reliable demonstration

Choose the reliable demonstration.

Grades are awarded on demonstrated functionality.

The learner model is the product.

Everything else exists to serve it.


## Concept Source of Truth

Frozen:

Postgres concepts table = Source of Truth (Metadata, difficulty, duration, display name)
Neo4j Concept nodes = Projection (Relationships, prerequisite paths)
