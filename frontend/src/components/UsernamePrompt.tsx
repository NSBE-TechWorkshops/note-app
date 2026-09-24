import { FormEvent, useState } from "react";

type UsernamePromptProps = {
  onSubmit: (username: string) => void;
  pending?: boolean;
  error?: string;
};

export function UsernamePrompt({ onSubmit, pending, error }: UsernamePromptProps) {
  const [value, setValue] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const username = value.trim();
    if (!username) return;
    onSubmit(username);
  };

  return <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="username-prompt-title">
    <form className="modal username-prompt" onSubmit={submit}>
      <h2 id="username-prompt-title">Choose a username</h2>
      <p>Pick a name to show in your sidebar instead of your email.</p>
      <input
        autoFocus
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Username"
        maxLength={50}
        aria-label="Username"
      />
      {error && <small className="modal-error">{error}</small>}
      <button type="submit" disabled={pending || !value.trim()}>{pending ? "Saving..." : "Continue"}</button>
    </form>
  </div>;
}
