# LearnGraph AI — Frontend Architecture Review
## Principal Frontend Architect · Staff Product Engineer · Technical Lead

> **Review Date:** 2026-06-07  
> **Reviewer Role:** Principal Frontend Architect / Staff Product Engineer  
> **HLD Source of Truth:** `design.md`  
> **UI Spec Source of Truth:** `uispec.md`  
> **Codebase:** `genAIproject/` (Next.js 16, React 19, Prisma + SQLite, Tailwind v4, Zustand, ReactFlow, Recharts, Anthropic SDK)

---

## Executive Summary

The frontend was **not built for a different platform**. It was designed from day one for the Adaptive Book-Learning Platform described in `design.md`. There are **zero DSA-platform artifacts**, zero course-centric assumptions, and zero legacy remnants. The stack is appropriate, the data model is aligned, and the architecture is coherent.

The frontend is **partially complete** — the skeleton exists for all 18 required screens, but several screens have **shallow implementations** (thin stubs that fetch data without full UI fidelity to the spec), **critical API gaps** (no real-time pipeline polling, no graph edit persistence, no tutor streaming, no progress analytics endpoint), and **type safety gaps** throughout.

The most critical blocker before backend development starts is the **grading function in the assessment API**, which is literally a `Math.random() > 0.3` placeholder. This means the assessment engine — the foundation of placement, locking, and curriculum personalization — is non-functional. This must be fixed before backend work begins or it will poison the test data in the database.

---

## Scores

| Dimension | Score | Rationale |
|---|---|---|
| **Architecture Alignment** | **91/100** | Built for the new vision; no DSA artifacts; correct data model |
| **Frontend Readiness for Backend Start** | **72/100** | All routes exist; several screens are shallow; 3 critical bugs |
| **Type Safety** | **48/100** | Heavy use of `Record<string, unknown>` throughout pages |
| **API Contract Completeness** | **65/100** | Core contracts exist; 8 missing endpoints; no streaming contract |
| **Graph Readiness** | **70/100** | Render + 4 states work; node editing not persisted; no DAG layout |
| **Assessment Readiness** | **40/100** | UI complete; grading is `Math.random()` — non-functional |
| **Revision System Readiness** | **78/100** | FSRS implemented correctly; revision session UI complete |
| **Learning Session Readiness** | **75/100** | Socratic loop works; no streaming; question capture logic is client-side heuristic |

---

## Critical Issues (Block Backend Start)

### CRIT-1: Assessment Grading is `Math.random()`

**File:** `src/app/api/assessment/route.ts` (Lines 179–182)

```typescript
async function gradeAnswer(questionId: string, answer: string | number): Promise<boolean> {
  return Math.random() > 0.3; // placeholder for demo
}
```

**Impact:** Every assessment result is random. All `UserNodeState` records written during assessment are garbage. The DAG-based placement that assessment → graph reveal → locking → curriculum all depend on is producing random data. Any backend work that reads `UserNodeState` to infer placement correctness will work against corrupted test data.

**Fix:** The assessment engine must store questions in the `Question` table with answers at generation time, then compare the submitted answer against `question.answer` at grade time.

---

### CRIT-2: File Processing is Synchronous and Blocks the Request

**File:** `src/app/api/books/[bookId]/process/route.ts`

The entire KG construction pipeline (Claude Opus call for concept extraction + Claude Opus call for edge inference) runs **synchronously inside a single API handler**. This will hit Vercel's 60-second function timeout on any real book. The `status` field (`parsing → kg_built → kg_verified`) is set optimistically within the same request — it's never actually polled; the processing page cannot show real pipeline progress.

**Fix:** Move the pipeline to a background worker (BullMQ / Inngest / Trigger.dev). The `/process` endpoint should enqueue the job and return immediately. Add `GET /api/books/{bookId}/status` for polling.

---

### CRIT-3: Upload Sends Raw Text Content in JSON Body

**File:** `src/app/upload/page.tsx` (Lines 51–59)

```typescript
const text = await file.text().catch(() => `Content from ${file.name}`);
fetch(`/api/books/${bookId}/process`, {
  body: JSON.stringify({ content: text.slice(0, 20000) }),
});
```

- PDF files cannot be read with `file.text()` — binary content will be garbled
- The `slice(0, 20000)` hard-cap silently truncates books
- There is no actual file upload API; the `sourceFile` field on `Book` is never populated

**Fix:** Implement proper multipart file upload to object storage (S3/R2). Backend must use a PDF parser (pdf-parse, pdfjs-dist) server-side.

---

## High Priority Issues

### HIGH-1: `globalStreak` is Hardcoded
`src/app/library/page.tsx` line 64: `const globalStreak = 7; // would come from user data`
No logic anywhere updates `globalStreak` or `lastActiveDate` on session complete or review submit.

### HIGH-2: Retention Rate is Hardcoded Mock
`src/app/progress/page.tsx` line 36: `const retentionRate = 87; // mock`
Chart data uses `Math.random()`. The entire progress page is a facade.

### HIGH-3: Graph Edits in Verify Page Are Not Persisted
`src/app/book/[bookId]/verify/page.tsx`: ReactFlow `onConnect` lets users add edges in the UI, but there is no API call that writes mutations back to the database. User edits are silently discarded on confirm.
Also: add/merge/split/delete node tools from the spec are completely absent.

### HIGH-4: `UserNodeState` Initialization After Assessment is Incomplete
`src/app/api/assessment/route.ts`: The `complete` action does not initialize `UserNodeState` rows for nodes that were never reached by the adaptive walk. Skipped nodes have no state and won't appear in the daily plan.

