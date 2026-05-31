# Recall product contract

## What Recall is

Recall is a support copilot for database incidents. A support engineer submits a new case, Recall searches a pinned public knowledge base, and the workbench returns one of two outcomes:

1. a resolution draft whose actionable steps are linked to supporting passages; or
2. an escalation that states which evidence is missing or contradictory.

It is an evidence-navigation tool, not an autonomous operator. It does not connect to customer databases, run commands, change infrastructure, close tickets, or claim certainty that its sources do not support.

## Primary user and workflow

The primary user is an L1 or L2 support engineer handling PostgreSQL and pgvector cases.

1. Select a safe demo case or choose **New case**.
2. Enter a subject, an optional product area, and the case description.
3. Choose **Analyze case**. This action starts the real retrieval and generation pipeline.
4. Review the category, summary, evidence strength, source passages, and proposed steps.
5. Copy or adapt a supported draft, or follow the stated escalation handoff.
6. Submit outcome feedback without resubmitting the original ticket text.

## Answer boundary

Recall may draft an answer only when all of the following are true:

- retrieval finds sufficiently relevant and diverse evidence;
- the evidence is not materially contradictory;
- every actionable step has at least one valid source citation;
- the provider returns the required structured shape; and
- the confidence policy passes its tuned evidence threshold.

If any condition fails, Recall returns `action: escalate` with a plain-language reason. The evidence score is presented as evidence strength, not as a probability that the answer is correct.

## MVP scope

Included:

- PostgreSQL and pgvector support questions covered by the pinned public corpus;
- dense and sparse retrieval, reciprocal-rank fusion, and reranking;
- Gemini, Ollama, and deterministic mock generation providers;
- cited draft and escalation outcomes;
- feedback on helpfulness, acceptance, correction, comment, and estimated minutes saved;
- reproducible local evaluation and Docker-based setup.

Deferred:

- production hosting and a public URL;
- private company knowledge and historical customer tickets;
- ticket-system integrations;
- SSO, tenant isolation, audit retention, and compliance review;
- automated remediation or database access;
- claims about user time saved before a real pilot.

## Success measures

The engineering gates are claim-level faithfulness of at least 90%, unsupported-case escalation recall of at least 90%, and Gemini warm p95 latency of at most 10 seconds on the documented test machine. These are targets until an evaluation run records the measured result.

