import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ThinkingOrb } from "thinking-orbs";
import type { User } from "oidc-client-ts";
import { userManager } from "./auth";
import { getChatSession, listChatSessions, listDocuments, sendChatMessage, uploadDocument } from "./api";
import type { ChatMessage, DocumentSummary } from "./api";
import { fetchMe, updateMe } from "./me";
import collapse from "./assets/corg/conversation-active.svg";
import newChatIcon from "./assets/corg/collapse-sidebar.svg";
import search from "./assets/corg/search.svg";
import { GrowingComposer } from "./components/GrowingComposer";
import { UsernamePrompt } from "./components/UsernamePrompt";
import settings from "./assets/corg/settings.svg";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function fetchHealth(): Promise<{ status: string }> {
  const response = await fetch(`${apiBaseUrl}/health`);
  if (!response.ok) throw new Error("Backend health check failed");
  return response.json();
}

type Turn = { question: string; answer: string };

function messagesToTurns(messages: ChatMessage[]): Turn[] {
  const turns: Turn[] = [];
  let pendingQuestion = "";

  for (const message of messages) {
    if (message.role === "user") {
      pendingQuestion = message.content;
    } else if (message.role === "assistant" && pendingQuestion) {
      turns.push({ question: pendingQuestion, answer: message.content });
      pendingQuestion = "";
    }
  }

  return turns;
}

function DocumentStatus({ status }: { status: string }) {
  if (status === "processing") return <small className="processing-status">Processing<span /></small>;
  if (status === "ready") return <small>Done</small>;
  if (status === "failed") return <small>Failed</small>;
  return <small>{status}</small>;
}