**Fix:** After `complete`, upsert a `locked` state for every node with no existing `UserNodeState` row.

### HIGH-5: Revision Session Fetches Entire Book for Each Card (N+1)
`src/app/book/[bookId]/revision/session/page.tsx` lines 54–69:
```typescript
const nodeRes = await fetch(`/api/books/${bookId}`).then(...);
```
This is called inside `Promise.all(dueItems.map(...))` — firing once **per due node**. 20 due nodes = 20 parallel full-book requests.

### HIGH-6: No Question Persistence in Learning Session
`src/app/book/[bookId]/learn/[nodeId]/page.tsx` lines 63–68:
```typescript
const isQuestion = msg.includes("?") || msg.toLowerCase().startsWith("what") ...
if (isQuestion) setQuestionSaved(true);
```
The UI shows "question saved," but the question is **never actually persisted** to the `Question` table.

---

## Medium Priority Issues

| ID | File | Issue |
|---|---|---|
| MED-1 | `assessment/question/page.tsx` | Assessment re-calls `action: "start"` on every next-topic, reconstructing full topological sort from DB each time |
| MED-2 | `graph/page.tsx` | `applyFilter` re-fetches the whole book on every filter toggle |
| MED-3 | `library/page.tsx` | Global search input renders but is not wired — no search handler |
| MED-4 | `progress/page.tsx` | Chart uses `Math.random()` — different data on every render |
| MED-5 | All pages | `Record<string, unknown>` pervasive — TypeScript provides false safety |
| MED-6 | `upload/page.tsx` | Fire-and-forget processing means errors from `/process` are invisible |
| MED-7 | All session routes | No rate limiting on Anthropic API calls — unbounded LLM cost exposure |

---

## Phase 1: Architecture Alignment Audit

**Previous platform assumed:** None. The codebase was built specifically for the Adaptive Book-Learning Platform.

**Evidence of correct architecture:**
- Book-centric routes: `/book/[bookId]/*`
- DAG utilities in `lib/dag.ts` (topological sort, cycle detection, descendants)
- FSRS-4.5 implementation in `lib/fsrs.ts`
- Prisma schema models: `Book`, `KGNode`, `KGEdge`, `UserNodeState`, `Question`, `Session`, `Notification`
- Four node states implemented consistently: `locked`, `available`, `mastered`, `due`
- The `kg_verified` status triggering graph review before assessment

**No mismatches found. Architecture alignment is excellent.**

---

## Phase 2: Route Structure Audit

### Current Route Tree

```
/ (root)                            → Auth/Splash
/library                            → Library (Bookshelf)
/upload                             → Add Book — Upload
/progress                           → Progress / Stats
/settings                           → Profile / Settings
/notifications                      → Notifications
/book/[bookId]                      → Book Home / Daily Plan
/book/[bookId]/processing           → Processing Status
/book/[bookId]/verify               → Graph Verification / Editor
/book/[bookId]/assessment           → Assessment Intro
/book/[bookId]/assessment/question  → Assessment Question
/book/[bookId]/assessment/results   → Assessment Results
/book/[bookId]/graph                → Knowledge Graph Map View
/book/[bookId]/course               → Course View
/book/[bookId]/node/[nodeId]        → Node Detail
/book/[bookId]/learn/[nodeId]       → Learning Session (Socratic)
/book/[bookId]/revision             → Revision Due List
/book/[bookId]/revision/session     → Revision Session
```

**All 18 required screens from the UI spec have a corresponding route. Route coverage is 100%.**

### Missing API Routes

- `GET /api/books/{bookId}/status` — needed for real-time processing polling
- `POST /api/books/{bookId}/graph/nodes` — create node
- `PATCH /api/books/{bookId}/graph/nodes/{nodeId}` — edit node
- `DELETE /api/books/{bookId}/graph/nodes/{nodeId}` — delete node
- `POST /api/books/{bookId}/graph/edges` — create edge
- `PATCH /api/books/{bookId}/graph/edges/{edgeId}` — update edge
- `DELETE /api/books/{bookId}/graph/edges/{edgeId}` — delete edge
- `GET /api/progress` — progress analytics
- `POST /api/notifications/{id}/read` — mark notification read

**Dead Routes:** None.  
**Legacy Routes:** None.

---

## Phase 3: Screen Coverage Audit

| Screen | Status | Missing Elements |
|---|---|---|
| **1. Auth** | COMPLETE | OAuth/Google absent; "Forgot password" is a no-op |
| **2. Library** | PARTIAL | Global search unwired; streak hardcoded; "Start today's plan" routes to `books[0]` not most-due book |
| **3. Upload** | PARTIAL | PDF parsing broken (file.text() on binary); no file storage; no upload progress bar |
| **4. Processing Status** | PARTIAL | No real-time per-step polling; static "Building..." text only |
| **5. Graph Verification** | PARTIAL | No node CRUD tools; edits not persisted; no cycle warning on edit |
| **6. Assessment Intro** | COMPLETE | All spec elements present |
| **7. Assessment Question** | PARTIAL | Always MCQ — no tier escalation; grading is random |
| **8. Assessment Results** | PARTIAL | No condensed graph preview; confident-but-wrong data not surfaced |
| **9. KG Map View** | PARTIAL | Node popover lacks mastery score display; naive grid layout (not DAG-aware) |
| **10. Book Home / Daily Plan** | COMPLETE | Three-mode logic correct; due-load indicator present |
| **11. Course View** | COMPLETE | Two tabs; section grouping; locked reasons from prereqs; mastery scores |
| **12. Node Detail** | COMPLETE | All spec elements: prereqs, unlocks, past questions, source excerpt |
| **13. Learning Session** | PARTIAL | No streaming; questions not persisted; transcript not stored |
| **14. Revision Due List** | COMPLETE | Due now/Upcoming tabs; urgency sort; start CTA |
| **15. Revision Session** | PARTIAL | assessment_miss questions ignored; completion summary lacks updated nextDue |
| **16. Progress / Stats** | PARTIAL | Retention hardcoded; chart uses random data; calendar heatmap absent |
| **17. Settings** | UNKNOWN | File not reviewed |
| **18. Notifications** | UNKNOWN | File not reviewed |

