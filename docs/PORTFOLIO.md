# Recall portfolio copy

This copy reflects the current project honestly: Recall is validated locally and Docker-ready, but it is not publicly hosted and has not completed a user pilot.

## Resume description

Built Recall, a Dockerized support copilot that combines dense and BM25 retrieval, reciprocal-rank fusion, and cross-encoder reranking to draft cited PostgreSQL and pgvector resolutions or safely escalate weak evidence. Designed the React, FastAPI, Qdrant, and PostgreSQL system with Gemini, Ollama, and mock providers; across 60 locked tests it reached 99.04% Recall@5, 100% citation coverage, 100% unsupported-case escalation recall, and 2.216-second warm p95 latency.

## Build-in-public update 1 — The problem and architecture

I built Recall because support engineers should not have to reconstruct the same database diagnosis from scratch every time.

A New case runs through dense and BM25 retrieval, reciprocal-rank fusion, cross-encoder reranking, and evidence selection before a model can draft anything. The operator sees the proposed steps beside the exact source passages, so the workflow stays reviewable rather than becoming a black-box chat.

The current build runs locally with React, FastAPI, Qdrant, PostgreSQL, and Docker Compose. It is Docker-ready, not publicly hosted yet.

## Build-in-public update 2 — Safe failure is a feature

The most important Recall output is sometimes “do not guess.”

If incident evidence is weak or contradictory, required citations are missing, structured output is invalid, or the generation provider fails, Recall returns a visible escalation with the retrieved context. Ticket text is processed for the request but is not written to the feedback database or application logs.

That conservative policy produced three false escalations on the locked test, but no unsupported case received a draft. I chose that tradeoff deliberately for an operator-facing support tool.

## Build-in-public update 3 — Measuring the pipeline

I evaluated Recall on 20 development cases for threshold selection and a separate 60-case locked test split.

The locked run measured 0.9904 Recall@5, 0.9119 MRR, 100% citation coverage across 97 generated claims, 100% unsupported-case escalation recall, and 2.216-second warm p95 end-to-end latency over 30 requests. The raw result files and evaluation commands are committed with the project.

These are controlled local benchmark results, not production or user-pilot claims. The automated faithfulness check verifies source support and citation identity; it is not a replacement for independent human review.

## Build-in-public update 4 — A deployable handoff without pretending it is deployed

Recall now has a local Compose stack, a separate cloud-ready Compose overlay, health checks, persistent volumes, private data-service networking, Caddy ingress placeholders, and exact setup instructions.

I also produced a 59.7-second walkthrough from the real local interface with offline narration, burned-in captions, and the measured benchmark results. The repository is ready for someone else to run and evaluate; cloud infrastructure, production secrets, identity, monitoring, and a public URL are intentionally left for the deployment phase.
