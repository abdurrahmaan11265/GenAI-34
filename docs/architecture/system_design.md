System Design — Adaptive Book-Learning Platform
A. High-level architecture
The system breaks into six layers, each owning one responsibility:
Ingestion pipeline — turns an uploaded book into a validated knowledge graph.
Graph store — holds per-book KGs (nodes + prerequisite edges) and per-user mastery state.
Assessment engine — places the user on the graph before they start.
Learning engine — Socratic, LLM-driven teaching, one node at a time.
Scheduling / revision engine — decides what's due and builds the daily plan.
Progress + gamification layer — streaks, scores, and the Coursera-style gated UI.
Keep the content graph (the book's concepts) separate from user state (mastery, intervals, history). One book → one canonical graph; many users → many overlays on top of it. This separation keeps the same graph reusable across users and lets you ship shared graphs for popular books.

B. Core data model
Book — { id, owner_id, title, source_file, status }. The canonical graph version is derived dynamically from the graph_versions table. Status moves through uploaded → parsing → kg_built → kg_verified → ready.
KG Node (concept) — { id, book_id, title, summary, source_chunks[], difficulty_tier }. Every node is traceable back to the chunk of book text it came from.
KG Edge — { from_node, to_node, type: "prerequisite" | "related", weight, confidence }. The prerequisite edges form a DAG — this is the single most important invariant in the system; assessment, locking, and graph reveal all read from it.
User-Node State — the user overlay is normalized into three structures to separate curriculum state, raw mastery, and spaced repetition:
  - user_concept_state: { user_id, concept_id, state: "locked" | "available" | "in_progress" | "mastered" | "due" }
  - concept_mastery: { mastery_score, last_assessed }
  - concept_fsrs: { stability, difficulty, next_due, last_reviewed }
Question — { id, node_id, type: "mcq" | "theory" | "applied", difficulty, source: "generated" | "user_asked" | "assessment_miss" | "revision" }. The source field is what powers targeted revision later.
Session — { id, user_id, book_id, mode: "learning" | "revision", node_ids[], transcript, questions_asked[], outcomes[] }.

C. Ingestion & KG construction (the pipeline behind everything)
This is the part most likely to break the product if rushed, since Sections D, F, and J all depend on the edges being correct.
Parse & chunk — extract text from the upload (PDF/EPUB), normalize, and chunk along the book's own structure (chapters → sections), since that structure is a strong prior for the graph.
Concept extraction — an LLM pass over chunks proposes candidate nodes, each grounded in the chunk it came from (so every node is traceable to source text — needed for teaching and for trust).
Edge inference — a second pass proposes prerequisite edges. Treat these as low-confidence by default: auto-generated prerequisites are the single biggest source of error. Run a cycle-check and reject anything that breaks the DAG.
Human-in-the-loop verification — before a book goes ready, the uploader (or a reviewer) sees the graph and can merge, split, delete, or re-link nodes. For popular public-domain books, ship a shared graph so most users skip this step entirely. This step is what stops one bad edge from cascading into wrong locks and a wrong assessment.

D. Assessment engine (placement)
This is adaptive testing on the DAG — formalize it rather than asking everything.
Walk the DAG top-down (toward leaves), in topological order. For each node, ask a short progression: MCQ → theory → applied, escalating only if the user passes the easier tier.
Mastery threshold per node — a node is "known" if the user clears its threshold. If they fail the easy tier on a node, stop descending that branch: that node and every dependent node above it are marked needs-learning, and you skip re-testing them (they're presumed unknown). This is exactly your original point 3, made deterministic.
Confidence calibration — ask "how sure are you?" before revealing correctness. Confident-but-wrong nodes are the highest-value revision targets and get flagged immediately.
Output — every node lands in a known state (mastered / available / locked), so the revealed graph (Section E) already reflects reality instead of a blank slate.

E. Graph reveal & visual states
After assessment the user sees their personalized KG. Use four visual states, not two:
Locked (greyed/disabled-looking) — prerequisites unmet.
Available — unlocked, not yet learned.
Mastered — solid/colored.
Due — mastered but fading, flagged for revision.
Progressive reveal — as prerequisites are cleared, downstream nodes transition locked → available, so the graph visibly "opens up" the way you described.

F. Learning engine (Socratic)
One node at a time, gated by the DAG — a node only becomes teachable when its prerequisites are mastered. This is the Coursera-style locking (Section I), driven entirely by the graph.
Socratic loop — the LLM teaches by questioning and probing rather than lecturing, grounded in the node's source_chunks so it stays faithful to the actual book.
Capture everything — every question the user asks during the session is stored as a Question with source: "user_asked" and attached to the node. These resurface in revision, so the user revisits exactly what confused them.
On completion — update the node's mastery_score, set state: mastered, initialize its spaced-repetition parameters, and re-evaluate downstream nodes for unlocking.

G. Revision & scheduling engine (the daily heartbeat)
This is your original point 6, made concrete. Decide this data model early — it runs every single day.
Use a real spaced-repetition algorithm — FSRS (preferred) or SM-2. Each node carries stability, difficulty, and next_due. "Should I revise today?" becomes a clean query: which of this user's nodes have next_due ≤ today? No hand-tuned heuristics.
Forgetting-curve state — store a decaying recall probability per node; that's what drives the due visual state in point 21 and lets you sort revision by urgency.
Daily plan generation — on opening a book, the engine returns one of: revise only (due cards exist, no new capacity), learn only (nothing due yet), or both (mix due reviews + new available nodes up to a daily load cap). Cap new nodes per day so the graph doesn't outrun the user's retention.
Targeted revision bank — pull revision questions from three sources: the user's own user_asked questions, their assessment_miss items, and items they got wrong while learning. Revision hits actual weak spots, not the whole node again.
Each review updates the schedule — grade the recall, feed it back into FSRS, recompute next_due. Over time the system learns the user's personal forgetting rate per concept.

H. Progress & gamification
Streaks at two levels: a global daily-activity streak, and a per-book consistency streak.
Progress metrics — per book: % nodes mastered, % graph revealed, due-load trend; per user: total concepts mastered, retention rate over time.
Make "due" feel actionable, not punishing — surface the day's plan as a small, completable list, not an ever-growing backlog (the daily cap in point 29 protects this).

I. UI/UX summary
Library view — the top level is the user's bookshelf with per-book progress; one level down is the per-book graph and course view.
Coursera-style course view per book: a path of nodes, locked ones visibly gated with a "complete X first" reason pulled straight from the unmet prerequisite edge.
Two tabs per book: Learning and Revision, both reading from the same KG + scheduling state.
Interactive graph view as the map/overview, with the four-state coloring from point 21.

J. Suggested stack (optional)
Graph store: Neo4j or Postgres with a recursive-CTE adjacency model (Postgres is fine at first and keeps user-state + content in one place). Pipeline: async workers (queue) for parse → extract → verify. Scheduling: FSRS as a library, state in Postgres. Frontend: a graph lib (React Flow / Cytoscape.js) for the map, standard component UI for the course view.

Two decisions to lock before building anything
KG construction + validation (Section C) and revision-due state (Section G) are the two data models everything else leans on. If the prerequisite DAG is wrong, assessment, locking, and reveal are all wrong; if the due-state model is wrong, the daily plan — the thing the user sees most — is wrong. Get these two right first; the rest can iterate.