---

## Phase 4: Component Architecture Audit

### Component Inventory

| Component | File | Classification | Verdict |
|---|---|---|---|
| `Sidebar` | `components/Sidebar.tsx` | Reusable Layout | Keep |
| `NodeStateBadge` | `components/NodeStateBadge.tsx` | Reusable Utility | Keep |
| `ProgressRing` | `components/ProgressRing.tsx` | Reusable Visual | Keep |
| `SessionProvider` | `components/SessionProvider.tsx` | Provider Wrapper | Keep |
| `ui/*` | `components/ui/` | Design System | Keep |

### Missing Components

| Component | Purpose | Complexity |
|---|---|---|
| `PipelineStatusStepper` | Visual stepper for book processing stages | Medium |
| `GraphCanvas (enhanced)` | Verify-mode with node CRUD tools | High |
| `GraphNodePopover` | Mini popover on node click in map view | Low |
| `AssessmentResultsGraph` | Condensed graph preview in results screen | Medium |
| `RetentionChart` | Recharts retention over time | Low |
| `CalendarHeatmap` | Activity heatmap on progress screen | Medium |
| `StreakWidget` | Global streak with "studied today" state | Low |
| `TutorMessageBubble` | Streaming-aware chat bubble | Medium |
| `FSRSGradeButtons` | Extract from revision session (currently inline) | Low |
| `ConfidenceSelector` | Duplicated in 2 files — extract | Low |

### Deletions

None. No dead components found.

### Refactors

- All page components: replace `Record<string, unknown>` with typed DTOs
- `graph/page.tsx`: extract node popover as `GraphNodePopover`
- `revision/session/page.tsx`: extract `ConfidenceSelector` + `GradeButtons`

---

## Phase 5: State Management Audit

### Current Architecture

All state is **local React `useState` per page**. Zustand is installed but unused. No TanStack Query.

### Problems

| Domain | Problem |
|---|---|
| Current book data | `GET /api/books/{bookId}` is called 3+ times per workflow (graph + course + learn all fetch the full book) |
| Assessment state | `topoOrder` array managed client-side — state lost on refresh |
| Graph edits | Not synchronized across components |
| Notifications | Unread count not updated across pages |
| Daily plan | Re-fetched on every return to book home |

### Recommended State Architecture

```typescript
// Server state (TanStack Query — preferred)
// useBook(bookId)          → GET /api/books/{bookId}         staleTime: 30s
// useBooks()               → GET /api/books                  staleTime: 60s
// useDailyPlan(bookId)     → GET /api/books/{bookId}/daily-plan  staleTime: 5min

// Client state (Zustand — ephemeral only)
interface AssessmentStore {
  bookId: string | null;
  topoOrder: string[];
  currentIndex: number;
  results: Map<string, { mastered: boolean; confidence: string }>;
  reset: () => void;
}

interface SessionStore {
  sessionId: string | null;
  nodeId: string | null;
  messages: TutorMessageDTO[];
}

interface NotificationsStore {
  unreadCount: number;
  markRead: (id: string) => void;
}
```

**Recommendation:** Install `@tanstack/react-query`. Use Zustand only for pure client-side ephemeral state.

---

## Phase 6: Type System Audit

### Current Problems

Pages use `Record<string, unknown>` and then cast with `as string`, `as number`. TypeScript does not catch breaking API contract changes.

### Required DTOs

