/**
 * Frontend → FastAPI adapter layer.
 *
 * Each function maps to one (or a few) real backend endpoints and returns the
 * DTO shape the pages expect (types/dto.ts). This file is the single place that
 * reconciles the UI's contract with the backend's actual routes, so pages never
 * call fetch()/apiGet() directly.
 */

import { apiGet, apiPost, apiPatch, apiDelete, apiUpload } from "./api-client";

import type {
  AuthResponseDTO,
  BookDetailDTO,
  BookSummaryDTO,
  BookStatusDTO,
  CreateBookDTO,
  CreateEdgeDTO,
  CreateNodeDTO,
  DailyPlanDTO,
  GraphDTO,
  KGEdgeDTO,
  KGNodeDTO,
  NotificationDTO,
  AssessmentAnswerRequestDTO,
  AssessmentAnswerResponseDTO,
  AssessmentCompleteResponseDTO,
  AssessmentNextResponseDTO,
  CompleteSessionResponseDTO,
  CreateSessionDTO,
  ProgressDTO,
  RevisionQueueDTO,
  ReviewRequestDTO,
  ReviewResponseDTO,
  SendMessageRequestDTO,
  SendMessageResponseDTO,
  SessionDTO,
  TutorMessageDTO,
  UpdateEdgeDTO,
  UpdateNodeDTO,
  UserDTO,
  UserUpdateDTO,
  QuestionType,
  NodeState,
} from "@/types/dto";

// ─────────────────────────────────────────────────────────────────────────────
// Mapping helpers (backend shape → UI shape)
// ─────────────────────────────────────────────────────────────────────────────

const lower = (s: string | null | undefined): NodeState =>
  ((s ?? "locked").toLowerCase() as NodeState);

const tierFromQType = (qt: string): QuestionType => {
  if (qt === "MCQ" || qt === "TRUE_FALSE") return "mcq";
  if (qt === "SCENARIO" || qt === "APPLIED") return "applied";
  return "theory";
};

const difficultyTier = (level: number): "beginner" | "intermediate" | "advanced" => {
  if (level <= 2) return "beginner";
  if (level === 3) return "intermediate";
  return "advanced";
};

const confToInt = (c: string): number =>
  c === "certain" ? 5 : c === "fairly_sure" ? 3 : 2;

const gradeToInt = (g: string): number =>
  ({ Again: 1, Hard: 2, Good: 3, Easy: 4 } as Record<string, number>)[g] ?? 3;

const today = () => new Date().toISOString().slice(0, 10);
const todayPlus = (days: number) =>
  new Date(Date.now() + days * 86400000).toISOString().slice(0, 10);

// ─────────────────────────────────────────────────────────────────────────────
// AUTH
// ─────────────────────────────────────────────────────────────────────────────

export async function loginUser(email: string, password: string): Promise<AuthResponseDTO> {
  // Backend returns { user, token }; NextAuth expects { access_token, user }.
  const raw = await apiPost<{ user: UserDTO; token: string }>("/auth/login", { email, password });
  return { access_token: raw.token, token_type: "bearer", user: raw.user };
}

export async function registerUser(name: string, email: string, password: string): Promise<AuthResponseDTO> {
  const raw = await apiPost<{ user: UserDTO; token: string }>("/auth/register", { name, email, password });
  return { access_token: raw.token, token_type: "bearer", user: raw.user };
}

// ─────────────────────────────────────────────────────────────────────────────
// USER
// ─────────────────────────────────────────────────────────────────────────────

export async function getMe(token: string): Promise<UserDTO> {
  return apiGet<UserDTO>("/users/me", { token });
}

export async function updateMe(token: string, data: UserUpdateDTO): Promise<UserDTO> {
  return apiPatch<UserDTO>("/users/me", data, { token });
}

// ─────────────────────────────────────────────────────────────────────────────
// BOOKS
// ─────────────────────────────────────────────────────────────────────────────

export async function listBooks(token: string): Promise<{ books: BookSummaryDTO[] }> {
  return apiGet<{ books: BookSummaryDTO[] }>("/books", { token });
}

export async function createBook(token: string, data: CreateBookDTO): Promise<{ book: BookDetailDTO }> {
  // Backend BookCreate uses is_public.
  return apiPost<{ book: BookDetailDTO }>("/books", { ...data, is_public: data.isPublic ?? false }, { token });
}

