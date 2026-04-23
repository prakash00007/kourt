const rawApiBaseUrl =
  process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const normalizedApiBaseUrl = rawApiBaseUrl.replace(/\/$/, "");
const API_BASE_URL = normalizedApiBaseUrl.endsWith("/api") ? normalizedApiBaseUrl : `${normalizedApiBaseUrl}/api`;

type ChatPayload = { query: string };
type DraftPayload = { draft_type: string; details: string };
type AuthPayload = { email: string; password: string };
type SignupPayload = AuthPayload & { tier: string };
type ChatResponse = {
  answer: string;
  citations: Array<{ title: string; citation?: string; court?: string; source_url?: string }>;
  sources: Array<{ title: string; excerpt: string; citation?: string; source_url?: string }>;
  disclaimer: string;
};
type AuthResponse = {
  access_token: string;
  token_type: string;
  user: { id: string; email: string; tier: string; created_at: string };
};
type DraftResponse = {
  title: string;
  draft: string;
  disclaimer: string;
};
type UploadResponse = {
  file_name: string;
  summary: {
    facts: string;
    issues: string;
    judgment: string;
    key_takeaways: string;
  };
  disclaimer: string;
};

function withAuthHeaders(headers: HeadersInit, token?: string) {
  if (!token) {
    return headers;
  }

  return {
    ...headers,
    Authorization: `Bearer ${token}`
  };
}

async function getErrorMessage(response: Response) {
  try {
    const payload = await response.json();
    if (payload?.error?.message) {
      return payload.error.message as string;
    }
    if (typeof payload?.detail === "string") {
      return payload.detail as string;
    }
  } catch {
    // Ignore JSON parse failures and fall back to the generic message.
  }

  return null;
}

async function apiRequest<T>(path: string, init: RequestInit, fallbackMessage: string): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new Error("Unable to reach the backend right now. Please check that the API server is running.");
  }

  if (!response.ok) {
    throw new Error((await getErrorMessage(response)) || fallbackMessage);
  }

  return response.json();
}

export async function sendChat(payload: ChatPayload, token?: string) {
  return apiRequest<ChatResponse>("/chat", {
    method: "POST",
    headers: withAuthHeaders({ "Content-Type": "application/json" }, token),
    body: JSON.stringify(payload)
  }, "Unable to complete legal research right now.");
}

export async function loginUser(payload: AuthPayload) {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }, "Unable to log in right now.");
}

export async function signupUser(payload: SignupPayload) {
  return apiRequest<AuthResponse>("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }, "Unable to sign up right now.");
}

export async function generateDraft(payload: DraftPayload, token?: string) {
  return apiRequest<DraftResponse>("/draft", {
    method: "POST",
    headers: withAuthHeaders({ "Content-Type": "application/json" }, token),
    body: JSON.stringify(payload)
  }, "Unable to generate the draft right now.");
}

export async function uploadJudgment(file: File, token?: string) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<UploadResponse>("/upload", {
    method: "POST",
    headers: withAuthHeaders({}, token),
    body: formData
  }, "Unable to summarize this judgment right now.");
}
