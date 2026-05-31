# Technical decisions

This file records the decisions that are easy to forget when changing the project. It is deliberately short; implementation details belong next to the code and operating instructions belong in the README.

## One local stack

Recall uses Docker Compose for the web app, API, PostgreSQL, Qdrant, bootstrap job, evaluator, and optional Ollama service. This makes the project slower to start for the first time, but gives contributors one repeatable setup.

The cloud Compose file is only an overlay for a single host. It is not intended to stand in for authentication, backups, monitoring, or a production deployment plan.

## Case text is transient

Subjects, descriptions, and product areas are processed in memory and are not stored in PostgreSQL, Qdrant, or application logs. Feedback is saved against a random analysis ID and cannot be used to reconstruct the original case.

Gemini requests cross the local machine boundary. Ollama stays with the configured Ollama endpoint, and the mock provider makes no model call.

## Retrieval is hybrid

Database incidents contain both exact error text and loose descriptions of symptoms, so Recall uses dense search and BM25. It combines their ranks with reciprocal-rank fusion, reranks the top candidates, and prefers source diversity in the final five passages.

The corpus consists of short notes tied to public PostgreSQL and pgvector sources. Bootstrap verifies their hashes and derives the corpus version from the content, making repeated runs deterministic.

## Escalation is a valid result

Recall does not have to answer every case. It escalates when evidence is weak or contradictory, required diagnostics are explicitly missing, a provider fails, structured output is invalid, or a response cites material that was not retrieved.

The evidence score is built from retrieval strength, source diversity, dense/sparse agreement, and citation coverage. It is an inspectable policy score, not a probability that the answer is correct.

## Providers share one response shape

Gemini, Ollama, and the mock provider all return the same structured fields. This keeps validation and the interface independent of the selected provider. Provider-specific features are ignored unless they fit that contract.

Gemini 3.5 Flash-Lite is the default because the earlier 2.5 Flash-Lite identifier was unavailable to the account used for validation. `GEMINI_MODEL` remains configurable.

## Evaluation has a held-out split

Twenty cases are used to choose the evidence threshold; the remaining sixty are kept for the reported test result. Provider requests are spaced during the quality run so rate limiting does not dominate the measurement. The delay is outside the latency timer.

The benchmark is synthetic and project-authored. Raw runs remain in the repository so readers can inspect both the successful controlled run and the earlier rate-limited run.

## The interface keeps evidence visible

The workbench keeps the selected case, decision, and supporting passages on one screen. It is intentionally closer to an incident console than a chat window. A request version and cancellation guard prevent a late response from appearing under a different case.

Submitted feedback never invents a time-saved estimate. Acceptance and usefulness can be recorded directly; time saved is only stored when a person supplies it.

## Walkthrough assets stay reproducible

The repository includes the video, transcript, captions, and poster. The walkthrough uses the real local interface and measured test results. It does not imply a public deployment or user pilot.

Last reviewed: May 31, 2026.