interface PersonalGraphNode {
  id: string; title: string; summary: string; difficulty: number; state: string;
  masteryScore: number; lastReviewed: string | null; nextDue: string | null; prerequisites: string[];
}
interface PersonalGraphSummary { total: number; mastered: number; locked: number; }
interface PersonalGraph {
  nodes: PersonalGraphNode[];
  edges: { fromNodeId: string; toNodeId: string; type: string }[];
  summary: PersonalGraphSummary;
}

/**
 * Full book + graph nodes. Merges book metadata (/books/{id}) with the
 * personalized graph reveal (/books/{id}/knowledge-graph) so node title,
 * summary, prerequisites and per-user state are all available to the pages.
 */
export async function getBook(token: string, bookId: string): Promise<{ book: BookDetailDTO }> {
  const [meta, graph] = await Promise.all([
    apiGet<{ book: Partial<BookDetailDTO> }>(`/books/${bookId}`, { token }).catch(() => ({ book: {} as Partial<BookDetailDTO> })),
    apiGet<PersonalGraph>(`/books/${bookId}/knowledge-graph`, { token }).catch(() => ({ nodes: [], edges: [], summary: {} as PersonalGraphSummary })),
  ]);

  const graphEdges = graph.edges ?? [];
  const nodes = (graph.nodes ?? []).map((n, idx) => ({
    id: n.id,
    bookId,
    title: n.title,
    summary: n.summary,
    sourceChunks: n.summary ? [n.summary] : [],
    difficultyTier: difficultyTier(n.difficulty),
    orderIndex: idx,
    sectionName: null,
    createdAt: today(),
    outgoingEdges: graphEdges
      .filter((e) => e.fromNodeId === n.id)
      .map((e) => ({ id: `${e.fromNodeId}-${e.toNodeId}`, fromNodeId: e.fromNodeId, toNodeId: e.toNodeId, type: String(e.type).toLowerCase() as KGEdgeDTO["type"], weight: 1, confidence: 1 })),
    incomingEdges: graphEdges
      .filter((e) => e.toNodeId === n.id)
      .map((e) => ({ id: `${e.fromNodeId}-${e.toNodeId}`, fromNodeId: e.fromNodeId, toNodeId: e.toNodeId, type: String(e.type).toLowerCase() as KGEdgeDTO["type"], weight: 1, confidence: 1 })),
    userNodeStates: [
      {
        id: `${n.id}-state`,
        userId: "",
        nodeId: n.id,
        bookId,
        state: lower(n.state),
        masteryScore: n.masteryScore ?? 0,
        recallStability: 0,
        recallDifficulty: 0,
        recallProbability: 0,
        lastReviewed: n.lastReviewed ?? null,
        nextDue: n.nextDue ?? null,
        lapseCount: 0,
        reviewCount: 0,
        createdAt: today(),
        updatedAt: today(),
      },
    ],
    questions: [],
  }));

  const m = meta.book ?? {};
  const book: BookDetailDTO = {
    id: bookId,
    ownerId: m.ownerId ?? "",
    title: m.title ?? "Untitled",
    author: m.author ?? null,
    sourceFile: null,
    coverUrl: null,
    status: (m.status as BookDetailDTO["status"]) ?? "ready",
    isPublic: m.isPublic ?? false,
    bookStreak: 0,
    lastStudied: null,
    createdAt: m.createdAt ?? today(),
    updatedAt: today(),
    nodes,
  };
  return { book };
}

export async function deleteBook(token: string, bookId: string): Promise<void> {
  return apiDelete<void>(`/books/${bookId}`, { token });
}

export async function uploadBookFile(
  token: string, bookId: string, file: File
): Promise<{ jobId: string; status: "queued" }> {
  const raw = await apiUpload<{ job_id?: string; jobId?: string }>(
    `/books/${bookId}/upload`, file, undefined, { token });
  return { jobId: raw.job_id ?? raw.jobId ?? "", status: "queued" };
}

export async function getBookStatus(token: string, bookId: string): Promise<BookStatusDTO> {
  return apiGet<BookStatusDTO>(`/books/${bookId}/status`, { token });
}

// ─────────────────────────────────────────────────────────────────────────────
// KNOWLEDGE GRAPH
// ─────────────────────────────────────────────────────────────────────────────

