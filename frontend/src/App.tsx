import { useQuery } from "@tanstack/react-query";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function fetchHealth(): Promise<{ status: string }> {
  const response = await fetch(`${apiBaseUrl}/health`);

  if (!response.ok) {
    throw new Error("Backend health check failed");
  }

  return response.json();
}

export function App() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    retry: false,
  });

  const status =
    health.status === "success"
      ? `Backend: ${health.data.status}`
      : health.status === "error"
        ? "Backend: unavailable"
        : "Backend: checking";

  return (
    <main className="app-shell">
      <section className="workspace">
        <p className="eyebrow">Student Notes RAG</p>
        <h1>Note Buddy</h1>
        <p className="summary">
          Upload course material, ask grounded questions, and build a study
          companion from your own notes.
        </p>
        <div className="status-row">
          <span className="status-dot" aria-hidden="true" />
          <span>{status}</span>
        </div>
      </section>
    </main>
  );
}
