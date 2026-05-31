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

## 2026-09-16 — Put every generation provider behind one strict contract

- **Context:** The local demo needs Gemini by default, an Ollama option, and deterministic tests without making confidence or citation behavior provider-specific.
- **Alternatives:** Implement separate response shapes; expose raw provider text; validate all providers against one schema.
- **Choice:** Gemini, Ollama, and mock providers return the same strict object: category, summary, cited steps, missing signals, conflicts, and an answerable flag.
- **Why:** Downstream safety checks and the interface can be provider-independent, and malformed output has one fail-closed path.
- **Consequences:** Provider features that do not fit the contract are ignored, and schema changes must be coordinated across all adapters.
- **Evidence:** Tests cover deterministic cited output, prompt isolation, and rejection of malformed JSON.
- **Revisit when:** A provider-independent field is demonstrably missing from real support reviews.

## 2026-09-16 — Send only selected evidence to generation

- **Context:** The ticket and corpus can contain prompt-injection text, and sending excess context makes unsupported synthesis harder to detect.
- **Alternatives:** Send the full corpus; send raw retrieval candidates; send only the five selected passages with explicit untrusted delimiters.
- **Choice:** Build the provider request from the ticket and final evidence set, label both as untrusted, require retrieved chunk IDs as citations, and request low-temperature structured JSON.
- **Why:** It narrows the model's evidence boundary and makes citation validation deterministic.
- **Consequences:** Missing retrieval evidence cannot be repaired by model memory; the case must escalate instead.
- **Evidence:** The prompt contract is inspected in tests and downstream validation rejects unknown citations.
- **Revisit when:** A measured failure requires a larger context window without reducing faithfulness.

## 2026-09-16 — Move the default from Gemini 2.5 Flash-Lite to 3.5 Flash-Lite

- **Context:** The original plan selected `gemini-2.5-flash-lite`, but a live API smoke test returned `404 NOT_FOUND` for a new user and directed the client to `gemini-3.5-flash-lite`.
- **Alternatives:** Keep a default that cannot run for this project; use the larger Flash model; adopt the current stable Flash-Lite model while leaving configuration open.
- **Choice:** Default to `gemini-3.5-flash-lite` and retain `GEMINI_MODEL` as an explicit override.
- **Why:** It preserves the intended low-latency, cost-conscious model class and is currently available with structured-output support.
- **Consequences:** The implementation differs from the original model identifier, and evaluation results must state the exact model used rather than the family name alone.
- **Evidence:** The live 2.5 request failed with the provider's migration message; Google's current model documentation lists 3.5 Flash-Lite as stable and structured-output capable.
- **Revisit when:** Google deprecates the model, the evaluation gate fails, or another supported model provides materially better faithfulness within the latency target.

## 2026-09-16 — Make confidence an inspectable evidence score

- **Context:** A single opaque confidence number can be mistaken for a calibrated probability and cannot explain why a case was escalated.
- **Alternatives:** Show the model's self-reported confidence; expose no score; calculate evidence strength from observable pipeline signals.
- **Choice:** Combine reranker relevance, source diversity, dense/sparse agreement, and valid citation coverage into a bounded evidence-strength score. Show every factor and compare the total with a development-tuned threshold.
- **Why:** Each factor can be measured, tested, and explained without claiming a probability of correctness.
- **Consequences:** The weighting is a product policy and requires evaluation; a strong score still cannot override conflicts, malformed output, or provider failure.
- **Evidence:** Analysis tests cover valid drafts, unknown citations, weak evidence, and provider failures.
- **Revisit when:** Development or pilot data supports a better-calibrated scoring model.

## 2026-09-16 — Store feedback separately from case content

