# Decision log

This log records decisions in the order they were made. Each entry explains the context, alternatives, choice, consequences, evidence, and the condition that would justify revisiting it.

## 2026-09-16 — Start with one reproducible local stack

- **Context:** Recall needs four cooperating services and must be usable by another developer without reconstructing the environment.
- **Alternatives:** Install every dependency directly on the host; provide separate commands for each service; use one Docker Compose project.
- **Choice:** Use a single Compose project with web, API, PostgreSQL, Qdrant, bootstrap, evaluator, and optional Ollama services.
- **Why:** It keeps service boundaries realistic while giving the project one repeatable startup command.
- **Consequences:** The first startup is slower because images and model dependencies must be downloaded. Persistent data lives in named volumes.
- **Evidence:** Compose can express startup ordering, health checks, profiles, and durable volumes in one reviewable file.
- **Revisit when:** A hosted environment requires managed databases, independent scaling, or an orchestrator-specific manifest.

## 2026-09-16 — Keep generation credentials server-side

- **Context:** The browser must never receive the Gemini API key.
- **Alternatives:** Call Gemini from React; proxy calls through FastAPI; require only local Ollama.
- **Choice:** All generation providers are called from FastAPI. Compose reads `GEMINI_API_KEY` from the host and passes it only to backend services.
- **Why:** This creates one enforceable secret boundary and keeps provider switching out of the frontend.
- **Consequences:** The API is required for analysis even when the interface is otherwise static.
- **Evidence:** The web image has no Gemini build argument or environment entry, and the browser calls only `/api`.
- **Revisit when:** Provider calls move behind a dedicated internal inference service.

## 2026-09-16 — Make New case the real analysis entry point

- **Context:** A support copilot is only useful if an engineer can submit an unseen case; a demo-ticket browser alone would not exercise the product's core behavior.
- **Alternatives:** Restrict the interface to seeded examples; use a disconnected visual form; send New case through the complete RAG pipeline.
- **Choice:** Subject, product area, and description from New case are submitted to the same retrieval, reranking, confidence, and generation path used by demo cases.
- **Why:** This makes the central interaction truthful and testable while retaining safe examples for quick evaluation.
- **Consequences:** Loading, provider failure, insufficient evidence, and rate-limit states become required product states rather than edge cases.
- **Evidence:** The public API has one analysis contract for seeded and newly entered cases.
- **Revisit when:** A ticket-system integration supplies richer structured context or requires a separate ingestion workflow.

## 2026-09-16 — Do not persist submitted ticket text

- **Context:** Support tickets may contain sensitive customer and infrastructure details, while the MVP only needs the text during one request.
- **Alternatives:** Store all requests for analytics; redact then store; keep the input in memory and store only explicit feedback.
- **Choice:** Process subject, product area, and description in memory and never write them to PostgreSQL, Qdrant, or application logs.
- **Why:** It minimizes data exposure without weakening the requested analysis flow.
- **Consequences:** A user cannot reopen prior private submissions, and evaluation must use committed public or synthetic cases instead of production history.
- **Evidence:** The database schema contains feedback and evaluation metadata but no ticket-body columns.
- **Revisit when:** A production retention policy, access controls, deletion workflow, and security review exist.

## 2026-09-16 — Treat escalation as a successful product outcome

- **Context:** Retrieval systems can return weak, irrelevant, or contradictory evidence. A fluent answer is unsafe in those conditions.
- **Alternatives:** Always produce a best-effort draft; show a warning beside every draft; block the draft and explain the handoff.
- **Choice:** Unsupported cases return a structured escalation with the reason, missing signals, and available evidence.
- **Why:** The system should optimize for safe support decisions rather than answer rate.
- **Consequences:** Some answerable cases may initially escalate until the threshold and corpus improve.
- **Evidence:** Final evaluation measures escalation precision, recall, F1, and the confusion matrix alongside retrieval quality.
- **Revisit when:** Development-set tuning or pilot review shows a systematic class of safe cases being rejected.

## 2026-09-16 — Pin short support notes to primary sources

- **Context:** A reproducible demo corpus needs stable content and provenance without redistributing large copies of documentation or depending on live web pages during startup.
- **Alternatives:** Scrape sources on every run; commit full upstream pages; commit concise support notes with source metadata and hashes.
- **Choice:** Store original, human-readable support notes derived from PostgreSQL documentation, pgvector documentation, and resolved pgvector issues. Pin each note to its source URL, license context, retrieval date, and SHA-256 hash.
- **Why:** This keeps the corpus reviewable, starts offline after model download, and makes source drift explicit.
- **Consequences:** The corpus is deliberately small and must be refreshed manually when upstream behavior changes.
- **Evidence:** Bootstrap rejects a changed source file when its recorded hash no longer matches.
- **Revisit when:** Corpus maintenance volume justifies an automated, reviewed ingestion pipeline.

## 2026-09-16 — Version the corpus from verified chunk content

- **Context:** Re-running bootstrap must not create duplicate points, and a changed note must produce an observable new corpus state.
- **Alternatives:** Use a timestamp; reuse a static version; hash stable chunk identifiers and content.
- **Choice:** Derive the corpus version from sorted chunk IDs, source hashes, and chunk-text hashes, then rebuild Qdrant only when that value changes.
- **Why:** The same inputs produce the same version and an actual content change cannot silently reuse the old index.
- **Consequences:** Any edited note triggers a complete small-corpus rebuild rather than an incremental update.
- **Evidence:** Unit tests prove deterministic chunks and versions, and the indexer returns `unchanged` on a matching collection.
- **Revisit when:** The corpus is large enough that incremental, transactional index updates materially reduce maintenance cost.

## 2026-09-16 — Combine lexical and semantic retrieval before reranking

- **Context:** Database incidents mix exact identifiers and error phrases with broader descriptions of symptoms. Either lexical or semantic retrieval alone can miss one side of that pattern.
- **Alternatives:** Dense search only; sparse search only; weighted score addition; reciprocal-rank fusion followed by a small cross-encoder.
- **Choice:** Retrieve 30 dense and 30 BM25 candidates, combine their ranks with reciprocal-rank fusion, rerank the best 20 with `ms-marco-TinyBERT-L-2-v2`, discard obviously irrelevant passages below the development floor, and return at most five passages.
- **Why:** Rank fusion avoids pretending the dense and sparse raw scores share a calibrated scale, while the small reranker improves ordering without sending corpus data to the generation provider.
- **Consequences:** The API process keeps three local models available and has a larger cold-start cost.
- **Evidence:** Unit tests cover fusion and diversity behavior; the evaluation suite will measure precision, recall, and reciprocal rank against dense-only and sparse-only baselines.
- **Revisit when:** Evaluation shows one retrieval path adds no value, corpus growth requires a different reranker, or latency exceeds the gate.

## 2026-09-16 — Prefer source diversity in the final context

- **Context:** Five high-scoring chunks from one document can look strong while providing little independent corroboration.
- **Alternatives:** Take the top five verbatim; allow one chunk per source; prefer unique sources and then permit a second passage.
- **Choice:** Fill the final context with distinct sources first, then allow at most one additional passage per source.
- **Why:** It exposes the generator and reviewer to broader evidence without discarding useful adjacent detail.
- **Consequences:** A slightly lower-ranked document can displace a second passage from the leading source.
- **Evidence:** The selection rule is deterministic and covered by a focused test.
- **Revisit when:** Claim-level evaluation shows adjacent same-source passages are systematically necessary.
