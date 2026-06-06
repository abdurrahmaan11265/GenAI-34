/**
 * Low-level fetch wrapper for FastAPI.
 *
 * All methods throw ApiError on non-2xx responses so callers can
 * handle them uniformly (e.g. redirect to /login on 401).
 *
 * Usage:
 *   import { apiGet, apiPost } from "@/lib/api-client";
 *   const books = await apiGet<BookSummaryDTO[]>("/books", token);
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
    message?: string
  ) {
    super(message ?? `API error ${status}`);
    this.name = "ApiError";
  }
}

type RequestOptions = {
  token?: string;
  signal?: AbortSignal;
};

async function request<T>(
  method: string,
  path: string,
  body: unknown,
  options: RequestOptions = {}
): Promise<T> {
  const headers: Record<string, string> = {};

  if (options.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: options.signal,
  });

  if (!res.ok) {
    let errorBody: unknown;
    try {
      errorBody = await res.json();
    } catch {
      errorBody = await res.text();
    }
    throw new ApiError(res.status, errorBody);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

export function apiGet<T>(path: string, options?: RequestOptions): Promise<T> {
  return request<T>("GET", path, undefined, options);
}

export function apiPost<T>(
  path: string,
  body: unknown,
  options?: RequestOptions
): Promise<T> {
  return request<T>("POST", path, body, options);
}

export function apiPatch<T>(
  path: string,
  body: unknown,
  options?: RequestOptions
): Promise<T> {
  return request<T>("PATCH", path, body, options);
}

export function apiDelete<T>(
  path: string,
  options?: RequestOptions
): Promise<T> {
  return request<T>("DELETE", path, undefined, options);
}

/**
 * Upload a file using multipart/form-data.
 * Returns the parsed JSON response.
 */
export async function apiUpload<T>(
  path: string,
  file: File,
  extraFields?: Record<string, string>,
  options?: RequestOptions
): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  if (extraFields) {
    for (const [k, v] of Object.entries(extraFields)) {
      form.append(k, v);
    }
  }

  const headers: Record<string, string> = {};
  if (options?.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }
  // Do NOT set Content-Type — browser sets it with boundary

  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers,
    body: form,
    signal: options?.signal,
  });

  if (!res.ok) {
    let errorBody: unknown;
    try {
      errorBody = await res.json();
    } catch {
      errorBody = await res.text();
    }
    throw new ApiError(res.status, errorBody);
  }

  return res.json() as Promise<T>;
}
