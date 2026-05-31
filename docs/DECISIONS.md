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

