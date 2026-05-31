# Deployment

Future deployment assets live here. No cloud service is created or contacted by the local build.

`compose.cloud.yaml` is an overlay for a single Docker host. It removes public ports from PostgreSQL, Qdrant, the API, the web container, and optional Ollama service; adds restart policies, health checks, resource limits, and Caddy ingress; and keeps state in named volumes.

## Validate without deploying

```bash
cp deploy/cloud.env.example .env.cloud
# Replace every placeholder locally, then validate the merged document:
docker compose --env-file .env.cloud -f compose.yaml -f compose.cloud.yaml config --quiet
```

The completed `.env.cloud` is ignored by Git. Validation parses and merges the configuration; it does not create containers or contact a cloud provider.

## Later deployment checklist

1. Provision a Linux host with Docker, enough disk for model caches and Qdrant, and at least 4 GiB RAM for Gemini-only operation. Containerized `qwen3:4b` needs additional memory.
2. Point the chosen domain's DNS records at the host and allow inbound TCP 80/443 plus UDP 443.
3. Put secrets in the host's secret manager or a root-readable environment file outside the repository.
4. Validate the merged Compose configuration with the exact production environment.
5. Start the stack, verify `/api/v1/health`, and test a safe case before sharing the URL.
6. Configure encrypted backups for the PostgreSQL, Qdrant, and Caddy volumes.
7. Add authentication, tenant isolation, rate limiting, monitoring, alerting, and a retention policy before accepting private support data.

This overlay is a deployment starting point, not a claim that Recall is production-ready or currently hosted.
