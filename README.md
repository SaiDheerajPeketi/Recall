# Recall

Recall is a database-support copilot that turns an incoming case into either a cited resolution draft or a clear escalation. The project is currently under active local development.

## Local stack

The repository contains a React workbench, a FastAPI service, PostgreSQL for feedback, and Qdrant for retrieval. Docker Compose is the supported local runtime.

```bash
cp .env.example .env
docker-compose up --build
```

The web interface will be available at `http://localhost:3000` and the API at `http://localhost:8000`.

> This repository is locally validated and Docker-ready. It is not currently hosted.

