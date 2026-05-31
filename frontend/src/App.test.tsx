import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const demoTickets = [
  {
    id: "DB-10468",
    subject: "Disk space is growing rapidly",
    description: "The database volume is growing and the source is not yet known.",
    product_area: "PostgreSQL maintenance",
    expected_action: "draft",
  },
  {
    id: "DB-10469",
    subject: "Vector query returns fewer rows",
    description: "A filtered HNSW query returns fewer rows than the requested limit.",
    product_area: "pgvector search",
    expected_action: "draft",
  },
];

const analysis = {
  analysis_id: "11111111-1111-4111-8111-111111111111",
  category: "Storage and maintenance",
  summary: "The evidence supports a measured storage investigation.",
  steps: [
    {
      title: "Measure growth",
      instruction: "Compare table, index, WAL, temporary-file, and log growth.",
      citations: ["postgresql-vacuum:001"],
    },
  ],
  evidence: [
    {
      chunk_id: "postgresql-vacuum:001",
      source_id: "postgresql-vacuum",
      title: "PostgreSQL: Routine Vacuuming",
      heading: "Safe response to rapid disk growth",
      url: "https://www.postgresql.org/docs/current/routine-vacuuming.html",
      excerpt: "Measure object growth before scheduling disruptive maintenance.",
      relevance: 0.99,
      dense_score: 0.8,
      sparse_score: 8,
    },
  ],
  confidence: {
    evidence_strength: 0.86,
    relevance: 0.99,
    source_diversity: 0.33,
    retrieval_agreement: 1,
    citation_coverage: 1,
    label: "strong",
    threshold: 0.55,
  },
  action: "draft",
  escalation_rationale: [],
  missing_signals: [],
  corpus_version: "recall-test",
  provider: "mock",
  provider_model: "deterministic-rules-v1",
  latency_ms: 112,
};

function response(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installFetchMock() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/demo-tickets")) return response(demoTickets);
      if (url.endsWith("/api/v1/health")) {
        return response({ status: "ready", checks: { provider: "ready" } });
      }
      if (url.endsWith("/api/v1/tickets/analyze")) return response(analysis);
      if (url.endsWith("/api/v1/feedback")) return response({ status: "recorded" }, 201);
      return response({}, 404);
    }),
  );
}

describe("Recall workbench", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("opens a blank New case composer", async () => {
    installFetchMock();
    render(<App />);

    await screen.findAllByText("DB-10468");
    fireEvent.change(screen.getByPlaceholderText("Search demo cases"), {
      target: { value: "Vector query" },
    });
    expect(screen.getByRole("button", { name: /Vector query returns fewer rows/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Disk space is growing rapidly/ })).not.toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Search demo cases"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Close queue" }));
    expect(screen.getByRole("button", { name: "Open incident queue" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    fireEvent.click(screen.getByRole("button", { name: "Open incident queue" }));
    fireEvent.click(screen.getByRole("button", { name: "New case" }));

    expect(screen.getByRole("heading", { name: "New case" })).toBeInTheDocument();
    expect(screen.getByLabelText("Subject")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Analyze case" })).toBeDisabled();
  });

  it("submits New case through analysis and renders cited evidence", async () => {
    installFetchMock();
    render(<App />);

    await screen.findAllByText("DB-10468");
    fireEvent.click(screen.getByRole("button", { name: "New case" }));
    fireEvent.change(screen.getByLabelText("Subject"), {
      target: { value: "Disk usage is rising" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "The database volume grew by 38 GB in two days." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Analyze case" }));

    await waitFor(() => {
      expect(screen.getByText("Cited resolution ready")).toBeInTheDocument();
    });
    expect(screen.getAllByText("postgresql-vacuum:001").length).toBeGreaterThan(0);
    expect(screen.getByText("mock · deterministic-rules-v1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Use draft" }));
    await waitFor(() => expect(screen.getByText("Feedback recorded")).toBeInTheDocument());
    const feedbackCall = vi.mocked(fetch).mock.calls.find(([input]) =>
      String(input).endsWith("/api/v1/feedback"),
    );
    expect(JSON.parse(String(feedbackCall?.[1]?.body))).toMatchObject({
      accepted: true,
      minutes_saved: null,
    });
  });

  it("discards an analysis that finishes after the active case changes", async () => {
    let releaseAnalysis: ((value: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/demo-tickets")) return response(demoTickets);
        if (url.endsWith("/api/v1/health")) {
          return response({ status: "ready", checks: { provider: "ready" } });
        }
        if (url.endsWith("/api/v1/tickets/analyze")) {
          return await new Promise<Response>((resolve) => {
            releaseAnalysis = resolve;
          });
        }
        return response({}, 404);
      }),
    );
    render(<App />);

    await screen.findAllByText("DB-10468");
    fireEvent.click(screen.getByRole("button", { name: "Analyze case" }));
    await screen.findByText("Analyzing case");
    fireEvent.click(screen.getByRole("button", { name: "New case" }));
    releaseAnalysis?.(response(analysis));

    await waitFor(() => expect(screen.getByRole("heading", { name: "New case" })).toBeInTheDocument());
    expect(screen.queryByText("Cited resolution ready")).not.toBeInTheDocument();
  });

  it("discards feedback completion after the active case changes", async () => {
    let releaseFeedback: ((value: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/demo-tickets")) return response(demoTickets);
        if (url.endsWith("/api/v1/health")) {
          return response({ status: "ready", checks: { provider: "ready" } });
        }
        if (url.endsWith("/api/v1/tickets/analyze")) return response(analysis);
        if (url.endsWith("/api/v1/feedback")) {
          return await new Promise<Response>((resolve) => {
            releaseFeedback = resolve;
          });
        }
        return response({}, 404);
      }),
    );
    render(<App />);

    await screen.findAllByText("DB-10468");
    fireEvent.click(screen.getByRole("button", { name: "Analyze case" }));
    await screen.findByText("Cited resolution ready");
    fireEvent.click(screen.getByRole("button", { name: "Use draft" }));
    fireEvent.click(screen.getByRole("button", { name: "New case" }));
    releaseFeedback?.(response({ status: "recorded" }, 201));

    await waitFor(() => expect(screen.getByRole("heading", { name: "New case" })).toBeInTheDocument());
    expect(screen.queryByText("Feedback recorded")).not.toBeInTheDocument();
  });

  it("has no automated accessibility violations in the default workbench", async () => {
    installFetchMock();
    const { container } = render(<App />);

    await screen.findAllByText("DB-10468");
    const result = await axe.run(container, {
      rules: {
        "color-contrast": { enabled: false },
        region: { enabled: false },
      },
    });

    expect(result.violations).toEqual([]);
  });
});
