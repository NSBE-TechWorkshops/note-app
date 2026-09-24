import { useEffect, useState } from "react";
import { userManager } from "../auth";

export function CallbackPage() {
  const [error, setError] = useState("");

  useEffect(() => {
    userManager
      .signinRedirectCallback()
      .then(() => window.location.replace("/"))
      .catch((err) => setError(err instanceof Error ? err.message : "Login failed"));
  }, []);

  return <main className="corg-app"><section className="chat-stage"><p>{error || "Signing you in..."}</p></section></main>;
}
