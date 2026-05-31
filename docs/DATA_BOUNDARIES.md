# Data and privacy boundaries

Recall's local demo is intentionally narrow: public documentation, resolved public issues, synthetic evaluation cases, and explicit user feedback.

## What is stored

| Data | Location | Purpose | Retention |
| --- | --- | --- | --- |
| Public source chunks and metadata | Qdrant named volume | Retrieval | Until the corpus is rebuilt or volumes are reset |
| Source URLs, licenses, retrieval dates, and hashes | Git repository | Provenance and reproducibility | Versioned with the corpus |
| Helpfulness and acceptance | PostgreSQL named volume | Product-quality feedback | Until local volumes are reset |
| Optional correction, comment, and minutes saved | PostgreSQL named volume | Qualitative review | Until local volumes are reset |
| Evaluation-run metadata | PostgreSQL named volume | Reproducibility | Until local volumes are reset |

## What is not stored

- New-case subject, description, or product area.
- Retrieved prompts or provider responses tied to a submitted case.
- Gemini or Ollama credentials.
- Browser analytics, cookies, or user identity.
- Private customer data in the committed corpus or demo tickets.

The API constructs case analysis in memory, returns the result, and discards the submitted text. Application logs record request IDs, status, provider, action, and latency, but never request bodies or generated prose.

## Provider boundary

With `GENERATION_PROVIDER=gemini`, the submitted case and selected public evidence leave the machine for Gemini processing. With `ollama`, generation stays with the configured Ollama endpoint. With `mock`, no model provider is contacted. The interface must always show which provider handled an analysis.

## Threats handled by the MVP

- Ticket text and retrieved documents are treated as untrusted data, never as system instructions.
- Citations must reference retrieved chunk identifiers; invented identifiers fail validation.
- Unsupported, conflicting, malformed, or provider-failed answers escalate.
- Secrets remain in backend runtime configuration and are never copied into images or frontend code.
- Feedback refers to a random analysis ID rather than storing the case text.

## Resetting local data

Stopping containers does not remove named volumes. The README's reset command deliberately removes the PostgreSQL and Qdrant volumes; use it only when local feedback and indexes can be discarded.

