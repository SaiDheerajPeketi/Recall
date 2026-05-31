import { expect, test } from "@playwright/test";

const analysis = {
  analysis_id: "11111111-1111-4111-8111-111111111111",
  category: "Vector search",
  summary: "The evidence supports comparing approximate results with an exact baseline.",
  steps: [
    {
      title: "Verify the query",
      instruction: "Compare the filtered approximate query with an exact query on the same data snapshot.",
      citations: ["pgvector-filtering:000"],
    },
  ],
  evidence: [
    {
      chunk_id: "pgvector-filtering:000",
      source_id: "pgvector-filtering",
      title: "pgvector filtering",
      heading: "Approximate indexes and filters",
      url: "https://github.com/pgvector/pgvector#filtering",
      excerpt: "Filtering is applied after an approximate index scan.",
      relevance: 0.97,
      dense_score: 0.82,
      sparse_score: 7.1,
    },
  ],
  confidence: {
    evidence_strength: 0.84,
    relevance: 0.97,
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
  latency_ms: 173,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/health", (route) =>
    route.fulfill({ json: { status: "ready", checks: { provider: "ready" } } }),
  );
  await page.route("**/api/v1/demo-tickets", (route) =>
    route.fulfill({
      json: [
        {
          id: "DB-10469",
          subject: "Vector query returns fewer rows after filtering",
          description: "An HNSW query with a category filter returns fewer rows than requested.",
          product_area: "pgvector search",
          expected_action: "draft",
        },
      ],
    }),
  );
  await page.route("**/api/v1/tickets/analyze", (route) => route.fulfill({ json: analysis }));
});

test("New case submits the analysis flow and renders cited evidence", async ({ page }, testInfo) => {
  await page.goto("/");

  if (testInfo.project.name.startsWith("mobile")) {
    await page.getByRole("button", { name: "Open incident queue" }).click();
  }
  await page.getByRole("button", { name: "New case" }).click();
  await page.getByLabel("Subject").fill("Filtered vector query returns too few rows");
  await page.getByLabel("Product area").fill("pgvector search");
  await page
    .getByLabel("Description")
    .fill("An HNSW cosine query with a category filter returns six rows when twenty are requested.");
  await page.getByRole("button", { name: "Analyze case" }).click();

  await expect(page.getByRole("heading", { name: "Cited resolution ready" })).toBeVisible();
  await expect(page.getByText("pgvector-filtering:000", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence and proposed actions" })).toBeVisible();
});
