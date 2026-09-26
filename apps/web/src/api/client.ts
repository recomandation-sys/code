/**
 * Centralized fetch wrapper (section 64). Owns the API base URL, standard
 * JSON handling, and error normalization — components/hooks never call
 * `fetch()` directly.
 */
import type { ApiError } from "@job-recommender/contracts";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/api/v1";

export class ApiClientError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: unknown[];

  constructor(status: number, error: ApiError) {
    super(error.message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = error.code;
    this.details = error.details ?? [];
  }
}

async function parseJsonSafely(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  const body = await parseJsonSafely(response);

  if (!response.ok) {
    const errorBody = (body as { error?: ApiError } | null)?.error;
    throw new ApiClientError(
      response.status,
      errorBody ?? { code: "UNKNOWN_ERROR", message: "Something went wrong. Please try again." },
    );
  }

  return (body as { data: T }).data;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  formData?: FormData;
  signal?: AbortSignal;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, signal } = options;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    signal,
    headers: formData ? undefined : { "Content-Type": "application/json" },
    body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
  });

  return handleResponse<T>(response);
}
