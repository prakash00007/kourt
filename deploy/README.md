# Public Hosting Guide (Anyone Can Access)

This setup deploys Kourt behind Caddy with HTTPS, so users open one domain and use both frontend and API from the same site.

## 1. Prerequisites

- A Linux VPS (Ubuntu 22.04+ recommended)
- A domain pointing to the VPS public IP (`A` record)
- Docker + Docker Compose plugin installed on the VPS

## Quick Share (Temporary URL)

If you want a public link immediately from your local machine:

```bash
# Terminal 1
cd backend
./venv312/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2
cd frontend
npm run build && npm start

# Terminal 3
ngrok http 3000
```

Share the `https://...ngrok-free.dev` URL shown by ngrok.

## 2. Prepare environment files

From repo root:

```bash
cp backend/.env.example backend/.env
cp deploy/.env.public.example deploy/.env.public
```

Edit `deploy/.env.public` and set:

- `PUBLIC_DOMAIN`
- `ACME_EMAIL`
- `GROQ_API_KEY`
- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`

For production safety, keep in `backend/.env`:

- `ALLOW_ANONYMOUS_DEMO=false`
- `ENABLE_DOCS=false`
- `CREATE_SCHEMA_ON_STARTUP=false`

## 3. Start public stack

```bash
docker compose --env-file deploy/.env.public -f deploy/docker-compose.public.yml up -d --build
```

## 4. Verify

```bash
docker compose --env-file deploy/.env.public -f deploy/docker-compose.public.yml ps
curl -sS https://your-domain.com/api/health
```

Open:

- `https://your-domain.com`

## 5. Update later

```bash
git pull
docker compose --env-file deploy/.env.public -f deploy/docker-compose.public.yml up -d --build
```

## 6. Logs and stop

```bash
docker compose --env-file deploy/.env.public -f deploy/docker-compose.public.yml logs -f
docker compose --env-file deploy/.env.public -f deploy/docker-compose.public.yml down
```