export async function getGraph(token: string, bookId: string): Promise<GraphDTO> {
  const g = await apiGet<GraphDTO>(`/books/${bookId}/graph`, { token });
  // Backend returns the raw enum (PREREQUISITE/RELATED); UI expects lowercase.
  return {
    ...g,
    edges: (g.edges ?? []).map((e) => ({ ...e, type: String(e.type).toLowerCase() as KGEdgeDTO["type"] })),
  };
}

export async function confirmGraph(token: string, bookId: string): Promise<{ success: true }> {
  await apiPost(`/books/${bookId}/graph/confirm`, {}, { token });
  return { success: true };
}

// Graph editor mutations (verify page) — backend editor endpoints are future work.
export async function createGraphNode(token: string, bookId: string, data: CreateNodeDTO): Promise<{ node: KGNodeDTO }> {
  return apiPost<{ node: KGNodeDTO }>(`/books/${bookId}/graph/nodes`, data, { token });
}
export async function updateGraphNode(token: string, bookId: string, nodeId: string, data: UpdateNodeDTO): Promise<{ node: KGNodeDTO }> {
  return apiPatch<{ node: KGNodeDTO }>(`/books/${bookId}/graph/nodes/${nodeId}`, data, { token });
}
export async function deleteGraphNode(token: string, bookId: string, nodeId: string): Promise<{ success: true }> {
  return apiDelete<{ success: true }>(`/books/${bookId}/graph/nodes/${nodeId}`, { token });
}
export async function createGraphEdge(token: string, bookId: string, data: CreateEdgeDTO): Promise<{ edge: KGEdgeDTO }> {
  return apiPost<{ edge: KGEdgeDTO }>(`/books/${bookId}/graph/edges`, data, { token });
}
export async function updateGraphEdge(token: string, bookId: string, edgeId: string, data: UpdateEdgeDTO): Promise<{ edge: KGEdgeDTO }> {
  return apiPatch<{ edge: KGEdgeDTO }>(`/books/${bookId}/graph/edges/${edgeId}`, data, { token });
}
export async function deleteGraphEdge(token: string, bookId: string, edgeId: string): Promise<{ success: true }> {
  return apiDelete<{ success: true }>(`/books/${bookId}/graph/edges/${edgeId}`, { token });
}

// ─────────────────────────────────────────────────────────────────────────────
// DAILY PLAN
// ─────────────────────────────────────────────────────────────────────────────

interface BackendPlanItem {
  conceptId: string; title: string; orderIndex: number; state: string;
  mastery: number; estimatedMinutes: number; unmetPrerequisites: string[];
}
interface BackendDailyPlan {
  bookId: string; mode: DailyPlanDTO["mode"]; revise: BackendPlanItem[]; learn: BackendPlanItem[];
  totalDue: number; totalNew: number; estimatedMinutes: number;
}