```typescript
// ============================================================
// DOMAIN: Books
// ============================================================
interface BookDTO {
  id: string;
  ownerId: string;
  title: string;
  author: string | null;
  sourceFile: string | null;
  coverUrl: string | null;
  status: "uploaded" | "parsing" | "kg_built" | "kg_verified" | "ready";
  isPublic: boolean;
  bookStreak: number;
  lastStudied: string | null;
  createdAt: string;
  updatedAt: string;
}

interface BookSummaryDTO extends BookDTO {
  totalNodes: number;
  masteredNodes: number;
  dueToday: number;
  progressPct: number;
}

interface BookDetailDTO extends BookDTO {
  nodes: KGNodeDetailDTO[];
}

// ============================================================
// DOMAIN: Graph
// ============================================================
interface KGNodeDTO {
  id: string;
  bookId: string;
  title: string;
  summary: string;
  sourceChunks: string[];
  difficultyTier: "beginner" | "intermediate" | "advanced";
  orderIndex: number;
  sectionName: string | null;
  createdAt: string;
}

interface KGNodeDetailDTO extends KGNodeDTO {
  outgoingEdges: KGEdgeDTO[];
  incomingEdges: KGEdgeDTO[];
  userNodeStates: UserNodeStateDTO[];
  questions: QuestionDTO[];
}

interface KGEdgeDTO {
  id: string;
  fromNodeId: string;
  toNodeId: string;
  type: "prerequisite" | "related";
  weight: number;
  confidence: number;
}

type NodeState = "locked" | "available" | "in_progress" | "mastered" | "due";

interface UserNodeStateDTO {
  id: string;
  userId: string;
  nodeId: string;
  bookId: string;
  state: NodeState;
  masteryScore: number;
  recallStability: number;
  recallDifficulty: number;
  recallProbability: number;
  lastReviewed: string | null; // YYYY-MM-DD
  nextDue: string | null;      // YYYY-MM-DD
  lapseCount: number;
  reviewCount: number;
  createdAt: string;
  updatedAt: string;
}

// ============================================================
// DOMAIN: Assessment
// ============================================================
type QuestionType = "mcq" | "theory" | "applied";
type QuestionSource = "generated" | "user_asked" | "assessment_miss";
type ConfidenceLevel = "not_sure" | "fairly_sure" | "certain";

interface QuestionDTO {
  id: string;
  nodeId: string;
  type: QuestionType;
  difficulty: "easy" | "medium" | "hard";
  source: QuestionSource;
  body: string;
  options: string[] | null;
  answer: number | null;
  explanation: string | null;
  createdAt: string;
}

interface AssessmentStartResponseDTO {
  question: QuestionDTO;
  nodeId: string;
  nodeTitle: string;
  tier: QuestionType;
  topicIndex: number;
  totalTopics: number;
  topoOrder: string[];
  done?: false;
}

interface AssessmentAnswerResponseDTO {
  correct: boolean;
  isMastered: boolean;
  explanation?: string;
}

interface AssessmentCompleteResponseDTO {
  mastered: number;
  available: number;
  locked: number;
  weakSpots: string[];
  graphPreview: Array<{ id: string; title: string; state: NodeState }>;
}

// ============================================================
// DOMAIN: Learning Session
// ============================================================
interface TutorMessageDTO {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  isQuestion?: boolean;
  savedQuestionId?: string;
}

interface SessionMessageRequestDTO {
  message: string;
  nodeId: string;
  isQuestion: boolean;
}

interface SessionMessageResponseDTO {
  response: string;
  savedQuestionId?: string;
}

interface SessionCompleteResponseDTO {
  masteryScore: number;
  unlockedNodes: string[];
  unlockedNodeIds: string[];
  nextDue: string;
}

// ============================================================
// DOMAIN: Revision
// ============================================================
type FSRSGrade = "Again" | "Hard" | "Good" | "Easy";

interface RevisionCardDTO {
  nodeId: string;
  nodeTitle: string;
  question: QuestionDTO;
  source: QuestionSource;
  recallProbability: number;
  daysOverdue: number;
}

interface RevisionReviewRequestDTO {
  grade: FSRSGrade;
  confidence: ConfidenceLevel;
  bookId: string;
}

interface RevisionReviewResponseDTO {
  nextDue: string;
  interval: number;
  state: NodeState;
}

// ============================================================
// DOMAIN: Daily Plan
// ============================================================
type PlanMode = "revise_only" | "learn_only" | "both" | "all_caught_up";

interface PlanNodeDTO {
  nodeId: string;
  planType: "revise" | "learn";
  node: { title: string; summary: string; difficultyTier: string };
  state: NodeState;
  lastReviewed: string | null;
  nextDue: string | null;
  recallProbability: number;
}

interface DailyPlanResponseDTO {
  mode: PlanMode;
  planNodes: PlanNodeDTO[];
  dueCount: number;
  availableCount: number;
  totalNodes: number;
  masteredCount: number;
  progressPct: number;
}

// ============================================================
// DOMAIN: Progress
// ============================================================
interface ProgressDTO {
  global: {
    totalConceptsMastered: number;
    totalConcepts: number;
    retentionRate: number;
    globalStreak: number;
    activityHistory: Array<{
      date: string;
      conceptsReviewed: number;
      conceptsLearned: number;
    }>;
  };
  books: Array<{
    bookId: string;
    title: string;
    masteredCount: number;
    totalNodes: number;
    progressPct: number;
    dueToday: number;
    bookStreak: number;
  }>;
  weakSpots: Array<{
    nodeId: string;
    nodeTitle: string;
    bookId: string;
    bookTitle: string;
    masteryScore: number;
    lapseCount: number;
  }>;
}

// ============================================================
// DOMAIN: Notifications
// ============================================================
type NotificationType =
  | "book_ready"
  | "book_needs_review"
  | "reviews_due"
  | "streak_reminder"
  | "milestone";

interface NotificationDTO {
  id: string;
  userId: string;
  bookId: string | null;
  type: NotificationType;
  title: string;
  body: string;
  read: boolean;
  link: string | null;
  createdAt: string;
}

// ============================================================
// DOMAIN: User / Settings
// ============================================================
interface UserDTO {
  id: string;
  email: string;
  name: string;
  avatarUrl: string | null;
  dailyNewNodeCap: number;
  dailyReminderTime: string | null;
  sessionLengthPref: number;
  notifyReminders: boolean;
  notifyDueReviews: boolean;
  notifyProcessing: boolean;
  globalStreak: number;
  lastActiveDate: string | null;
}

interface UserUpdateDTO {
  name?: string;
  dailyNewNodeCap?: number;
  dailyReminderTime?: string;
  sessionLengthPref?: number;
  notifyReminders?: boolean;
  notifyDueReviews?: boolean;
  notifyProcessing?: boolean;
}
```

