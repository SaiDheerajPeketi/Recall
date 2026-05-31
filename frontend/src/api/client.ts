import type { components } from "./schema";

export type DemoTicket = components["schemas"]["DemoTicket"];
export type TicketAnalyzeRequest = components["schemas"]["TicketAnalyzeRequest"];
export type TicketAnalysisResponse = components["schemas"]["TicketAnalysisResponse"];
export type FeedbackRequest = components["schemas"]["FeedbackRequest"];

export interface HealthResponse {
  status: "ready" | "degraded";
  checks: Record<string, string>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export function getDemoTickets(): Promise<DemoTicket[]> {
  return request<DemoTicket[]>("/api/v1/demo-tickets");
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health");
}

export function analyzeTicket(
  payload: TicketAnalyzeRequest,
  signal?: AbortSignal,
): Promise<TicketAnalysisResponse> {
  return request<TicketAnalysisResponse>("/api/v1/tickets/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function submitFeedback(payload: FeedbackRequest): Promise<{ status: "recorded" }> {
  return request<{ status: "recorded" }>("/api/v1/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
