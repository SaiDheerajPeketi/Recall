# Recall evaluation report

Run date: 2026-09-16  
Corpus: pinned PostgreSQL and pgvector public sources in `data/sources.json`  
Generator: Gemini 3.5 Flash-Lite  
Evidence threshold: 0.55, selected on the 20-case development split

## Results

| Measure | Development | Locked test |
| --- | ---: | ---: |
| Cases | 20 | 60 |
| Retrieval cases | 18 | 52 |
| Precision@5 | 0.3333 | 0.2923 |
| Recall@5 | 1.0000 | 0.9904 |
| MRR | 0.9213 | 0.9119 |
| Claim-level faithfulness | 100% (36 claims) | 100% (97 claims) |
| Citation coverage | 100% | 100% |
| Escalation accuracy | 90% | 95% |
| Escalation precision | 66.67% | 80% |
| Escalation recall | 100% | 100% |
| Escalation F1 | 80% | 88.89% |
| Provider success | 16/16 attempts | 49/49 attempts |

The locked-test escalation confusion matrix was 12 true escalations, 45 true drafts, 3 conservative false escalations, and 0 unsafe false drafts. This clears the project gates of at least 90% claim-level faithfulness and at least 90% unsupported-case escalation recall.

Retrieval latency on the locked test was 80.65 ms p50 and 91.75 ms p95. A separate 30-request warm end-to-end run measured 2,050 ms p50 and 2,216 ms p95, with a 1,544–2,640 ms range, 30 drafts, and no provider failures. This clears the 10-second Gemini p95 gate.

## Provider behavior

The first unpaced Gemini run triggered 26 generation failures and converted all of them into safe escalations. That run is retained as operational evidence, but it is not used for the quality claim. The controlled run waited 2.5 seconds between requests outside the latency timer and completed all 49 model calls successfully. The application also retries transient Gemini request failures up to two times before escalating.

The Ollama integration reached the container and attempted a real `qwen3:4b` request. The configured Docker VM exposed 1.9 GiB, while Ollama reported that the model required 3.3 GiB, so the request failed safely before generation. No Ollama quality or latency comparison is claimed from that environment. Increase Docker memory to at least 4 GiB and rerun the documented command to produce one.

## What these numbers do not prove

- The cases are synthetic and labeled for this project; they have not been independently adjudicated by support engineers.
- The faithfulness check is an automated citation-and-semantic-support proxy, not a human factuality review.
- The corpus is intentionally small and limited to PostgreSQL and pgvector material.
- No pilot users have measured time saved, so Recall makes no productivity claim.
- Provider latency and rate limits can vary by account, region, and time.

## Raw measurements

- `results/dev-gemini-controlled.json` — current 20-case development run and full threshold sweep.
- `results/test-gemini-controlled.json` — current 60-case locked test plus all 30 latency samples.
- `results/test-gemini.json` — initial unpaced run retained to show provider-rate behavior.
- `results/ollama-smoke.json` — one attempted local-model request and its fail-closed result.

Case text is used only during the run. Result rows contain case IDs, tags, retrieved chunk IDs, scores, actions, and measurements—not submitted case text.
