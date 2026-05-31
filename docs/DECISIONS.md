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
