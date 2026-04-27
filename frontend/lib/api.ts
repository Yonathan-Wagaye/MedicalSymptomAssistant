const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ──

export type Source = {
  id: string;
  title: string;
  snippet: string;
};

export type RelatedTopic = {
  name: string;
  matched_symptoms: string[];
  confidence: string;
  reason: string | null;
};

export type QueryResponse = {
  session_id: string;
  answer: string;
  urgency: "emergency" | "normal" | "clarification_needed";
  follow_up_questions: string[];
  related_topics: RelatedTopic[];
  sources: Source[];
  disclaimer: string;
};

export type Session = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type MessageRecord = {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type SessionDetail = Session & {
  messages: MessageRecord[];
};

// ── API calls ──

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Server error (${res.status})`);
  }
  return res.json();
}

export function createSession(title?: string) {
  return request<Session>("/sessions", {
    method: "POST",
    body: JSON.stringify({ title: title ?? null }),
  });
}

export function getSession(id: string) {
  return request<SessionDetail>(`/sessions/${id}`);
}

export function submitQuery(sessionId: string, query: string) {
  return request<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, query }),
  });
}
