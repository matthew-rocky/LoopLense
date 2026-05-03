import type { AnyRow, ChatResponse, LoopDetail, MemoResponse, NetworkGraph, Summary } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    throw new Error(`LoopLens API ${response.status}: ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

export function getSummary() {
  return request<Summary>("/summary");
}

export function getLoops(params?: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return request<AnyRow[]>(`/loops${query.size ? `?${query}` : ""}`);
}

export function getLoop(id: string) {
  return request<LoopDetail>(`/loops/${encodeURIComponent(id)}`);
}

export function getNetwork(id: string) {
  return request<NetworkGraph>(`/loops/${encodeURIComponent(id)}/network`);
}

export function postChat(message: string, selected_loop_id?: string) {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ message, selected_loop_id })
  });
}

export function postMemo(loop_id: string) {
  return request<MemoResponse>("/memo", {
    method: "POST",
    body: JSON.stringify({ loop_id })
  });
}

export function postVerify(loop_id: string, memo: string | Record<string, unknown>) {
  return request<{ final_status: string; verification: AnyRow; warnings: string[] }>("/verify", {
    method: "POST",
    body: JSON.stringify({ loop_id, memo })
  });
}

