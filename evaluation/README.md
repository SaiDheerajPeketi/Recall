# Evaluation

Recall uses 80 synthetic, human-readable database-support cases grounded in the pinned corpus:

- 20 development cases for retrieval checks and threshold selection.
- 60 locked test cases for the reported final measurements.

The labels identify the expected source documents and whether Recall should draft or escalate. The set includes known-answer, ambiguous, irrelevant, contradictory, missing-evidence, and prompt-injection cases. It is a project benchmark, not an independent human evaluation.

## Reproduce the runs

Start the local stack and make either `GEMINI_API_KEY` or `GOOGLE_API_KEY` available to Compose. The key is read at runtime and is not written to a file.

```bash
docker compose up -d --build

# Development split and threshold trace
docker compose run --rm evaluator python -m app.evaluation \
  --split dev --provider gemini --request-delay-ms 2500 \
  --output /app/evaluation/results/dev-gemini-controlled.json

# Locked test and 30-request warm latency run
docker compose run --rm evaluator python -m app.evaluation \
  --split test --provider gemini --request-delay-ms 2500 --latency-runs 30 \
  --output /app/evaluation/results/test-gemini-controlled.json

# Provider-independent smoke run
GENERATION_PROVIDER=mock docker compose run --rm evaluator python -m app.evaluation \
  --split test --provider mock
```

The delay is outside measured request latency. It prevents a local benchmark from turning into an artificial provider burst test.

For Ollama, allocate at least 4 GiB to the Docker VM before loading `qwen3:4b`:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull qwen3:4b
OLLAMA_BASE_URL=http://ollama:11434 docker compose run --rm evaluator \
  python -m app.evaluation --split test --provider ollama --latency-runs 30
```

## Metric definitions

- Precision@5, Recall@5, and MRR use the expected source IDs for cases with retrieval labels.
- Claim-level faithfulness requires every step citation to exist in the retrieved context and a local BGE cosine similarity of at least 0.45 between the step and cited text.
- Citation coverage reports whether each actionable step has only valid retrieved citations.
- Escalation treats `escalate` as the positive class and reports accuracy, precision, recall, F1, and a confusion matrix.
- Warm latency is end-to-end analysis latency after one warm-up request. Raw samples are retained.

See [REPORT.md](REPORT.md) for results, limitations, and the exact raw-output filenames.