- **Context:** Product learning needs outcome signals, but storing submitted case text would violate the MVP's data-minimization boundary.
- **Alternatives:** Store the full analysis; store redacted tickets; store only an opaque analysis ID and explicit feedback fields.
- **Choice:** Persist helpfulness, acceptance, optional correction or comment, and estimated minutes saved against a random analysis ID.
- **Why:** It supports quality review without reconstructing the original customer case.
- **Consequences:** Feedback cannot be replayed automatically against the original input.
- **Evidence:** The feedback table has no subject, description, or ticket-text column, and this invariant is tested.
- **Revisit when:** A reviewed retention design provides encryption, access control, deletion, and a legitimate need for case-level replay.

## 2026-09-16 — Frame Recall as a support copilot

- **Context:** The product helps an operator investigate and decide; it does not autonomously resolve or close customer incidents.
- **Alternatives:** Present Recall as an answer bot; present it as a search console; describe it as a support copilot.
- **Choice:** Use the product line “Support copilot” and keep a human decision point on both drafts and escalations.
- **Why:** The label matches the actual authority boundary and avoids implying that generated steps are executed automatically.
- **Consequences:** The interface emphasizes evidence and review over conversational novelty.
- **Evidence:** The workbench exposes sources, confidence factors, escalation reasons, and explicit feedback controls beside every result.
- **Revisit when:** Recall can safely execute a narrowly defined remediation with audited approval.

## 2026-09-16 — Run New case through the complete analysis pipeline

- **Context:** A prominent New case action would be misleading if it opened a static mock or bypassed retrieval.
- **Alternatives:** Use a prerecorded example; build a separate form page; open a composer inside the workbench and submit to the public analysis API.
- **Choice:** New case clears the selected demo, accepts subject, description, and optional product area, then calls `/api/v1/tickets/analyze` and renders the returned retrieval evidence, cited draft, or escalation in place.
- **Why:** The primary workflow demonstrates the real RAG behavior while preserving the operator’s context.
- **Consequences:** Provider and retrieval failures must have visible, recoverable interface states.
- **Evidence:** Component tests verify blank-case creation and a real analysis request producing cited evidence.
- **Revisit when:** Case creation needs attachments, identity, or integration with an external ticket system.

## 2026-09-16 — Use an evidence-dense escalation console

- **Context:** Operators must compare a case, a proposed resolution, and the supporting passages without losing the queue.
- **Alternatives:** Chat-first layout; a dashboard of summary cards; a three-pane escalation console.
- **Choice:** Use the approved escalation-console direction: queue at left, case and decision in the center, evidence ledger at right, with the primary workflow restacked for narrow screens.
- **Why:** It keeps provenance adjacent to each decision and makes weak-evidence handoff a first-class state.
- **Consequences:** The desktop view is intentionally dense; mobile prioritizes the active case before secondary queue context.
- **Evidence:** The implementation uses semantic text, tables, landmarks, keyboard focus, reduced-motion support, and an automated accessibility scan rather than decorative raster UI assets.
- **Revisit when:** Usability testing shows operators need a different default information hierarchy.

## 2026-09-16 — Bind analysis results to the submitted case

- **Context:** Generation can take several seconds, during which an operator may select another queue item or begin a new case.
- **Alternatives:** Disable all navigation; allow late responses to render; cancel the request and reject results whose request version is no longer active.
- **Choice:** Abort the previous browser request on case changes and guard every response with a monotonically increasing request version.
- **Why:** A resolution drafted from one incident must never appear under another incident, even if the network completes an already-cancelled request.
- **Consequences:** Leaving a case discards any in-progress result and the operator must analyze it again if they return.
- **Evidence:** A component test resolves an older request after New case is selected and verifies that its draft is not rendered.
- **Revisit when:** Per-case background jobs and an authenticated result inbox replace synchronous browser requests.

## 2026-09-16 — Never infer outcome metrics from a button click

