# Kourt Production Architecture

This document describes the production-ready architecture for Kourt after hardening from MVP mode.

## Stack

- Frontend: Next.js (standalone build)
- Backend: FastAPI + Gunicorn/Uvicorn workers
- Database: PostgreSQL
- Cache + rate-limit state: Redis
- Object storage: S3-compatible storage (MinIO locally, S3 in cloud)
- Vector store: ChromaDB persistent store
- Observability: structured JSON logs + Prometheus metrics endpoint
- Migrations: Alembic
- Agent orchestration: LangGraph state-machine workflow for research

## Agent package layout

The system now uses a strict hierarchical agent package:

- `app/agents/main/supervisor.py`: main supervisor agent that reports final step trace
- `app/agents/tasks/research/supervisor.py`: LangGraph research task supervisor
- `app/agents/tasks/research/state.py`: typed state for graph execution
- `app/agents/tasks/research/subagents/*`: planner/retriever/synthesizer/verifier subagents
- `app/agents/tasks/drafting/supervisor.py`: drafting task supervisor
- `app/agents/tasks/drafting/subagents/drafting_worker.py`: drafting worker subagent
- `app/agents/tasks/summarization/supervisor.py`: summarization task supervisor
- `app/agents/tasks/summarization/subagents/summarization_worker.py`: summarization worker subagent
- `app/agents/shared/trace.py`: common trace/report contracts

## Runtime contracts

- `APP_ENV=production`
- `ENABLE_DOCS=false`
- `ALLOW_ANONYMOUS_DEMO=false`
- `CREATE_SCHEMA_ON_STARTUP=false`
- `JWT_SECRET_KEY` must be a secure value
- Health endpoints:
  - `/api/health/live`
  - `/api/health/ready`
  - `/api/health`
- Metrics endpoint:
  - `/api/metrics`
- Multi-agent endpoint:
  - `/api/agents/research` (LangGraph supervisor + planner/retriever/synthesizer/verifier subagents)

## Deployment shape

Production compose now includes:

- `frontend`
- `backend`
- `postgres`
- `redis`
- `minio`

`backend` runs Alembic migrations during container start and then starts Gunicorn.

## Security and reliability controls

- Trusted hosts validation through `TRUSTED_HOSTS`
- Strict production config validation inside `Settings`
- Rate limiting for public API routes (health and metrics excluded)
- DB pool tuning (`pool_pre_ping`, timeout, recycle)
- Healthchecks on frontend/backend/postgres/redis

## CI

The repository now includes a CI workflow at `.github/workflows/ci.yml`:

- Backend: install dependencies and run `pytest`
- Frontend: install dependencies and run `npm run build`

## Go-live checklist

1. Set production secrets in environment:
   - API keys
   - JWT secret
   - DB credentials
   - S3 credentials
2. Run `docker compose -f docker-compose.prod.yml up -d --build`.
3. Verify:
   - `GET /api/health/live`
   - `GET /api/health/ready`
   - `GET /api/metrics`
4. Configure external monitoring and alerting on readiness and HTTP error rate.
