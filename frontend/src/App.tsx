import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import type { User } from "oidc-client-ts";
import { userManager } from "./auth";
import { askQuestion, listDocuments, uploadDocument } from "./api";
import { fetchMe, updateMe } from "./me";
import collapse from "./assets/corg/conversation-active.svg";
import newChatIcon from "./assets/corg/collapse-sidebar.svg";
import paperclip from "./assets/corg/paperclip.svg";
import search from "./assets/corg/search.svg";
import { GrowingComposer } from "./components/GrowingComposer";
import { UsernamePrompt } from "./components/UsernamePrompt";
import settings from "./assets/corg/settings.svg";
import spinner from "./assets/corg/spinner.svg";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function fetchHealth(): Promise<{ status: string }> {
  const response = await fetch(`${apiBaseUrl}/health`);
  if (!response.ok) throw new Error("Backend health check failed");
  return response.json();
}

type Turn = { question: string; answer: string };

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
  const setUsername = useMutation({
    mutationFn: updateMe,
    onSuccess: (updated) => queryClient.setQueryData(["me"], updated),
  });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeQuestion, setActiveQuestion] = useState("");
  const [documentName, setDocumentName] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [thinking, setThinking] = useState(false);
  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: (doc) => {
      setDocumentName(doc.filename);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
  const ask = useMutation({
    mutationFn: askQuestion,
    onSuccess: (response) => {
      setTurns((current) => [...current, { question: response.question, answer: response.answer }]);
    },
    onSettled: () => setThinking(false),
  });

  useEffect(() => {
    userManager.getUser().then(setUser);
  }, []);

  const login = () => userManager.signinRedirect();
  const logout = () => userManager.signoutRedirect();

  const submitQuestion = (trimmed: string) => {
    if (thinking || ask.isPending) return;
    if (!user) return login();
    setActiveQuestion(trimmed);
    setThinking(true);
    ask.mutate(trimmed);
  };

  const newChat = () => { setTurns([]); setActiveQuestion(""); setSidebarOpen(false); };

  const needsUsername = !!user && me.isSuccess && !me.data?.display_name;

  return (
    <main className="corg-app">
      {needsUsername && <UsernamePrompt
        pending={setUsername.isPending}
        error={setUsername.isError ? "Couldn't save your username. Try again." : undefined}
        onSubmit={(username) => setUsername.mutate(username)}
      />}
      {sidebarOpen && <aside className="sidebar" aria-label="Conversation history">
        <div className="sidebar-header"><em>Corg</em><button aria-label="Close sidebar" onClick={() => setSidebarOpen(false)}><img src={collapse} alt="" /></button></div>
        <button className="new-chat" onClick={newChat}><img src={newChatIcon} alt="" />New chat</button>
        <label className="conversation-search"><img src={search} alt="" /><input placeholder="Search conversations" /></label>
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
          <h1>Corg</h1>
          <GrowingComposer ariaLabel="Ask about your notes" onSubmit={submitQuestion} />
          {ask.isError && <p className="inline-error">{ask.error instanceof Error ? ask.error.message : "Question failed"}</p>}
          <label className="document-upload"><img src={paperclip} alt="" /><span>{upload.isPending ? "Uploading..." : documentName || documents.data?.[0]?.filename || "Add a document"}</span><input type="file" accept=".pdf,.txt" onChange={(event) => { const file = event.target.files?.[0]; if (file) upload.mutate(file); }} /></label>
          {upload.isError && <p className="inline-error">{upload.error instanceof Error ? upload.error.message : "Upload failed"}</p>}
          {documents.data?.[0] && <small className="document-status">Latest document: {documents.data[0].status}</small>}
        </div> : <div className="conversation">
          {turns.map((turn, index) => <div className="turn" key={`${turn.question}-${index}`}><p className="question">{turn.question}</p><article className="answer"><p>{turn.answer}</p>{documentName && <div className="sources"><span>Source</span><span>{documentName}</span></div>}</article></div>)}
          {thinking && <div className="thinking"><p>{activeQuestion || "Searching your notes"}</p><div className="thinking-pill"><img src={spinner} alt="" /></div><small>Retrieving relevant passages</small></div>}
          <GrowingComposer className="docked" ariaLabel="Ask another question" onSubmit={submitQuestion} />
        </div>}
      </section>
    </main>
  );
}