export function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth, retry: false });
  const [user, setUser] = useState<User | null>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const me = useQuery({ queryKey: ["me"], queryFn: fetchMe, enabled: !!user, retry: false });
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    enabled: !!user,
    refetchInterval: (query) => query.state.data?.some((doc) => doc.status === "processing") ? 5000 : false,
    retry: false,
  });
  const chatSessions = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: listChatSessions,
    enabled: !!user,
    retry: false,
  });
  const setUsername = useMutation({
    mutationFn: updateMe,
    onSuccess: (updated) => queryClient.setQueryData(["me"], updated),
  });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeQuestion, setActiveQuestion] = useState("");
  const [selectedDocuments, setSelectedDocuments] = useState<DocumentSummary[]>([]);
  const [documentsModalOpen, setDocumentsModalOpen] = useState(false);
  const [conversationSearch, setConversationSearch] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [thinking, setThinking] = useState(false);
  const conversationEnd = useRef<HTMLDivElement>(null);
  const upload = useMutation({ mutationFn: uploadDocument });
  const ask = useMutation({
    mutationFn: async (question: string) => {
      return sendChatMessage(activeSessionId, question, selectedDocuments.map((doc) => doc.id));
    },
    onSuccess: (response) => {
      setActiveSessionId(response.session.id);
      setTurns((current) => [...current, ...messagesToTurns(response.messages)]);
      queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
    onSettled: () => setThinking(false),
  });
  const openSession = useMutation({
    mutationFn: getChatSession,
    onSuccess: (session) => {
      setActiveSessionId(session.id);
      setTurns(messagesToTurns(session.messages));
      setActiveQuestion("");
      setSelectedDocuments([]);
      setDocumentsModalOpen(false);
      setSidebarOpen(false);
    },
  });

  useEffect(() => {
    userManager.getUser().then(setUser);
  }, []);

  useEffect(() => {
    if (turns.length === 0 && !thinking) return;
    requestAnimationFrame(() => requestAnimationFrame(() => {
      conversationEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" });
    }));
  }, [turns.length, thinking]);

  useEffect(() => {
    if (!documents.data) return;
    setSelectedDocuments((current) => current.map((selected) => documents.data.find((doc) => doc.id === selected.id) ?? selected));
  }, [documents.data]);

  const login = () => userManager.signinRedirect();
  const logout = () => userManager.signoutRedirect();

  const attachFiles = async (files: File[]) => {
    if (!user) return login();
    const uploaded = await Promise.all(files.map((file) => upload.mutateAsync(file)));
    setSelectedDocuments((current) => [...current, ...uploaded.filter((doc) => !current.some((selected) => selected.id === doc.id))]);
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    setDocumentsModalOpen(true);
  };

  const removeSelectedDocument = (documentId: string) => {
    setSelectedDocuments((current) => current.filter((doc) => doc.id !== documentId));
  };

  const submitQuestion = (trimmed: string) => {
    if (thinking || ask.isPending) return;
    if (!user) return login();
    setActiveQuestion(trimmed);
    setThinking(true);
    ask.mutate(trimmed);
  };

  const newChat = () => { setActiveSessionId(null); setTurns([]); setActiveQuestion(""); setSelectedDocuments([]); setDocumentsModalOpen(false); setSidebarOpen(false); };

  const needsUsername = !!user && me.isSuccess && !me.data?.display_name;
  const filteredSessions = (chatSessions.data ?? []).filter((session) =>
    session.title.toLowerCase().includes(conversationSearch.trim().toLowerCase())
  );

  return (
    <main className="corg-app">
      {needsUsername && <UsernamePrompt
        pending={setUsername.isPending}
        error={setUsername.isError ? "Couldn't save your username. Try again." : undefined}
        onSubmit={(username) => setUsername.mutate(username)}
      />}
      {documentsModalOpen && <div className="modal-overlay" onClick={() => setDocumentsModalOpen(false)}>
        <section className="modal documents-modal" aria-label="Selected documents" onClick={(event) => event.stopPropagation()}>
          <div className="documents-modal-header"><h2>Documents</h2><button type="button" onClick={() => setDocumentsModalOpen(false)} aria-label="Close documents">×</button></div>
          <div className="selected-documents">
            {selectedDocuments.map((doc) => <div className="selected-document" key={doc.id}><span>{doc.filename}</span><DocumentStatus status={doc.status} /><button type="button" onClick={() => removeSelectedDocument(doc.id)}>Remove</button></div>)}
            {selectedDocuments.length === 0 && <p>No documents selected for this chat.</p>}
          </div>
          <label className="add-documents-button">{upload.isPending ? "Uploading..." : "Add more documents"}<input type="file" accept=".pdf,.txt" multiple onChange={(event) => attachFiles(Array.from(event.target.files ?? []))} /></label>
        </section>
      </div>}
      {sidebarOpen && <aside className="sidebar" aria-label="Conversation history">
        <div className="sidebar-header"><em>Note Buddy</em><button aria-label="Close sidebar" onClick={() => setSidebarOpen(false)}><img src={collapse} alt="" /></button></div>
        <button className="new-chat" onClick={newChat}><img src={newChatIcon} alt="" />New chat</button>
        <label className="conversation-search"><img src={search} alt="" /><input placeholder="Search conversations" value={conversationSearch} onChange={(event) => setConversationSearch(event.target.value)} /></label>
        <p className="section-label">Conversations</p>
        <div className="history-list">
          {chatSessions.isLoading && <small>Loading conversations...</small>}
          {chatSessions.isError && <small>Couldn't load conversations.</small>}
          {filteredSessions.map((session) => <button
            className={`history-row${session.id === activeSessionId ? " active" : ""}`}
            key={session.id}
            onClick={() => openSession.mutate(session.id)}
            type="button"
          ><span>{session.title}</span></button>)}
          {chatSessions.isSuccess && filteredSessions.length === 0 && <small>No saved conversations yet.</small>}
        </div>
        <footer className="sidebar-footer">
          <div className="workspace-avatar">C</div>
          <div><strong>{me.data?.display_name || me.data?.email || "Local workspace"}</strong><small>{health.status === "success" ? "Ready to retrieve" : "Offline mode"}</small></div>
          <button className="sidebar-settings-button" aria-label="Settings" onClick={() => navigate({ to: "/settings" })}><img src={settings} alt="" /></button>
        </footer>
      </aside>}
      <section className="chat-stage">
        <div className="auth-actions">
          {user ? <button onClick={logout}>Sign out{me.data?.email ? ` (${me.data.email})` : ""}</button> : <button onClick={login}>Sign in</button>}
        </div>
        {!sidebarOpen && <button className="menu-button" aria-label="Open sidebar" onClick={() => setSidebarOpen(true)}><span /><span /><span /></button>}
        {turns.length === 0 && !thinking ? <div className="welcome">
          <h1>Note Buddy</h1>
          <GrowingComposer ariaLabel="Ask about your notes" documentCount={selectedDocuments.length} uploadPending={upload.isPending} onDocumentsClick={() => setDocumentsModalOpen(true)} onFilesSelected={attachFiles} onSubmit={submitQuestion} />
          {ask.isError && <p className="inline-error">{ask.error instanceof Error ? ask.error.message : "Question failed"}</p>}
          {openSession.isError && <p className="inline-error">{openSession.error instanceof Error ? openSession.error.message : "Conversation failed to load"}</p>}
          {upload.isError && <p className="inline-error">{upload.error instanceof Error ? upload.error.message : "Upload failed"}</p>}
          {selectedDocuments.length > 0 && <small className="document-status">{selectedDocuments.length} document{selectedDocuments.length === 1 ? "" : "s"} selected for this chat</small>}
        </div> : <div className="conversation">
          {turns.map((turn, index) => <div className="turn" key={`${turn.question}-${index}`}><p className="question">{turn.question}</p><article className="answer"><ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.answer}</ReactMarkdown>{selectedDocuments.length > 0 && <div className="sources"><span>Sources</span><span>{selectedDocuments.map((doc) => doc.filename).join(", ")}</span></div>}</article></div>)}
          {thinking && <div className="thinking"><p>{activeQuestion || "Searching your notes"}</p><div className="thinking-pill"><ThinkingOrb state="searching" size={32} theme="dark" color="#ffffff" aria-label="Thinking" /></div><small className="retrieving-text">Retrieving relevant passages</small></div>}
          <div ref={conversationEnd} />
          <GrowingComposer className="docked" ariaLabel="Ask another question" documentCount={selectedDocuments.length} uploadPending={upload.isPending} onDocumentsClick={() => setDocumentsModalOpen(true)} onFilesSelected={attachFiles} onSubmit={submitQuestion} />
        </div>}
      </section>
    </main>
  );
}