---

## Phase 7: API Contract Extraction

All endpoints require auth via NextAuth session cookie.

---

### AUTH

**POST /api/auth/register**
```
Request:  { name, email, password }
Response: { user: { id, email, name } }
Errors:   400 { error: "Email already in use" }
```

---

### BOOKS

**GET /api/books**
```
Response: { books: BookSummaryDTO[] }
Cache:    60s stale time
```

**POST /api/books**
```
Request:  { title, author?, isPublic }
Response: { book: BookDTO }
Status:   201
```

**GET /api/books/{bookId}**
```
Response: { book: BookDetailDTO }
Cache:    30s stale time
Notes:    Most-called endpoint. MUST be cached at query layer.
          Returns all nodes with userNodeStates for the authenticated user.
```

**PATCH /api/books/{bookId}**
```
Request:  Partial<{ title, author, isPublic }>
Response: { book: BookDTO }
```

---

### BOOK PIPELINE

**POST /api/books/{bookId}/process**
```
[MUST CHANGE TO ASYNC]
Request:  multipart file upload (PDF/EPUB/TXT)
Response: { jobId: string, status: "queued" }
Notes:    Must return immediately. Job runs in background worker.
          Current sync implementation will timeout on real books.
```

**GET /api/books/{bookId}/status** ← MISSING — CREATE THIS
```
Response: {
  status: "uploaded" | "parsing" | "kg_built" | "kg_verified" | "ready",
  currentStep: "Parsing & chunking" | "Extracting concepts" | "Inferring prerequisites" | "Ready for review",
  stepIndex: 0–3,
  totalSteps: 4,
  estimatedSecondsRemaining: number,
  error?: string
}
Polling:  Frontend polls every 3s while status is not terminal
```

---

### GRAPH

**GET /api/books/{bookId}/graph**
```
Response: { nodes: KGNodeDTO[], edges: KGEdgeDTO[] }
```

**POST /api/books/{bookId}/graph**
```
Request:  { action: "confirm" }
Response: { success: true }
Effect:   Sets book.status = "ready", initializes all UserNodeState as "locked"
```

**POST /api/books/{bookId}/graph/nodes** ← MISSING
```
Request:  { title, summary, difficultyTier, sectionName? }
Response: { node: KGNodeDTO }
```

**PATCH /api/books/{bookId}/graph/nodes/{nodeId}** ← MISSING
```
Request:  Partial<{ title, summary, difficultyTier }>
Response: { node: KGNodeDTO }
```

**DELETE /api/books/{bookId}/graph/nodes/{nodeId}** ← MISSING
```
Response: { success: true }
Notes:    Cascade-delete edges and UserNodeState
```

**POST /api/books/{bookId}/graph/edges** ← MISSING
```
Request:  { fromNodeId, toNodeId, type: "prerequisite" | "related", confidence }
Response: { edge: KGEdgeDTO }
Errors:   409 { error: "Would create cycle" }
```

**PATCH /api/books/{bookId}/graph/edges/{edgeId}** ← MISSING
```
Request:  Partial<{ type, confidence }>
Response: { edge: KGEdgeDTO }
```

**DELETE /api/books/{bookId}/graph/edges/{edgeId}** ← MISSING
```
Response: { success: true }
```

---

### DAILY PLAN

**GET /api/books/{bookId}/daily-plan**
```
Response: DailyPlanResponseDTO
Cache:    5 minutes stale time
```

---

### ASSESSMENT

**POST /api/assessment**
```
action: "start"
  Request:  { bookId, action: "start", nodeIndex? }
  Response: AssessmentStartResponseDTO | { done: true }
  CRITICAL: Must persist generated question to Question table before returning.

action: "answer"
  Request:  { bookId, action: "answer", nodeId, questionId, answer, confidence }
  Response: AssessmentAnswerResponseDTO
  CRITICAL: Must fetch Question by questionId and compare against question.answer.
            Must NOT use Math.random().

action: "complete"
  Request:  { bookId, action: "complete" }
  Response: AssessmentCompleteResponseDTO
  CRITICAL: Must upsert "locked" UserNodeState for all nodes with no state row.
            Must return graphPreview with all node states.
```

---

### SESSIONS

**POST /api/sessions**
```
Request:  { bookId, mode: "learning" | "revision", nodeIds: string[] }
Response: { session: SessionDTO }
Status:   201
```

**POST /api/sessions/{sessionId}/message**
```
Request:  { message, nodeId, isQuestion }
Response: { response, savedQuestionId? }
Must:
  1. Persist user message to session.transcript
  2. If isQuestion, create Question { source: "user_asked", body: message, nodeId }
  3. Call Anthropic grounded in node.sourceChunks
  4. Persist AI response to transcript
  5. Return response
Preferred: Streaming via Response / SSE
```

**POST /api/sessions/{sessionId}/complete**
```
Request:  {}
Response: SessionCompleteResponseDTO
Must:
  1. Update UserNodeState: state = "mastered", masteryScore = 1.0
  2. Initialize FSRS params for the node
  3. Set nextDue = today + initial interval
  4. Re-evaluate downstream nodes for unlock
  5. Return unlockedNodes list
```

---

### REVISION

**POST /api/nodes/{nodeId}/review**
```
Request:  { grade: "Again"|"Hard"|"Good"|"Easy", confidence, bookId }
Response: { nextDue, interval, state }
Already implemented. Missing: does not update globalStreak/lastActiveDate.
```

