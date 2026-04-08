# Kourt Frontend

Next.js frontend for the AI copilot MVP.

## Local setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The app expects the FastAPI backend at `http://localhost:8000/api` unless you override `NEXT_PUBLIC_API_BASE_URL`.
