# Recall walkthrough script

This is the narration from the 59.7-second product walkthrough.

- **Voice:** Kokoro `af_heart`, generated offline
- **Timing:** Final voice clips use a 0.85× post-generation tempo adjustment
- **Direction:** Calm and conversational, with technical terms read clearly
- **Captions:** Burned-in phrase captions with uniform word styling, plus a separate WebVTT file
- **Music:** Restrained locally synthesized pulse beneath the narration

## 0.000–4.574 — Repeated work

Support teams keep solving the same database incidents from scratch.

## 4.574–11.908 — New case

Recall is a support copilot. A new case starts the full RAG pipeline—not a canned demo.

## 11.908–22.590 — Retrieval

It searches dense and BM25 indexes, fuses the results, reranks the strongest evidence, and keeps only diverse source passages.

## 22.590–34.441 — Resolution

Gemini drafts an answer only from that evidence. Every operational step links back to a retrieved chunk, so the operator can inspect the source before acting.

## 34.441–42.669 — Escalation

When logs are missing or evidence conflicts, Recall stops and produces a clear escalation instead of guessing.

## 42.669–54.570 — Evaluation

On sixty locked tests, citation coverage was one hundred percent, escalation recall one hundred percent, and warm p95 latency 2.2 seconds.

## 54.570–59.694 — Close

Recall is Docker-ready, locally validated, and available on GitHub.
