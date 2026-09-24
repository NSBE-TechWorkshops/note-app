import { getAccessToken } from "./auth";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type Me = { email: string; display_name: string | null };

export async function fetchMe(): Promise<Me> {
  const token = await getAccessToken();
  if (!token) throw new Error("Not signed in");
  const response = await fetch(`${apiBaseUrl}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Auth check failed");
  return response.json();
}

export async function updateMe(displayName: string): Promise<Me> {
  const token = await getAccessToken();
  if (!token) throw new Error("Not signed in");
  const response = await fetch(`${apiBaseUrl}/me`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ display_name: displayName }),
  });
  if (!response.ok) throw new Error("Failed to update username");
  return response.json();
}
