import type {
  TimelinePage,
  CategoryNode,
  MessageDetail,
  ActivityEvent,
  SubmitMessageInput,
  ApiError,
  TimelineParams,
  DeleteImpact,
} from "@/api/types";

const BASE = "/api";

class ApiClientError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "ApiClientError";
  }
}

function isApiError(body: unknown): body is { error: ApiError } {
  return (
    body !== null &&
    typeof body === "object" &&
    "error" in body &&
    body.error !== null &&
    typeof body.error === "object" &&
    "code" in body.error &&
    "message" in body.error
  );
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      throw new ApiClientError("unexpected_response", "Unexpected response");
    }
    if (isApiError(body)) {
      throw new ApiClientError(body.error.code, body.error.message);
    }
    throw new ApiClientError("unexpected_response", "Unexpected response");
  }
  if (res.status === 204) {
    return undefined as T;
  }
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiClientError("unexpected_response", "Malformed response");
  }
}

export function buildSubmissionInput(text: string): SubmitMessageInput {
  return {
    submission_uuid: crypto.randomUUID(),
    text,
    submitted_at: new Date().toISOString(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
}

export const api = {
  async submitMessage(input: SubmitMessageInput): Promise<MessageDetail> {
    return request<MessageDetail>(`${BASE}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  },

  async getTimeline(params?: TimelineParams): Promise<TimelinePage> {
    const searchParams = new URLSearchParams();
    if (params?.page !== undefined) searchParams.set("page", String(params.page));
    if (params?.page_size !== undefined) searchParams.set("page_size", String(params.page_size));
    if (params?.category_id) searchParams.set("category_id", params.category_id);
    if (params?.status) searchParams.set("status", params.status);
    const qs = searchParams.toString();
    return request<TimelinePage>(`${BASE}/timeline${qs ? `?${qs}` : ""}`);
  },

  async getCategories(): Promise<CategoryNode[]> {
    return request<CategoryNode[]>(`${BASE}/categories`);
  },

  async undoMessage(id: string): Promise<void> {
    await request<void>(`${BASE}/messages/${id}/undo`, { method: "POST" });
  },

  async updateEvent(id: string, patch: Record<string, unknown>): Promise<ActivityEvent> {
    return request<ActivityEvent>(`${BASE}/events/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
  },

  async deleteEvent(id: string): Promise<void> {
    return request<void>(`${BASE}/events/${id}`, { method: "DELETE" });
  },

  async reclassifyEvent(id: string): Promise<ActivityEvent> {
    return request<ActivityEvent>(`${BASE}/events/${id}/reclassify`, { method: "POST" });
  },

  async retryMessage(id: string): Promise<{ status: string }> {
    return request<{ status: string }>(`${BASE}/messages/${id}/retry`, { method: "POST" });
  },

  async deleteMessage(id: string): Promise<void> {
    return request<void>(`${BASE}/messages/${id}`, { method: "DELETE" });
  },

  async createCategory(data: { name: string; parent_id?: string }): Promise<CategoryNode> {
    return request<CategoryNode>(`${BASE}/categories`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },

  async renameCategory(id: string, data: { name: string }): Promise<CategoryNode> {
    return request<CategoryNode>(`${BASE}/categories/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },

  async mergeCategories(data: { source_id: string; target_id: string }): Promise<void> {
    return request<void>(`${BASE}/categories/merge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },

  async getDeleteImpact(id: string): Promise<DeleteImpact> {
    return request<DeleteImpact>(`${BASE}/categories/${id}/impact`);
  },

  async deleteCategory(id: string): Promise<void> {
    return request<void>(`${BASE}/categories/${id}`, { method: "DELETE" });
  },

  async health(): Promise<{ status: string }> {
    return request<{ status: string }>(`${BASE}/health`);
  },
};
