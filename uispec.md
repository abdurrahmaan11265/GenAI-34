UI Specification — Adaptive Book-Learning Platform
This document lists every screen in the product and the full contents of each. Screens are grouped by flow. Each screen lists its purpose, contents (every element on the screen), states (empty / loading / error / edge cases), and actions (where the user can go next).
The screen inventory maps directly onto the system design: ingestion → assessment → graph → learning → revision → progress.

Screen Inventory (quick map)
Splash / Auth
Library (Home / Bookshelf)
Add Book — Upload
Add Book — Processing Status
Graph Verification / Editor (uploader-reviewer)
Assessment — Intro
Assessment — Question
Assessment — Results
Knowledge Graph — Map View
Book Home — Daily Plan
Course View (Coursera-style path)
Node Detail
Learning Session (Socratic)
Revision — Due List
Revision Session
Progress / Stats
Profile / Settings
Notifications

1. Splash / Auth
Purpose: Entry point — sign in or create an account.
Contents:
App logo and one-line tagline.
Sign in form: email, password.
Sign up form: name, email, password.
Social / OAuth buttons (optional: Google).
"Forgot password" link.
Toggle between Sign in / Sign up.
States:
Loading (auth in progress).
Error (invalid credentials, email already used).
Actions:
Successful auth → Library (Screen 2). First-time users land on Library with the empty state.

2. Library (Home / Bookshelf)
Purpose: The top-level hub. Shows everything the user is studying and the entry point to add more.
Contents:
Header bar: app logo, global search, profile avatar (→ Settings), notifications bell.
Global streak widget: current daily streak count, flame/streak icon, "studied today" check state.
Today summary strip: total nodes due across all books, "X min plan today" estimate, a primary CTA "Start today's plan."
Book grid / shelf: each book card shows:
Cover thumbnail + title + author.
Book status badge (Processing, Needs review, Ready, Take assessment).
Progress ring: % nodes mastered.
Secondary line: nodes due today for this book, per-book streak.
"+ Add Book" card / button (→ Upload).
Sort / filter controls (recently studied, most due, alphabetical).
States:
Empty: no books yet — large illustration + "Upload your first book" CTA.
Processing: book card shows spinner + status; not yet openable.
Needs review: card flags that the graph needs verification before assessment.
Actions:
Tap a Ready book → Book Home / Daily Plan (Screen 10).
Tap a book that hasn't been assessed → Assessment Intro (Screen 6).
Tap a Needs review book → Graph Verification (Screen 5).
"Start today's plan" → opens the most-due book's daily plan.

3. Add Book — Upload
Purpose: Get a book file into the system.
Contents:
Drag-and-drop zone + file picker. Accepted formats listed (PDF, EPUB).
Optional metadata fields: title, author (auto-filled from file when possible, editable).
Visibility toggle: private to me / contribute graph to shared library (for public-domain books).
File size / format constraints note.
Upload button.
States:
Idle / file selected / uploading (progress bar) / error (unsupported format, too large).
Actions:
Upload complete → Processing Status (Screen 4).