- **Context:** Draft acceptance is a useful feedback signal, but it does not prove a fixed amount of time was saved.
- **Alternatives:** Store a default estimate; omit time saved; ask the operator for an observed estimate.
- **Choice:** Record acceptance without `minutes_saved` unless a person explicitly supplies that measurement.
- **Why:** Portfolio evaluation must use real observations rather than a convenient fabricated number.
- **Consequences:** The local demo reports no time-saved result before a pilot collects it.
- **Evidence:** The UI test inspects the feedback request and verifies that draft acceptance sends a null time-saved value.
- **Revisit when:** The feedback flow includes an optional, clearly labeled time-saved input.

## 2026-09-16 — Tune safety policy on development data only

- **Context:** The evidence-strength cutoff affects both useful drafts and unsafe answers, so selecting it on final test outcomes would overfit the reported benchmark.
- **Alternatives:** Keep an arbitrary cutoff; tune against all 80 cases; reserve a development split and lock the final test split.
- **Choice:** Use 20 development cases to select a 0.55 evidence threshold, then report the unchanged policy on 60 locked test cases.
- **Why:** It separates product-policy selection from the measurement used to describe generalization.
- **Consequences:** The small development split makes the threshold provisional, and the complete threshold sweep remains in the raw run file.
- **Evidence:** The selected threshold achieved 90% development accuracy and 100% unsupported-case recall; the locked test achieved 95% accuracy and 100% recall.
- **Revisit when:** A larger independently labeled case set or pilot feedback supports recalibration.

## 2026-09-16 — Treat explicit evidence gaps as a pre-generation safety signal

- **Context:** Retrieval can find topically relevant guidance even when a case explicitly says that essential logs, timestamps, query plans, or reconciled measurements are unavailable.
- **Alternatives:** Let the model decide every time; lower retrieval scores; detect a narrow set of explicit missing or conflicting signals before generation.
- **Choice:** Escalate cases that explicitly report those diagnostic gaps before calling a model, while still returning the retrieved passages for operator context.
- **Why:** Topical similarity cannot make absent incident evidence appear, and a deterministic guard is testable across providers.
- **Consequences:** The policy intentionally favors conservative false escalations and must remain narrow enough not to block documented reversible diagnostics.
- **Evidence:** Missing-evidence and contradiction cases reached 100% escalation recall on both evaluation splits, with three conservative false escalations on the locked test.
- **Revisit when:** Real support cases show recurring false positives or identify additional high-risk missing signals.

## 2026-09-16 — Pace the provider benchmark and publish rate-limit behavior

- **Context:** An initial unpaced Gemini benchmark caused 26 generation failures, making provider quota behavior dominate quality results.
- **Alternatives:** Hide the failed run; report it as model quality; preserve it as operational evidence and rerun with controlled spacing outside the latency timer.
- **Choice:** Keep the unpaced raw result, add bounded retries, and use a 2.5-second inter-request delay for the reported quality run.
- **Why:** Quality metrics should measure the pipeline under a viable request rate, while the burst failure remains important deployment evidence.
- **Consequences:** The local test takes longer, and production still needs explicit rate limiting, backoff, and capacity planning.
- **Evidence:** The controlled test completed 49 of 49 provider attempts and the 30-request latency run completed without failures.
- **Revisit when:** Production quota, concurrency, or provider changes.

## 2026-09-16 — Report Ollama as unavailable on the tested machine

- **Context:** The optional containerized `qwen3:4b` provider loaded its manifest, but the Docker VM exposed 1.9 GiB and Ollama required 3.3 GiB.
- **Alternatives:** Substitute a smaller unplanned model; report estimated performance; record the failed smoke test and give an exact rerun condition.
- **Choice:** Keep `qwen3:4b` as configured, report no Ollama quality or latency result, and require at least 4 GiB of Docker memory before rerunning.
- **Why:** A missing measurement is more honest than a comparison made with a different model or invented values.
- **Consequences:** The current deliverable validates provider switching and fail-closed behavior but not local-model quality.
- **Evidence:** The real Ollama request returned HTTP 500 with a model-memory requirement of 3.3 GiB; Recall converted it into an escalation.
- **Revisit when:** The Docker VM memory allocation is increased or the project deliberately adopts a smaller named model.