**GET /api/books/{bookId}/revision-queue** ← MISSING
```
Response: {
  due: RevisionCardDTO[],      // sorted by recallProbability ASC
  upcoming: RevisionCardDTO[]  // sorted by nextDue ASC
}
Notes:    Question priority: user_asked > assessment_miss > generated
```

---

### PROGRESS

**GET /api/progress** ← MISSING
```
Response: ProgressDTO
Notes:
  retentionRate = avg(recallProbability) for all UserNodeState where state = "mastered"
  activityHistory = Session records grouped by date
  weakSpots = UserNodeState where masteryScore < 0.4 AND state != "locked"
```

---

### USER

**GET /api/user**
```
Response: { user: UserDTO }
```

**PATCH /api/user**
```
Request:  UserUpdateDTO
Response: { user: UserDTO }
```

---

### NOTIFICATIONS

**GET /api/notifications**
```
Response: { notifications: NotificationDTO[] }
```

**POST /api/notifications/{id}/read** ← MISSING
```
Response: { notification: NotificationDTO }
```

---

## Phase 8: Knowledge Graph Readiness

| Capability | Status | Notes |
|---|---|---|
| Graph Rendering | WORKING | ReactFlow with 4-state coloring |
| Four Node Visual States | WORKING | locked/available/mastered/due correctly differentiated |
| Node Popover | WORKING | Side panel with title, state, mastery, last reviewed, next due |
| Filters | WORKING | all/due/available/mastered/locked |
| Progress Overlay | WORKING | % mastered · % revealed |
| Graph Verification Mode | PARTIAL | Can add edges; no node CRUD; edits not persisted |
| Low-confidence Edge Highlighting | WORKING | Animated orange edges below 0.6 |
| DAG-respecting Layout | MISSING | Naive grid layout, not topology-aware |
| Cycle Warning on Edit | MISSING | `wouldCreateCycle` exists in lib/dag.ts but not wired to verify UI |
| Node Edit Form | MISSING | Cannot change title/summary/difficulty |
| Edge Delete | MISSING | No delete interaction |
| Graph Refresh After Session | MISSING | After mastering a node, graph state doesn't auto-update |

**Graph Readiness Score: 70/100**

**Required Libraries:**
- `@dagrejs/dagre` — DAG layout for ReactFlow (recommended)

---

## Phase 9: Assessment Readiness

**Assessment Readiness Score: 40/100**

### Critical Gaps

1. **Grading is `Math.random()`** — see CRIT-1
2. **MCQ-only** — no MCQ→theory→applied tier escalation per node
3. **Questions not persisted** — cannot grade against stored answers
4. **Assessment walk is client-managed** — `topoIndex` managed in `useState`, lost on refresh
5. **Missing UserNodeState initialization on complete**
6. **Results screen missing confident-but-wrong list and graph preview**

### Required Fixes

1. Persist questions to DB before serving → grade by comparing submitted answer to `question.answer`
2. After MCQ pass, generate theory question for same node; after theory pass, optionally serve applied
3. Assessment walk state should be server-side (session-stored) or at minimum resilient to page refresh
4. `complete` action must upsert locked states for all untested nodes
5. Surface `assessment_miss` questions in results screen

---

## Phase 10: Learning Session Readiness

**Learning Session Readiness Score: 75/100**

### What Works
- Session creation
- Message send/receive (full round-trip)
- Completion with node unlock propagation
- Source text reference panel
- "Question saved" visual indicator (UI only)

### What's Missing

1. **No streaming** — full Anthropic round-trip before response renders. Fix: `client.messages.stream()` with `Response` streaming
2. **Questions not persisted** — `isQuestion` heuristic is client-side and unreliable; server must persist
3. **Session transcript not stored** — `transcript` field on Session is never updated during conversation
4. **No inline mini-questions/checks** — spec mentions inline checks during dialogue; absent
5. **Tutor grounding** — must verify Anthropic system prompt actually uses `node.sourceChunks`

---

## Phase 11: Revision System Readiness

**Revision System Readiness Score: 78/100**

### What Works
- FSRS-4.5 (`lib/fsrs.ts`) — well-implemented, correct algorithm
- `POST /api/nodes/{nodeId}/review` — correctly updates all FSRS state fields
- Revision due list with due/upcoming separation
- FSRS grade buttons (Again/Hard/Good/Easy)
- Confidence selector
- Completion summary with grade breakdown

### What's Missing

1. **N+1 in revision session** — HIGH-5
2. **Question source priority** — `assessment_miss` questions ignored
3. **Completion summary** — updated `nextDue` per card not displayed
4. **Global streak not updated** — after review, `user.globalStreak` unchanged
5. **Retention visualization** — progress page shows hardcoded 87%

---

## Phase 12: Backend Handoff Document

### Priority 1 — Fix Before Any Backend Work

| Task | Why |
|---|---|
| Fix `gradeAnswer()` in `/api/assessment` | Random grading = corrupted UserNodeState; all subsequent backend work reads garbage data |
| Add `GET /api/books/{bookId}/status` | Processing page cannot show real progress |
| Move `/api/books/{bookId}/process` to async worker | Synchronous LLM calls will timeout on real books |

### Priority 2 — Core Gaps to Build

| Endpoint | Consumer Screen |
|---|---|
| `GET /api/progress` | Progress page |
| `POST /api/notifications/{id}/read` | Notifications page |
| `GET /api/books/{bookId}/revision-queue` | Revision session (eliminates N+1) |

### Priority 3 — Graph Editor Persistence

All six graph node/edge CRUD endpoints (see Phase 7).