export async function getDailyPlan(token: string, bookId: string): Promise<DailyPlanDTO> {
  const [plan, curr] = await Promise.all([
    apiGet<BackendDailyPlan>(`/books/${bookId}/daily-plan`, { token }),
    apiGet<{ totalConcepts: number; masteredConcepts: number }>(`/books/${bookId}/curriculum`, { token })
      .catch(() => ({ totalConcepts: 0, masteredConcepts: 0 })),
  ]);
  const mk = (it: BackendPlanItem, planType: "revise" | "learn") => ({
    nodeId: it.conceptId,
    planType,
    node: { title: it.title, summary: "", difficultyTier: "beginner" as const },
    state: lower(it.state),
    lastReviewed: null,
    nextDue: null,
    recallProbability: it.mastery,
  });
  const planNodes = [
    ...plan.revise.map((it) => mk(it, "revise")),
    ...plan.learn.map((it) => mk(it, "learn")),
  ];
  const total = curr.totalConcepts || planNodes.length;
  const mastered = curr.masteredConcepts || 0;
  return {
    mode: plan.mode,
    planNodes,
    dueCount: plan.totalDue,
    availableCount: plan.totalNew,
    totalNodes: total,
    masteredCount: mastered,
    progressPct: total ? Math.round((100 * mastered) / total) : 0,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// ASSESSMENT  (backend is assessment_id-keyed; we track it per book here)
// ─────────────────────────────────────────────────────────────────────────────

interface BackendQuestion {
  id: string; concept_id: string; concept_name: string; question_type: string;
  difficulty_level: number; bloom_level: string; question_text: string; options: string[];
}
interface BackendStart { assessment_id: string; question: BackendQuestion | null; progress: { concepts_total: number }; completed: boolean; }
interface BackendAnswer {
  result: { is_correct: boolean; correctness: string; score: number; feedback: string; explanation: string; correct_answer: string; correct_option: number | null; branch_stopped: boolean };
  next_question: BackendQuestion | null; progress: { concepts_total: number; concepts_resolved: number }; completed: boolean;
}

interface AssessSession {
  assessmentId: string;
  totalTopics: number;
  topicIndex: number;
  pending: { question: BackendQuestion | null; completed: boolean } | null;
}

// Persisted in sessionStorage (not a module variable) so the active assessment
// survives reloads / Next.js Fast Refresh between rendering a question and
// submitting the answer.
const ASSESS_KEY = (bookId: string) => `lexis_assess_${bookId}`;
function loadAssess(bookId: string): AssessSession | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(ASSESS_KEY(bookId));
  return raw ? (JSON.parse(raw) as AssessSession) : null;
}
function saveAssess(bookId: string, s: AssessSession): void {
  if (typeof window !== "undefined") window.sessionStorage.setItem(ASSESS_KEY(bookId), JSON.stringify(s));
}

const mapQuestion = (q: BackendQuestion) => ({
  question: {
    id: q.id,
    nodeId: q.concept_id,
    type: tierFromQType(q.question_type),
    difficulty: (q.difficulty_level <= 2 ? "easy" : q.difficulty_level === 3 ? "medium" : "hard") as "easy" | "medium" | "hard",
    source: "generated" as const,
    body: q.question_text,
    options: q.options && q.options.length ? q.options : null,
    answer: null,
    explanation: null,
    createdAt: today(),
  },
  nodeId: q.concept_id,
  nodeTitle: q.concept_name,
  tier: tierFromQType(q.question_type),
});

export async function startAssessment(token: string, bookId: string): Promise<AssessmentNextResponseDTO> {
  const raw = await apiPost<BackendStart>("/assessments", { book_id: bookId }, { token });
  const sess: AssessSession = {
    assessmentId: raw.assessment_id,
    totalTopics: raw.progress?.concepts_total ?? 0,
    topicIndex: 0,
    pending: null,
  };
  saveAssess(bookId, sess);
  if (raw.completed || !raw.question) return { done: true };
  const mapped = mapQuestion(raw.question);
  return { done: false, ...mapped, topicIndex: 0, totalTopics: sess.totalTopics, topoOrder: [] };
}

export async function submitAssessmentAnswer(
  token: string, data: AssessmentAnswerRequestDTO
): Promise<AssessmentAnswerResponseDTO> {
  const sess = loadAssess(data.bookId);
  if (!sess) throw new Error("No active assessment session.");
  const raw = await apiPost<BackendAnswer>(
    `/assessments/${sess.assessmentId}/responses`,
    { question_id: data.questionId, answer: String(data.answer), confidence_level: confToInt(String(data.confidence)) },
    { token }
  );
  sess.pending = { question: raw.next_question, completed: raw.completed };
  saveAssess(data.bookId, sess);
  return {
    correct: raw.result.is_correct,
    isMastered: raw.result.is_correct,
    explanation: raw.result.explanation || raw.result.feedback || null,
    correctAnswer: raw.result.correct_answer || null,
    correctOption: raw.result.correct_option ?? null,
  };
}

export async function getNextAssessmentQuestion(_token: string, bookId: string): Promise<AssessmentNextResponseDTO> {
  const sess = loadAssess(bookId);
  if (!sess || !sess.pending || sess.pending.completed || !sess.pending.question) {
    return { done: true };
  }
  sess.topicIndex += 1;
  saveAssess(bookId, sess);
  const mapped = mapQuestion(sess.pending.question);
  return { done: false, ...mapped, topicIndex: sess.topicIndex, totalTopics: sess.totalTopics, topoOrder: [] };
}

interface BackendComplete {
  summary: { mastered: number; ready: number; learning: number; weak: number; unknown: number; locked: number };
  outcomes: { concept_id: string; concept_name: string; mastery_estimate: number; placement_state: string }[];
}
const placementToState = (p: string): NodeState =>
  p === "MASTERED" ? "mastered" : p === "READY" ? "available" : p === "LEARNING" ? "available" : "locked";

export async function completeAssessment(token: string, bookId: string): Promise<AssessmentCompleteResponseDTO> {
  const sess = loadAssess(bookId);
  if (!sess) throw new Error("No active assessment session.");
  const raw = await apiPost<BackendComplete>(`/assessments/${sess.assessmentId}/complete`, {}, { token });
  return {
    mastered: raw.summary.mastered,
    available: raw.summary.ready + raw.summary.learning,
    locked: raw.summary.locked,
    weakSpots: raw.outcomes.filter((o) => o.placement_state === "WEAK").map((o) => o.concept_name),
    graphPreview: raw.outcomes.map((o) => ({ id: o.concept_id, title: o.concept_name, state: placementToState(o.placement_state) })),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// SESSIONS (Socratic tutor)  → backend /lessons
// ─────────────────────────────────────────────────────────────────────────────

interface BackendTurn { turnIndex: number; userMessage: string; assistantMessage: string; hintLevel: number; }

export async function createSession(
  token: string, data: CreateSessionDTO
): Promise<{ session: SessionDTO; transcript: TutorMessageDTO[] }> {
  const raw = await apiPost<{ sessionId: string; conceptId: string; transcript?: BackendTurn[] }>(
    "/lessons", { book_id: data.bookId, concept_id: data.nodeIds[0] }, { token });
  // Backend resumes an in-progress session and returns its transcript; replay it.
  const transcript: TutorMessageDTO[] = [];
  for (const t of raw.transcript ?? []) {
    transcript.push({ role: "user", content: t.userMessage, timestamp: new Date().toISOString() });
    transcript.push({ role: "assistant", content: t.assistantMessage, timestamp: new Date().toISOString() });
  }
  return {
    session: {
      id: raw.sessionId, userId: "", bookId: data.bookId, mode: data.mode,
      nodeIds: data.nodeIds, completedAt: null, createdAt: new Date().toISOString(),
    },
    transcript,
  };
}

export interface QuizQuestionDTO {
  id: string; conceptId: string; questionType: string; questionText: string; options: string[];
}
export interface QuizResultDTO {
  passed: boolean; score: number; unlockedConcepts: string[]; message: string;
  results: { questionId: string; isCorrect: boolean; correctAnswer: string; explanation: string }[];
}

export async function generateQuiz(token: string, sessionId: string): Promise<{ questions: QuizQuestionDTO[]; conceptTitle: string }> {
  const raw = await apiPost<{ questions: QuizQuestionDTO[]; conceptTitle: string }>(
    `/lessons/${sessionId}/quiz`, {}, { token });
  return { questions: raw.questions ?? [], conceptTitle: raw.conceptTitle };
}

export async function gradeQuiz(
  token: string, sessionId: string, responses: { question_id: string; answer: string }[]
): Promise<QuizResultDTO> {
  return apiPost<QuizResultDTO>(`/lessons/${sessionId}/quiz/grade`, { responses }, { token });
}

export async function sendMessage(
  token: string, sessionId: string, data: SendMessageRequestDTO
): Promise<SendMessageResponseDTO> {
  const raw = await apiPost<{ tutorResponse: string; followUpQuestion: string; hint: string; questionCaptured: boolean }>(
    `/lessons/${sessionId}/tutor`,
    { message: data.message, hint_level: 0, is_question: data.isQuestion },
    { token }
  );
  const parts = [raw.tutorResponse, raw.followUpQuestion].filter(Boolean);
  return {
    response: parts.join("\n\n"),
    savedQuestionId: raw.questionCaptured ? "saved" : undefined,
  };
}

export async function completeSession(token: string, sessionId: string): Promise<CompleteSessionResponseDTO> {
  const raw = await apiPost<{ status: string; unlockedConcepts: string[] }>(
    `/lessons/${sessionId}/complete`, {}, { token });
  return {
    masteryScore: 0.9,
    unlockedNodes: raw.unlockedConcepts ?? [],
    unlockedNodeIds: [],
    nextDue: todayPlus(1),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// REVISION  → backend /books/{id}/revision + /concepts/{cid}/review
// ─────────────────────────────────────────────────────────────────────────────

interface BackendDue { bookId: string; count: number; due: { conceptId: string; title: string; nextDue: string | null; retrievability: number }[]; }

export async function getRevisionQueue(token: string, bookId: string): Promise<RevisionQueueDTO> {
  const raw = await apiGet<BackendDue>(`/books/${bookId}/revision`, { token });
  const card = (d: BackendDue["due"][number]) => ({
    nodeId: d.conceptId,
    nodeTitle: d.title,
    question: {
      id: `${d.conceptId}-recall`,
      nodeId: d.conceptId,
      type: "theory" as const,
      difficulty: "medium" as const,
      source: "generated" as const,
      body: `Recall and explain in your own words: ${d.title}`,
      options: null,
      answer: null,
      explanation: null,
      createdAt: today(),
    },
    source: "generated" as const,
    recallProbability: d.retrievability,
    daysOverdue: 0,
  });
  return { due: raw.due.map(card), upcoming: [] };
}

export async function reviewNode(
  token: string, nodeId: string, data: ReviewRequestDTO
): Promise<ReviewResponseDTO> {
  const raw = await apiPost<{ intervalDays: number; stability: number; grade: number }>(
    `/books/${data.bookId}/concepts/${nodeId}/review`,
    { grade: gradeToInt(String(data.grade)) },
    { token }
  );
  return {
    nextDue: todayPlus(raw.intervalDays ?? 1),
    interval: raw.intervalDays ?? 1,
    state: gradeToInt(String(data.grade)) >= 3 ? "mastered" : "due",
    newStability: raw.stability ?? 0,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// PROGRESS  → backend /dashboard
// ─────────────────────────────────────────────────────────────────────────────

interface BackendDashboard {
  conceptsMastered: number; conceptsTracked: number; avgMastery: number;
  totalDue: number; globalStreak: number; studiedToday: boolean;
  books: { bookId: string; title: string; totalConcepts: number; masteredConcepts: number; percentMastered: number; dueToday: number }[];
  weakSpots: { title: string; bookTitle: string; mastery: number }[];
}

export async function getProgress(token: string): Promise<ProgressDTO> {
  const d = await apiGet<BackendDashboard>("/dashboard", { token });
  return {
    global: {
      totalConceptsMastered: d.conceptsMastered,
      totalConcepts: d.conceptsTracked,
      retentionRate: d.avgMastery,
      globalStreak: d.globalStreak,
      activityHistory: [],
    },
    books: d.books.map((b) => ({
      bookId: b.bookId, title: b.title, masteredCount: b.masteredConcepts,
      totalNodes: b.totalConcepts, progressPct: b.percentMastered, dueToday: b.dueToday, bookStreak: 0,
    })),
    weakSpots: d.weakSpots.map((w, i) => ({
      nodeId: `weak-${i}`, nodeTitle: w.title, bookId: "", bookTitle: w.bookTitle,
      masteryScore: w.mastery, lapseCount: 0,
    })),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// NOTIFICATIONS
// ─────────────────────────────────────────────────────────────────────────────

interface BackendNotification { id: string; type: string; message: string; read: boolean; link: string | null; }

export async function listNotifications(token: string): Promise<{ notifications: NotificationDTO[] }> {
  const raw = await apiGet<{ notifications: BackendNotification[] }>("/notifications", { token });
  return {
    notifications: (raw.notifications ?? []).map((n) => ({
      id: n.id,
      userId: "",
      bookId: null,
      type: (n.type === "due_reviews" ? "reviews_due"
        : n.type === "needs_review" ? "book_needs_review"
        : n.type === "take_assessment" ? "book_ready"
        : n.type === "streak" ? "streak_reminder"
        : "milestone") as NotificationDTO["type"],
      title: n.message,
      body: "",
      read: n.read,
      link: n.link,
      createdAt: new Date().toISOString(),
    })),
  };
}

// Notification read-state isn't persisted server-side yet; no-op for the UI.
export async function markNotificationRead(_token: string, notificationId: string): Promise<{ notification: NotificationDTO }> {
  return {
    notification: {
      id: notificationId, userId: "", bookId: null, type: "milestone",
      title: "", body: "", read: true, link: null, createdAt: new Date().toISOString(),
    },
  };
}

export async function markAllNotificationsRead(_token: string): Promise<{ success: true }> {
  return { success: true };
}
