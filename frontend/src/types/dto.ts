/**
 * Domain Transfer Objects — Frontend ↔ FastAPI contract.
 *
 * Every interface here maps to a Pydantic model on the FastAPI side.
 * The naming convention follows snake_case → camelCase transformation
 * that will be handled by fastapi's response_model + json serialization.
 *
 * Backend team: these interfaces are the exact shape the frontend expects.
 * Do NOT change field names without updating both sides.
 */

// ─────────────────────────────────────────────────────────────────────────────
// PRIMITIVES / SHARED
// ─────────────────────────────────────────────────────────────────────────────

export type NodeState = "locked" | "available" | "in_progress" | "mastered" | "due";
export type QuestionType = "mcq" | "theory" | "applied";
export type QuestionSource = "generated" | "user_asked" | "assessment_miss";
export type ConfidenceLevel = "not_sure" | "fairly_sure" | "certain";
export type FSRSGrade = "Again" | "Hard" | "Good" | "Easy";
export type PlanMode = "revise_only" | "learn_only" | "both" | "all_caught_up";
export type BookStatus = "uploaded" | "parsing" | "kg_built" | "kg_verified" | "ready";
export type DifficultyTier = "beginner" | "intermediate" | "advanced";
export type EdgeType = "prerequisite" | "related";
export type NotificationType =
  | "book_ready"
  | "book_needs_review"
  | "reviews_due"
  | "streak_reminder"
  | "milestone";

// ─────────────────────────────────────────────────────────────────────────────
// AUTH
// ─────────────────────────────────────────────────────────────────────────────

export interface RegisterRequestDTO {
  name: string;
  email: string;
  password: string;
}

export interface LoginRequestDTO {
  email: string;
  password: string;
}

export interface AuthResponseDTO {
  access_token: string;
  token_type: "bearer";
  user: UserDTO;
}

// ─────────────────────────────────────────────────────────────────────────────
// USER
// ─────────────────────────────────────────────────────────────────────────────

export interface UserDTO {
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
  lastActiveDate: string | null; // YYYY-MM-DD
  createdAt: string;
}