4. Add Book — Processing Status
Purpose: Show pipeline progress while the book is parsed and the graph is built. (Maps to status parsing → kg_built → kg_verified → ready.)
Contents:
Book title + cover.
Pipeline stepper with live state per stage:
Parsing & chunking.
Extracting concepts (nodes).
Inferring prerequisites (edges).
Ready for review.
Estimated time remaining / current step detail.
"We'll notify you when it's ready" note + option to leave the screen.
States:
In progress (per-step spinners/checkmarks).
Failed (with reason + retry, e.g. couldn't parse the file).
Done → prompts to review the graph.
Actions:
On completion → Graph Verification (Screen 5), or directly to Assessment Intro if a shared/verified graph already exists.
Can navigate away; progress continues in background (surfaces in Library + Notifications).

5. Graph Verification / Editor (uploader-reviewer)
Purpose: Let the uploader confirm or fix the auto-generated knowledge graph before it goes ready. This is the human-in-the-loop step that prevents bad edges from cascading into wrong locks and a wrong assessment.
Contents:
Interactive graph canvas — nodes and prerequisite edges laid out as a DAG.
Node panel (on select): title, auto-generated summary, source text excerpt (the chunk it came from), difficulty tier.
Edge panel (on select): from → to, type (prerequisite / related), confidence score.
Low-confidence edges highlighted for priority review.
Editing tools: add node, merge nodes, split node, delete node, add/remove/redirect edge, edit summary.
Cycle / validity warning banner (flags if an edit would break the DAG).
"Looks good — mark ready" confirmation button.
States:
Unverified (default after pipeline).
Editing (unsaved changes indicator).
Invalid (a proposed edge creates a cycle — blocked with explanation).
Actions:
Confirm → book becomes ready, routes to Assessment Intro (Screen 6).
For users who didn't upload (using a shared graph), this screen is skipped.

6. Assessment — Intro
Purpose: Explain the placement test before it starts.
Contents:
Book title.
Short explanation: "We'll ask a few questions per topic to find out what you already know, so we don't teach you things you've mastered."
What to expect: question types (MCQ → theory → applied), rough length, that it adapts and stops early on weak areas.
Note that confidence will be asked before answers are revealed.
"Begin assessment" CTA.
States: static.
Actions: Begin → Assessment Question (Screen 7).

7. Assessment — Question
Purpose: The adaptive placement test itself. Walks the DAG top-down in topological order, escalating difficulty per node only when the user passes the easier tier.
Contents:
Progress indicator: current topic name, how many topics covered / remaining (approximate, since it's adaptive).
Difficulty tier badge: MCQ / Theory / Applied.
Question body.
Answer input — varies by type:
MCQ: selectable options.
Theory: short free-text / structured answer.
Applied: scenario prompt + free-text.
Confidence selector shown before submitting / before correctness is revealed (e.g. Not sure / Fairly sure / Certain).
Submit button.
Skip / "I don't know" option (counts as a fail for that tier).
States:
Answered → brief feedback (correct / incorrect) and confidence-vs-correctness note.
Branch stop: when the user fails the easy tier of a node, a small inline note ("We'll cover this and what builds on it") and the test moves on — dependent nodes are marked needs-learning without re-testing.
Loading next question.
Actions:
Submit → next question, or → Assessment Results when the walk completes.

8. Assessment — Results
Purpose: Summarize placement and hand the user to their graph.
Contents:
Headline: "Here's where you're starting."
Summary stats: topics already mastered, topics to learn, topics locked (prereqs missing).
A condensed preview of the graph with the four-state coloring.
Highlighted weak spots / flagged confident-but-wrong topics (these get revision priority later).
"See my knowledge graph" CTA, and "Start learning" CTA.
States: static.
Actions:
→ Knowledge Graph Map (Screen 9) or → Book Home / Daily Plan (Screen 10).

9. Knowledge Graph — Map View
Purpose: The personalized concept map for one book — the overview the user navigates by.
Contents:
Interactive graph (pan / zoom) of nodes + prerequisite edges.
Four visual states with a legend:
Locked — greyed, disabled-looking (prerequisites unmet).
Available — unlocked, not yet learned.
Mastered — solid / colored.
Due — mastered but fading, flagged for revision.
Node tap → mini popover: title, state, mastery score, last reviewed, next due; buttons to learn or revise.
Filters / toggles: show only due, only available, only mastered.
Progress summary overlay: % mastered, % revealed.
States:
Fresh post-assessment (most nodes locked/available).
Progressively revealed as prerequisites clear (locked → available transitions are visible).
Actions:
Tap an available node → Node Detail (Screen 12) or straight into a Learning Session.
Tap a due node → Revision Session.
Locked node → shows "Complete X first" reason, no entry.

10. Book Home — Daily Plan
Purpose: What the user sees on opening a book — the day's tailored plan. This is the product's daily heartbeat.
Contents:
Book header: title, cover, per-book streak, overall progress ring.
Today's plan card, one of three modes:
Revise only — due reviews exist, no new capacity today.
Learn only — nothing due yet, here are new available topics.
Both — a mix of due reviews + new nodes, up to the daily cap.
Plan breakdown: list of the specific nodes scheduled today (revise vs learn labeled), estimated time.
Primary CTA: "Start today's plan."
Secondary entries: tabs / links to Learning, Revision, Graph.
Due-load indicator: how many nodes are due now and trend.
States:
All caught up (nothing due, nothing new pending) — celebratory state.
Backlog building (gentle nudge, but capped so it stays completable, not punishing).
Actions:
Start plan → routes through the scheduled sessions in order.
Tab into Course View (11), Revision (14), or Graph (9).

11. Course View (Coursera-style path)
Purpose: The linear/structured way through the book's topics, gated by prerequisites.
Contents:
Path / list of nodes in learning order (sections → topics), styled like a course curriculum.
Each node row: title, state icon (locked / available / in-progress / mastered / due), mastery score, short summary.
Locked nodes are visibly gated, each with a "Complete X first" reason pulled from the unmet prerequisite edge.
Section grouping with section-level progress bars.
Two tabs at top: Learning and Revision (both read the same KG + scheduling state).
States:
Locked rows non-tappable with reason.
In-progress rows show resume.
Actions:
Tap available/in-progress node → Node Detail (12) or Learning Session (13).
Switch to Revision tab → Revision Due List (14).

12. Node Detail
Purpose: Single-concept overview before entering a session.
Contents:
Node title + summary.
Source excerpt (the book chunk this concept maps to).
State + metrics: mastery score, recall strength, last reviewed, next due.
Prerequisites list (with their states) and what this node unlocks downstream.
Your past questions for this node (captured user_asked questions from prior learning sessions).
CTAs: "Learn this" / "Revise this" (whichever applies).
States:
Locked (CTA disabled, prereqs shown).
Mastered (shows revise + history).
Actions:
→ Learning Session (13) or Revision Session (15).

13. Learning Session (Socratic)
Purpose: Teach one node in a Socratic, question-driven style grounded in the book text.
Contents:
Conversation area — the back-and-forth dialogue (LLM probes with questions rather than lecturing).
Current node indicator (title + where it sits in the path).
User input box (free text); option to ask a question at any time.
Captured-question indicator — visual cue that the user's own questions are being saved to this node for later revision.
Reference panel (collapsible): the relevant source excerpt from the book.
Session controls: pause/save, end session, "I've got this" / mark understood.
Inline checks / mini-questions during the dialogue.
States:
Active dialogue.
Completing — on finish, shows mastery update and which downstream nodes just unlocked.
Actions:
Complete → node marked mastered, spaced-repetition params initialized, downstream nodes re-evaluated for unlock → returns to Course View / Daily Plan with the next item.

14. Revision — Due List
Purpose: Show what's due for review and let the user start.
Contents:
List of due nodes for this book, sorted by urgency (recall probability / overdue-ness).
Per row: node title, last reviewed, how overdue, source-of-question hint.
Count + estimated time.
"Start revision" CTA.
Toggle: due now / upcoming.
States:
Nothing due — caught-up state with next due date.
Backlog — capped, prioritized list.
Actions:
Start → Revision Session (15).

15. Revision Session
Purpose: Run targeted recall practice and feed results back into the schedule.
Contents:
One question at a time, drawn from the targeted revision bank: the user's own past questions (user_asked), assessment misses (assessment_miss), and items missed during learning.
Question body + answer input (type-appropriate).
Confidence selector before reveal (same pattern as assessment).
Self-grade / recall rating after reveal (e.g. Again / Hard / Good / Easy — FSRS-style), or auto-graded for MCQ.
Progress through the due set.
States:
In session.
Completion summary: how recall went, updated next-due dates, schedule adjusted.
Actions:
Each answer → grade feeds FSRS, recomputes next_due; node state may flip due → mastered.
Finish → back to Daily Plan / Revision Due List.

16. Progress / Stats
Purpose: Show learning health at book and account level.
Contents:
Global: total concepts mastered across the library, retention rate over time (chart), global daily streak + calendar heatmap.
Per book: % nodes mastered, % graph revealed, due-load trend over time, per-book streak.
Weak-spots list (low mastery / frequently missed nodes).
Milestones / badges (optional gamification).
States:
Early state (little data — encouraging copy).
Populated charts.
Actions:
Tap a book's stats → that book's Graph or Daily Plan.

17. Profile / Settings
Purpose: Account and learning preferences.
Contents:
Profile: name, email, avatar.
Learning settings: daily new-node cap (controls the "Both" plan load), daily reminder time, session length preference.
Notification preferences (reminders, due-review alerts, processing-done alerts).
Account: change password, manage shared-graph contributions, sign out, delete account.
States: standard form states.
Actions: save settings; sign out → Auth.

18. Notifications
Purpose: Surface time-sensitive events.
Contents:
"Your book is ready / needs review" (pipeline done).
"You have X reviews due today."
Streak reminders ("keep your streak alive").
Milestone notices.
States: read / unread.
Actions: tap → routes to the relevant screen (book, daily plan, graph review).

Cross-cutting UI elements (present across screens)
Navigation: persistent bottom nav or sidebar — Library, Today/Plan, Progress, Profile.
Streak + due badges visible on Library and within each book.
Four-state node coloring used consistently anywhere a node is shown (graph, course view, lists).
The same KG + scheduling state backs the Learning tab, Revision tab, and Graph view — they're three lenses on one data model, never out of sync.