---

### Session Message Handler Requirements (for backend team)

```
POST /api/sessions/{sessionId}/message

Required behavior:
1. Load session from DB (nodeIds, transcript)
2. Load node by nodeIds[0] → get sourceChunks
3. Persist user message to session.transcript
4. If isQuestion=true:
   a. Create Question record:
      { nodeId, type: "theory", source: "user_asked", body: message, difficulty: "easy" }
   b. Return savedQuestionId in response
5. Build Anthropic system prompt:
   """
   You are a Socratic tutor teaching the concept: "{node.title}".
   Ground your teaching in this text from the book:
   {node.sourceChunks[0..2].join("\n\n")}
   
   Rules:
   - Never lecture. Ask probing questions to guide understanding.
   - Stay faithful to the book text.
   - Keep responses under 150 words.
   """
6. Call Anthropic (streaming preferred)
7. Persist AI response to session.transcript
8. Return { response, savedQuestionId? }
```

### Assessment Grading Fix Requirements

```
POST /api/assessment (action: "start")
- After generating question, persist to Question table
- Return actual DB question.id

POST /api/assessment (action: "answer")
- Fetch Question by questionId from DB
- For MCQ: compare (answer as number) === question.answer
- For theory/applied: use Anthropic to evaluate free-text answer
- Proceed with existing UserNodeState update logic

POST /api/assessment (action: "complete")
- Upsert state="locked" for every KGNode in this book
  that has no UserNodeState row for this user
- Return graphPreview: all UserNodeState rows with node titles and states
```

### Global Streak Logic (add to review + session complete handlers)

```typescript
const today = new Date().toISOString().split("T")[0];
const user = await prisma.user.findUnique({ where: { id: userId } });
const yesterday = new Date(Date.now() - 86400000).toISOString().split("T")[0];

const newStreak = user.lastActiveDate === yesterday
  ? user.globalStreak + 1
  : user.lastActiveDate === today
    ? user.globalStreak
    : 1; // streak broken — reset

await prisma.user.update({
  where: { id: userId },
  data: { globalStreak: newStreak, lastActiveDate: today }
});
```

---

## Phase 13: PR Plan

### PR 1 — Assessment Engine Fix
**Goal:** Make assessment grading functional and deterministic.

**Files:**
- `src/app/api/assessment/route.ts` — persist questions; implement real grading; complete action initializes all UserNodeState; return graphPreview

**Dependencies:** None  
**Effort:** 1 day  
**Risk:** High (foundation of all placement)  
**Backend Deps:** None

---

### PR 2 — Async Pipeline + Status Polling
**Goal:** Move book processing to background; add polling endpoint; fix file upload.

**Files:**
- `src/app/api/books/[bookId]/process/route.ts` — enqueue job only
- `src/app/api/books/[bookId]/status/route.ts` — NEW
- `src/app/book/[bookId]/processing/page.tsx` — add polling loop, per-step stepper
- `src/app/upload/page.tsx` — multipart upload or presigned URL

**Dependencies:** Queue infrastructure decision (Inngest recommended for Next.js)  
**Effort:** 2–3 days  
**Risk:** High  
**Backend Deps:** Queue infrastructure

---

### PR 3 — Graph Edit Persistence
**Goal:** Make graph verification editor persist mutations.

**Files:**
- `src/app/api/books/[bookId]/graph/nodes/route.ts` — NEW
- `src/app/api/books/[bookId]/graph/nodes/[nodeId]/route.ts` — NEW
- `src/app/api/books/[bookId]/graph/edges/route.ts` — NEW
- `src/app/api/books/[bookId]/graph/edges/[edgeId]/route.ts` — NEW
- `src/app/book/[bookId]/verify/page.tsx` — wire mutations; add node CRUD tools; cycle check on connect

**Dependencies:** PR 1  
**Effort:** 2 days  
**Risk:** Medium  
**Backend Deps:** None

---

### PR 4 — Type System Overhaul
**Goal:** Replace `Record<string, unknown>` with typed DTOs.

**Files:** All page.tsx files; create `src/types/dto.ts`

**Dependencies:** None (safe to parallelize)  
**Effort:** 1.5 days  
**Risk:** Low  
**Backend Deps:** None

---

### PR 5 — Session Message Grounding + Question Persistence
**Goal:** Tutor grounded in source text; user questions persisted.

**Files:**
- `src/app/api/sessions/[sessionId]/message/route.ts` — grounded system prompt; question persistence; transcript update
- `src/app/api/sessions/[sessionId]/complete/route.ts` — verify unlock logic
- `src/app/book/[bookId]/learn/[nodeId]/page.tsx` — remove client-side question heuristic

**Dependencies:** PR 4  
**Effort:** 1 day  
**Risk:** Medium  
**Backend Deps:** Anthropic API key

---

### PR 6 — Progress Analytics Endpoint
**Goal:** Progress page shows real data.

**Files:**
- `src/app/api/progress/route.ts` — NEW: aggregate retention, activity, weak spots
- `src/app/progress/page.tsx` — consume real data; add CalendarHeatmap component

**Effort:** 1.5 days  
**Risk:** Low

---

### PR 7 — Revision Queue + Streak Logic
**Goal:** Fix N+1 in revision session; add streak tracking; fix question priority.

**Files:**
- `src/app/api/books/[bookId]/revision-queue/route.ts` — NEW
- `src/app/api/nodes/[nodeId]/review/route.ts` — add streak update
- `src/app/book/[bookId]/revision/session/page.tsx` — use revision-queue; fix N+1