export interface UserUpdateDTO {
  name?: string;
  dailyNewNodeCap?: number;
  dailyReminderTime?: string;
  sessionLengthPref?: number;
  notifyReminders?: boolean;
  notifyDueReviews?: boolean;
  notifyProcessing?: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// BOOKS
// ─────────────────────────────────────────────────────────────────────────────

export interface BookDTO {
  id: string;
  ownerId: string;
  title: string;
  author: string | null;
  sourceFile: string | null;
  coverUrl: string | null;
  status: BookStatus;
  isPublic: boolean;
  bookStreak: number;
  lastStudied: string | null; // YYYY-MM-DD
  createdAt: string;
  updatedAt: string;
}

/** Returned by GET /books (list) — includes derived stats */
export interface BookSummaryDTO extends BookDTO {
  totalNodes: number;
  masteredNodes: number;
  dueToday: number;
  progressPct: number; // 0–100
}

/** Returned by GET /books/{id} — full book with graph nodes */
export interface BookDetailDTO extends BookDTO {
  nodes: KGNodeDetailDTO[];
}

export interface CreateBookDTO {
  title: string;
  author?: string;
  isPublic?: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// PIPELINE / PROCESSING
// ─────────────────────────────────────────────────────────────────────────────

export type ProcessingStep =
  | "Parsing & chunking"
  | "Extracting concepts"
  | "Inferring prerequisites"
  | "Ready for review";

export interface BookStatusDTO {
  status: BookStatus;
  currentStep: ProcessingStep;
  stepIndex: number;        // 0–3
  totalSteps: 4;
  estimatedSecondsRemaining: number | null;
  error: string | null;     // non-null if pipeline failed
}

// ─────────────────────────────────────────────────────────────────────────────
// KNOWLEDGE GRAPH — NODES & EDGES
// ─────────────────────────────────────────────────────────────────────────────

export interface KGNodeDTO {
  id: string;
  bookId: string;
  title: string;
  summary: string;
  sourceChunks: string[];   // parsed from JSON in DB
  difficultyTier: DifficultyTier;
  orderIndex: number;
  sectionName: string | null;
  createdAt: string;
}

/** Node returned inside BookDetailDTO — includes edges + user state */
export interface KGNodeDetailDTO extends KGNodeDTO {
  outgoingEdges: KGEdgeDTO[];
  incomingEdges: KGEdgeDTO[];
  userNodeStates: UserNodeStateDTO[];
  questions: QuestionDTO[];
}

export interface KGEdgeDTO {
  id: string;
  fromNodeId: string;
  toNodeId: string;
  type: EdgeType;
  weight: number;       // default 1.0
  confidence: number;   // 0.0–1.0; < 0.6 = low-confidence, highlight in verify
}

export interface GraphDTO {
  nodes: KGNodeDTO[];
  edges: KGEdgeDTO[];
}

// Graph editor mutations — used by verify page
export interface CreateNodeDTO {
  title: string;
  summary: string;
  difficultyTier: DifficultyTier;
  sectionName?: string;
}

export interface UpdateNodeDTO {
  title?: string;
  summary?: string;
  difficultyTier?: DifficultyTier;
  sectionName?: string;
}

export interface CreateEdgeDTO {
  fromNodeId: string;
  toNodeId: string;
  type: EdgeType;
  confidence: number;
}

export interface UpdateEdgeDTO {
  type?: EdgeType;
  confidence?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// USER NODE STATE (the per-user overlay on the graph)
// ─────────────────────────────────────────────────────────────────────────────

export interface UserNodeStateDTO {
  id: string;
  userId: string;
  nodeId: string;
  bookId: string;
  state: NodeState;
  masteryScore: number;       // 0.0–1.0
  recallStability: number;    // FSRS S (days)
  recallDifficulty: number;   // FSRS D (1–10)
  recallProbability: number;  // 0.0–1.0
  lastReviewed: string | null; // YYYY-MM-DD
  nextDue: string | null;      // YYYY-MM-DD
  lapseCount: number;
  reviewCount: number;
  createdAt: string;
  updatedAt: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// QUESTIONS
// ─────────────────────────────────────────────────────────────────────────────

export interface QuestionDTO {
  id: string;
  nodeId: string;
  type: QuestionType;
  difficulty: "easy" | "medium" | "hard";
  source: QuestionSource;
  body: string;
  options: string[] | null;  // MCQ options (A, B, C, D)
  answer: number | null;     // 0-indexed correct option (MCQ only)
  explanation: string | null;
  createdAt: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// ASSESSMENT ENGINE
// ─────────────────────────────────────────────────────────────────────────────

export interface AssessmentStartResponseDTO {
  done: false;
  question: QuestionDTO;
  nodeId: string;
  nodeTitle: string;
  tier: QuestionType;
  topicIndex: number;
  totalTopics: number;
  topoOrder: string[]; // all node IDs in topological order
}

export interface AssessmentDoneResponseDTO {
  done: true;
}

export type AssessmentNextResponseDTO =
  | AssessmentStartResponseDTO
  | AssessmentDoneResponseDTO;

export interface AssessmentAnswerRequestDTO {
  bookId: string;
  nodeId: string;
  questionId: string;
  answer: number | string; // number for MCQ (index), string for theory/applied
  confidence: ConfidenceLevel;
}

export interface AssessmentAnswerResponseDTO {
  correct: boolean;
  isMastered: boolean;
  explanation: string | null;
}

export interface AssessmentCompleteResponseDTO {
  mastered: number;
  available: number;
  locked: number;
  weakSpots: string[]; // node titles of confident-but-wrong answers
  graphPreview: Array<{ id: string; title: string; state: NodeState }>;
}

// ─────────────────────────────────────────────────────────────────────────────
// DAILY PLAN
// ─────────────────────────────────────────────────────────────────────────────

export interface PlanNodeDTO {
  nodeId: string;
  planType: "revise" | "learn";
  node: {
    title: string;
    summary: string;
    difficultyTier: DifficultyTier;
  };
  state: NodeState;
  lastReviewed: string | null;
  nextDue: string | null;
  recallProbability: number; // 0.0–1.0
}

export interface DailyPlanDTO {
  mode: PlanMode;
  planNodes: PlanNodeDTO[];
  dueCount: number;
  availableCount: number;
  totalNodes: number;
  masteredCount: number;
  progressPct: number; // 0–100
}

// ─────────────────────────────────────────────────────────────────────────────
// SESSIONS (Learning / Tutor)
// ─────────────────────────────────────────────────────────────────────────────

export interface CreateSessionDTO {
  bookId: string;
  mode: "learning" | "revision";
  nodeIds: string[];
}

export interface SessionDTO {
  id: string;
  userId: string;
  bookId: string;
  mode: "learning" | "revision";
  nodeIds: string[];
  completedAt: string | null;
  createdAt: string;
}

export interface TutorMessageDTO {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  isQuestion?: boolean;
  savedQuestionId?: string; // set when a user question was persisted
}

export interface SendMessageRequestDTO {
  message: string;
  nodeId: string;
  isQuestion: boolean;
}

export interface SendMessageResponseDTO {
  response: string;
  savedQuestionId?: string;
}

export interface CompleteSessionResponseDTO {
  masteryScore: number;
  unlockedNodes: string[];   // node titles
  unlockedNodeIds: string[]; // node IDs
  nextDue: string;           // first scheduled review date (YYYY-MM-DD)
}

// ─────────────────────────────────────────────────────────────────────────────
// REVISION
// ─────────────────────────────────────────────────────────────────────────────

export interface RevisionCardDTO {
  nodeId: string;
  nodeTitle: string;
  question: QuestionDTO;
  source: QuestionSource;
  recallProbability: number;
  daysOverdue: number;
}

export interface RevisionQueueDTO {
  due: RevisionCardDTO[];
  upcoming: RevisionCardDTO[];
}

export interface ReviewRequestDTO {
  grade: FSRSGrade;
  confidence: ConfidenceLevel;
  bookId: string;
}

export interface ReviewResponseDTO {
  nextDue: string;    // YYYY-MM-DD
  interval: number;   // days
  state: NodeState;
  newStability: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// PROGRESS / ANALYTICS
// ─────────────────────────────────────────────────────────────────────────────

export interface ActivityDayDTO {
  date: string;              // YYYY-MM-DD
  conceptsReviewed: number;
  conceptsLearned: number;
}

export interface BookProgressDTO {
  bookId: string;
  title: string;
  masteredCount: number;
  totalNodes: number;
  progressPct: number;
  dueToday: number;
  bookStreak: number;
}

export interface WeakSpotDTO {
  nodeId: string;
  nodeTitle: string;
  bookId: string;
  bookTitle: string;
  masteryScore: number;
  lapseCount: number;
}

export interface ProgressDTO {
  global: {
    totalConceptsMastered: number;
    totalConcepts: number;
    retentionRate: number;       // 0.0–1.0
    globalStreak: number;
    activityHistory: ActivityDayDTO[];
  };
  books: BookProgressDTO[];
  weakSpots: WeakSpotDTO[];
}

// ─────────────────────────────────────────────────────────────────────────────
// NOTIFICATIONS
// ─────────────────────────────────────────────────────────────────────────────

export interface NotificationDTO {
  id: string;
  userId: string;
  bookId: string | null;
  type: NotificationType;
  title: string;
  body: string;
  read: boolean;
  link: string | null;   // route to push to on tap
  createdAt: string;
}
