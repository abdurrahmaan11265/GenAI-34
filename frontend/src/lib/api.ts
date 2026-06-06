/**
 * All frontend → FastAPI API calls.
 *
 * Every function in this module corresponds 1:1 to a FastAPI endpoint.
 * Pages import from here — never call fetch() or apiGet() directly in components.
 *
 * Token is obtained from NextAuth session:
 *   const { data: session } = useSession();
 *   const token = (session?.user as { accessToken?: string })?.accessToken ?? "";
 */

import {
  apiGet, apiPost, apiPatch, apiDelete, apiUpload,
} from "./api-client";

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
  UpdateEdgeDTO,
  UpdateNodeDTO,
  UserDTO,
  UserUpdateDTO,
} from "@/types/dto";

// ─────────────────────────────────────────────────────────────────────────────
// AUTH
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Called by NextAuth credentials provider to validate email/password.
 * Returns the user object + access_token to be stored in the session.
 */
export async function loginUser(
  email: string,
  password: string
): Promise<AuthResponseDTO> {
  return apiPost<AuthResponseDTO>("/auth/login", { email, password });
}

/**
 * Register a new user account.
 */
export async function registerUser(
  name: string,
  email: string,
  password: string
): Promise<AuthResponseDTO> {
  return apiPost<AuthResponseDTO>("/auth/register", { name, email, password });
}

// ─────────────────────────────────────────────────────────────────────────────
// USER
// ─────────────────────────────────────────────────────────────────────────────

export async function getMe(token: string): Promise<{ user: UserDTO }> {
  return apiGet<{ user: UserDTO }>("/users/me", { token });
}

export async function updateMe(
  token: string,
  data: UserUpdateDTO
): Promise<{ user: UserDTO }> {
  return apiPatch<{ user: UserDTO }>("/users/me", data, { token });
}

// ─────────────────────────────────────────────────────────────────────────────
// BOOKS
// ─────────────────────────────────────────────────────────────────────────────

export async function listBooks(
  token: string
): Promise<{ books: BookSummaryDTO[] }> {
  return apiGet<{ books: BookSummaryDTO[] }>("/books", { token });
}

export async function createBook(
  token: string,
  data: CreateBookDTO
): Promise<{ book: BookDetailDTO }> {
  return apiPost<{ book: BookDetailDTO }>("/books", data, { token });
}

export async function getBook(
  token: string,
  bookId: string
): Promise<{ book: BookDetailDTO }> {
  return apiGet<{ book: BookDetailDTO }>(`/books/${bookId}`, { token });
}

export async function updateBook(
  token: string,
  bookId: string,
  data: Partial<CreateBookDTO>
): Promise<{ book: BookDetailDTO }> {
  return apiPatch<{ book: BookDetailDTO }>(`/books/${bookId}`, data, { token });
}

/**
 * Upload the book file for processing (PDF / EPUB / TXT).
 * Backend parses, extracts concepts, infers edges — all async.
 * Returns immediately with jobId.
 */
export async function uploadBookFile(
  token: string,
  bookId: string,
  file: File
): Promise<{ jobId: string; status: "queued" }> {
  return apiUpload<{ jobId: string; status: "queued" }>(
    `/books/${bookId}/upload`,
    file,
    undefined,
    { token }
  );
}

/**
 * Poll this endpoint every 3 seconds from the processing page.
 */
export async function getBookStatus(
  token: string,
  bookId: string
): Promise<BookStatusDTO> {
  return apiGet<BookStatusDTO>(`/books/${bookId}/status`, { token });
}

// ─────────────────────────────────────────────────────────────────────────────
// KNOWLEDGE GRAPH
// ─────────────────────────────────────────────────────────────────────────────

export async function getGraph(
  token: string,
  bookId: string
): Promise<GraphDTO> {
  return apiGet<GraphDTO>(`/books/${bookId}/graph`, { token });
}

/**
 * User has reviewed and approved the graph. Sets book.status = "ready"
 * and initializes all UserNodeState rows as "locked".
 */
export async function confirmGraph(
  token: string,
  bookId: string
): Promise<{ success: true }> {
  return apiPost<{ success: true }>(`/books/${bookId}/graph/confirm`, {}, { token });
}

// Graph node mutations (verify page editor)

export async function createGraphNode(
  token: string,
  bookId: string,
  data: CreateNodeDTO
): Promise<{ node: KGNodeDTO }> {
  return apiPost<{ node: KGNodeDTO }>(
    `/books/${bookId}/graph/nodes`,
    data,
    { token }
  );
}

export async function updateGraphNode(
  token: string,
  bookId: string,
  nodeId: string,
  data: UpdateNodeDTO
): Promise<{ node: KGNodeDTO }> {
  return apiPatch<{ node: KGNodeDTO }>(
    `/books/${bookId}/graph/nodes/${nodeId}`,
    data,
    { token }
  );
}

export async function deleteGraphNode(
  token: string,
  bookId: string,
  nodeId: string
): Promise<{ success: true }> {
  return apiDelete<{ success: true }>(
    `/books/${bookId}/graph/nodes/${nodeId}`,
    { token }
  );
}

// Graph edge mutations

