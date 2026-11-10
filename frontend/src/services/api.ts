import type { PlanInput, PlanResponse, Place } from "../types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error ?? `Request failed (${res.status})`);
  return body as T;
}

export const searchPlaces = async (query: string, signal?: AbortSignal): Promise<Place[]> => {
  const data = await request<{ results: Place[] }>(`/api/geocode?q=${encodeURIComponent(query)}`, { signal });
  return data.results;
};

export const planRoutes = (input: PlanInput, signal?: AbortSignal): Promise<PlanResponse> =>
  request<PlanResponse>("/api/plan", { method: "POST", body: JSON.stringify(input), signal });
