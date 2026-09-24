import { FormEvent, useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchMe, updateMe } from "../me";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: fetchMe, retry: false });
  const [username, setUsername] = useState("");

  useEffect(() => {
    setUsername(me.data?.display_name ?? "");
  }, [me.data?.display_name]);

  const mutation = useMutation({
    mutationFn: updateMe,
    onSuccess: (updated) => queryClient.setQueryData(["me"], updated),
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = username.trim();
    if (!trimmed) return;
    mutation.mutate(trimmed);
  };

  return <main className="corg-app">
    <section className="chat-stage settings-page">
      <div className="settings-panel">
        <Link to="/" className="settings-back">Back</Link>
        <h1>Settings</h1>
        <form onSubmit={submit} className="settings-form">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Username"
            maxLength={50}
          />
          <button type="submit" disabled={mutation.isPending || !username.trim()}>
            {mutation.isPending ? "Saving..." : "Save changes"}
          </button>
          {mutation.isSuccess && <small className="settings-status">Saved.</small>}
          {mutation.isError && <small className="settings-status settings-error">Couldn't save your username. Try again.</small>}
        </form>
      </div>
    </section>
  </main>;
}