export async function createGraphEdge(
  token: string,
  bookId: string,
  data: CreateEdgeDTO
): Promise<{ edge: KGEdgeDTO }> {
  return apiPost<{ edge: KGEdgeDTO }>(
    `/books/${bookId}/graph/edges`,
    data,
    { token }
  );
}

export async function updateGraphEdge(
  token: string,
  bookId: string,
  edgeId: string,
  data: UpdateEdgeDTO
): Promise<{ edge: KGEdgeDTO }> {
  return apiPatch<{ edge: KGEdgeDTO }>(
    `/books/${bookId}/graph/edges/${edgeId}`,
    data,
    { token }
  );
}

export async function deleteGraphEdge(
  token: string,
  bookId: string,
  edgeId: string
): Promise<{ success: true }> {
  return apiDelete<{ success: true }>(
    `/books/${bookId}/graph/edges/${edgeId}`,
    { token }
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DAILY PLAN
// ─────────────────────────────────────────────────────────────────────────────

export async function getDailyPlan(
  token: string,
  bookId: string
): Promise<DailyPlanDTO> {
  return apiGet<DailyPlanDTO>(`/books/${bookId}/daily-plan`, { token });
}

// ─────────────────────────────────────────────────────────────────────────────
// ASSESSMENT
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Start the assessment for a book. Returns the first question.
 */
export async function startAssessment(
  token: string,
  bookId: string
): Promise<AssessmentNextResponseDTO> {
  return apiPost<AssessmentNextResponseDTO>(
    "/assessment/start",
    { bookId },
    { token }
  );
}

/**
 * Submit an answer. Returns whether it was correct + next state.
 * The question generator + grader live entirely on the backend.
 */
export async function submitAssessmentAnswer(
  token: string,
  data: AssessmentAnswerRequestDTO
): Promise<AssessmentAnswerResponseDTO> {
  return apiPost<AssessmentAnswerResponseDTO>(
    "/assessment/answer",
    data,
    { token }
  );
}

/**
 * Get the next question after answering. Backend manages topological walk.
 */
export async function getNextAssessmentQuestion(
  token: string,
  bookId: string
): Promise<AssessmentNextResponseDTO> {
  return apiPost<AssessmentNextResponseDTO>(
    "/assessment/next",
    { bookId },
    { token }
  );
}

/**
 * Finalize assessment — initializes all remaining UserNodeState rows.
 * Returns the placement summary shown on results screen.
 */
export async function completeAssessment(
  token: string,
  bookId: string
): Promise<AssessmentCompleteResponseDTO> {
  return apiPost<AssessmentCompleteResponseDTO>(
    "/assessment/complete",
    { bookId },
    { token }
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SESSIONS (Socratic tutor)
// ─────────────────────────────────────────────────────────────────────────────

export async function createSession(
  token: string,
  data: CreateSessionDTO
): Promise<{ session: SessionDTO }> {
  return apiPost<{ session: SessionDTO }>("/sessions", data, { token });
}

export async function sendMessage(
  token: string,
  sessionId: string,
  data: SendMessageRequestDTO
): Promise<SendMessageResponseDTO> {
  return apiPost<SendMessageResponseDTO>(
    `/sessions/${sessionId}/message`,
    data,
    { token }
  );
}

export async function completeSession(
  token: string,
  sessionId: string
): Promise<CompleteSessionResponseDTO> {
  return apiPost<CompleteSessionResponseDTO>(
    `/sessions/${sessionId}/complete`,
    {},
    { token }
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// REVISION
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Returns the due + upcoming card queue with questions pre-loaded.
 * Replaces the N+1 pattern of fetching per-node inside the session.
 */
export async function getRevisionQueue(
  token: string,
  bookId: string
): Promise<RevisionQueueDTO> {
  return apiGet<RevisionQueueDTO>(
    `/books/${bookId}/revision-queue`,
    { token }
  );
}

/**
 * Submit a FSRS grade for a node after reviewing it.
 */
export async function reviewNode(
  token: string,
  nodeId: string,
  data: ReviewRequestDTO
): Promise<ReviewResponseDTO> {
  return apiPost<ReviewResponseDTO>(
    `/nodes/${nodeId}/review`,
    data,
    { token }
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PROGRESS
// ─────────────────────────────────────────────────────────────────────────────

export async function getProgress(
  token: string
): Promise<ProgressDTO> {
  return apiGet<ProgressDTO>("/progress", { token });
}

// ─────────────────────────────────────────────────────────────────────────────
// NOTIFICATIONS
// ─────────────────────────────────────────────────────────────────────────────

export async function listNotifications(
  token: string
): Promise<{ notifications: NotificationDTO[] }> {
  return apiGet<{ notifications: NotificationDTO[] }>(
    "/notifications",
    { token }
  );
}

export async function markNotificationRead(
  token: string,
  notificationId: string
): Promise<{ notification: NotificationDTO }> {
  return apiPost<{ notification: NotificationDTO }>(
    `/notifications/${notificationId}/read`,
    {},
    { token }
  );
}

export async function markAllNotificationsRead(
  token: string
): Promise<{ success: true }> {
  return apiPost<{ success: true }>(
    "/notifications/read-all",
    {},
    { token }
  );
}