**Dependencies:** PR 1 (assessment_miss questions need real assessment data)  
**Effort:** 1 day  
**Risk:** Medium

---

### PR 8 — Graph Layout + UX Polish
**Goal:** DAG-respecting layout; cache invalidation after sessions.

**Files:**
- `src/app/book/[bookId]/graph/page.tsx` — dagre layout
- `src/app/book/[bookId]/learn/[nodeId]/page.tsx` — invalidate graph cache on complete
- Install `@dagrejs/dagre`

**Dependencies:** PRs 4, 5  
**Effort:** 1 day  
**Risk:** Low

---

### PR 9 — Streak Widget + Notifications Read
**Goal:** Library shows real streak; notifications markable as read.

**Files:**
- `src/app/api/notifications/[id]/read/route.ts` — NEW
- `src/app/library/page.tsx` — consume user.globalStreak from /api/user
- `src/app/notifications/page.tsx` — wire mark-read

**Dependencies:** PR 7  
**Effort:** 0.5 days  
**Risk:** Low

---

### PR 10 — TanStack Query Migration
**Goal:** Eliminate N+1 fetching; add proper caching layer.

**Files:** Install `@tanstack/react-query`; wrap app; migrate all fetch calls; create `src/query/` directory.

**Dependencies:** PR 4  
**Effort:** 2 days  
**Risk:** Medium (broad change)

---

## Recommended Folder Structure

```
src/
├── app/
│   ├── api/
│   │   ├── assessment/
│   │   ├── auth/
│   │   ├── books/[bookId]/
│   │   │   ├── daily-plan/
│   │   │   ├── graph/
│   │   │   │   ├── edges/[edgeId]/      ← NEW
│   │   │   │   ├── edges/               ← NEW
│   │   │   │   ├── nodes/[nodeId]/      ← NEW
│   │   │   │   └── nodes/               ← NEW
│   │   │   ├── process/
│   │   │   ├── revision-queue/          ← NEW
│   │   │   └── status/                  ← NEW
│   │   ├── nodes/[nodeId]/review/
│   │   ├── notifications/
│   │   │   └── [id]/read/               ← NEW
│   │   ├── progress/                    ← NEW
│   │   ├── sessions/[sessionId]/
│   │   └── user/
│   └── book/[bookId]/
│       ├── assessment/
│       ├── course/
│       ├── graph/
│       ├── learn/[nodeId]/
│       ├── node/[nodeId]/
│       ├── processing/
│       ├── revision/
│       └── verify/
├── components/
│   ├── ui/
│   ├── graph/                           ← NEW
│   ├── assessment/                      ← NEW: ConfidenceSelector extracted
│   ├── revision/                        ← NEW: FSRSGradeButtons extracted
│   ├── session/                         ← NEW: TutorMessageBubble
│   └── progress/                        ← NEW: CalendarHeatmap, RetentionChart
├── lib/
│   ├── auth.ts, dag.ts, db.ts, fsrs.ts, utils.ts
├── types/
│   └── dto.ts                           ← NEW: All DTOs from Phase 6
├── hooks/                               ← NEW
├── stores/                              ← NEW: Zustand (assessmentStore, sessionStore)
└── query/                               ← NEW: TanStack Query keys + prefetch helpers
```

---

## Implementation Order

| Day | PR | Task |
|---|---|---|
| 1 | PR 1 | Fix assessment grading — this unblocks all testing |
| 2–3 | PR 2 | Async pipeline + status polling — unblocks full upload→learn flow |
| 4 | PR 4 | Type system overhaul — enables all subsequent PRs to be type-safe |
| 5 | PR 5 | Session message grounding + question persistence |
| 6–7 | PR 3 | Graph edit persistence |
| 8 | PR 6 + PR 9 | Progress analytics + streak + notifications |
| 9 | PR 7 | Revision queue fix + N+1 elimination |
| 10 | PR 8 | Graph layout polish |
| 11–12 | PR 10 | TanStack Query migration |

---

## Can Backend Development Start?

> ### ✅ YES — Conditionally

**Confidence: 82%**

### Safe to Start Now

| Area | Reason |
|---|---|
| Auth API | Contracts are final |
| Book CRUD | Correctly implemented and specified |
| Daily Plan | Correctly implemented |
| FSRS Review | Correctly implemented |
| Session Create + Complete | Contracts clear |
| Notifications CRUD | Schema and contracts clear |
| User Settings | Schema and contracts clear |
| Progress Analytics Endpoint | DTO defined; no frontend dependency |
| Graph Editor APIs | DTOs defined; contracts clear |
| Book Status Polling API | Contract defined |

### Do NOT Start Until Frontend Fixes Are In

| Area | Wait For | Reason |
|---|---|---|
| Assessment Engine (server-side) | PR 1 | Random grading produces garbage data; backend would build on wrong test state |
| Pipeline Worker Architecture | PR 2 | Queue technology decision must be made before implementing async pipeline |
| File Upload API | PR 2 | Upload mechanism (multipart vs presigned URL) must be settled first |

---

## Summary

The frontend is architecturally sound and built for the correct platform. The Prisma schema is complete and frozen. FSRS is correct. DAG utilities are correct. All 18 screens and all required routes exist.

Three critical bugs exist — all fixable in 2–3 days by one engineer. Once those are resolved, full-speed parallel backend development can begin across all remaining API domains. The API contracts in Phase 7 are sufficient for backend engineers to begin implementation immediately on all non-blocked areas.
