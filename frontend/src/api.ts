import { getAccessToken } from "./auth";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function authHeaders() {
  const token = await getAccessToken();
  if (!token) throw new Error("Not signed in");
  return { Authorization: `Bearer ${token}` };
}

export type DocumentSummary = {
  id: string;
  filename: string;
  status: string;
  mime_type: string;
  error_message?: string | null;
};

export async function listDocuments(): Promise<DocumentSummary[]> {
  const response = await fetch(`${apiBaseUrl}/documents`, { headers: await authHeaders() });
  if (!response.ok) throw new Error("Failed to list documents");
  return response.json();
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/documents/upload`, {
    method: "POST",
    headers: await authHeaders(),
    body: form,
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export type AskResponse = {
  id: string;
  question: string;
  answer: string;
  model: string;
  sources: { chunk_id: string; text_preview: string; document_id: string }[];
};

export type ChatSessionSummary = {
  id: string;
  title: string;
  course_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  model?: string | null;
  created_at: string;
};

export type ChatSessionDetail = ChatSessionSummary & {
  messages: ChatMessage[];
};

export type SendChatMessageResponse = {
  session: ChatSessionSummary;
  messages: ChatMessage[];
  sources: { chunk_id: string; text_preview: string; document_id: string }[];
};

export async function listChatSessions(): Promise<ChatSessionSummary[]> {
  const response = await fetch(`${apiBaseUrl}/chat/sessions`, { headers: await authHeaders() });
  if (!response.ok) throw new Error("Failed to list chat sessions");
  return response.json();
}

export async function createChatSession(title: string): Promise<ChatSessionSummary> {
  const response = await fetch(`${apiBaseUrl}/chat/sessions`, {
    method: "POST",
    headers: {
      ...(await authHeaders()),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function getChatSession(sessionId: string): Promise<ChatSessionDetail> {
  const response = await fetch(`${apiBaseUrl}/chat/sessions/${sessionId}`, { headers: await authHeaders() });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function sendChatMessage(sessionId: string | null, content: string, documentIds: string[]): Promise<SendChatMessageResponse> {
  const response = await fetch(sessionId ? `${apiBaseUrl}/chat/sessions/${sessionId}/messages` : `${apiBaseUrl}/chat/messages`, {
    method: "POST",
    headers: {
      ...(await authHeaders()),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content, session_id: sessionId, document_ids: documentIds }),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await fetch(`${apiBaseUrl}/questions/ask`, {
    method: "POST",
    headers: {
      ...(await authHeaders()),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
