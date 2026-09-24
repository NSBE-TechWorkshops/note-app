import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import collapse from "./assets/corg/conversation-active.svg";
import newChatIcon from "./assets/corg/collapse-sidebar.svg";
import paperclip from "./assets/corg/paperclip.svg";
import search from "./assets/corg/search.svg";
import { GrowingComposer } from "./components/GrowingComposer";
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeQuestion, setActiveQuestion] = useState("");
  const [documentName, setDocumentName] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [thinking, setThinking] = useState(false);

  const submitQuestion = (trimmed: string) => {
    if (thinking) return;
    setActiveQuestion(trimmed);
    setThinking(true);
    window.setTimeout(() => {
      setTurns((current) => [...current, {
        question: trimmed,
        answer: documentName
          ? `Based on ${documentName}, here is a grounded starting point: the relevant passages support this answer. Connect the claim to the specific example in your notes, then use the source chip below to review the evidence.`
          : "Upload course material first, then I can ground this answer in the passages from your notes.",
      }]);
      setThinking(false);
    }, 650);
  };

  const newChat = () => { setTurns([]); setActiveQuestion(""); setSidebarOpen(false); };

  return (
    <main className="corg-app">
      {sidebarOpen && <aside className="sidebar" aria-label="Conversation history">
        <div className="sidebar-header"><em>Corg</em><button aria-label="Close sidebar" onClick={() => setSidebarOpen(false)}><img src={collapse} alt="" /></button></div>
        <button className="new-chat" onClick={newChat}><img src={newChatIcon} alt="" />New chat</button>
        <label className="conversation-search"><img src={search} alt="" /><input placeholder="Search conversations" /></label>
        <footer className="sidebar-footer"><div className="workspace-avatar">C</div><div><strong>Local workspace</strong><small>{health.status === "success" ? "Ready to retrieve" : "Offline mode"}</small></div><img src={settings} alt="Settings" /></footer>
      </aside>}
      <section className="chat-stage">
        {!sidebarOpen && <button className="menu-button" aria-label="Open sidebar" onClick={() => setSidebarOpen(true)}><span /><span /><span /></button>}
        {turns.length === 0 && !thinking ? <div className="welcome">
          <h1>Corg</h1>
          <GrowingComposer ariaLabel="Ask about your notes" onSubmit={submitQuestion} />
          <label className="document-upload"><img src={paperclip} alt="" /><span>{documentName || "Add a document"}</span><input type="file" accept=".pdf,.doc,.docx,.txt,.md" onChange={(event) => setDocumentName(event.target.files?.[0]?.name ?? "")} /></label>
        </div> : <div className="conversation">
          {turns.map((turn, index) => <div className="turn" key={`${turn.question}-${index}`}><p className="question">{turn.question}</p><article className="answer"><p>{turn.answer}</p>{documentName && <div className="sources"><span>Source</span><span>{documentName}</span></div>}</article></div>)}
          {thinking && <div className="thinking"><p>{activeQuestion || "Searching your notes"}</p><div className="thinking-pill"><img src={spinner} alt="" /></div><small>Retrieving relevant passages</small></div>}
          <GrowingComposer className="docked" ariaLabel="Ask another question" onSubmit={submitQuestion} />
        </div>}
      </section>
    </main>
  );
}
