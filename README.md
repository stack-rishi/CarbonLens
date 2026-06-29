# CarbonLens 🌿

> Scope 3 Supply Chain Carbon Intelligence Platform

CarbonLens helps organizations track, forecast, and optimize carbon 
emissions across their entire supply chain. Built for sustainability 
teams that need real data, not spreadsheets.

## Live Demo
- Frontend: [carbonlens.vercel.app](https://carbonlens.vercel.app)
- API: [carbonlens-api.fly.dev/docs](https://carbonlens-api.fly.dev/docs)

## Features
- **Real-time emission tracking** — Scope 1, 2 & 3 across all suppliers
- **Interactive supply chain map** — color-coded by emission intensity
- **AI-powered forecasting** — Prophet ML models per supplier
- **Carbon route optimizer** — OR-Tools LP solver, minimize CO2 per shipment
- **AI co-pilot** — Groq LLaMA 3.1 70B, grounded in your emission data
- **PDF reports** — GHG Protocol aligned, one-click generation

## Stack
| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Tailwind + shadcn/ui |
| Backend | Python FastAPI + SQLAlchemy + Alembic |
| Database | Supabase (PostgreSQL) + Row Level Security |
| AI/ML | Groq (LLaMA 3.1 70B) + Prophet + OR-Tools |
| Infra | Fly.io (backend) + Vercel (frontend) |
| Cost | $0/month on free tiers |

## Quick Start
```bash
git clone https://github.com/yourusername/carbonlens
cd carbonlens
cp .env.example .env
# Fill in .env with your Supabase + Groq keys
cd backend && poetry install && poetry run alembic upgrade head
poetry run python seed.py
cd ../frontend && npm install
python ../scripts/dev.py
```

Open http://localhost:5173
Login: admin@acmecorp.com / password123

## Architecture
```
carbonlens/
├── frontend/          # Vite + React 18 + TypeScript + Tailwind CSS + shadcn/ui
├── backend/           # Python FastAPI with Poetry
│   ├── api/           # route handlers
│   ├── services/      # business logic
│   ├── models/        # Pydantic schemas + SQLAlchemy ORM models
│   ├── workers/       # background tasks (FastAPI BackgroundTasks, no Celery)
│   └── core/          # config, db connection, auth middleware
├── scripts/           # dev, deploy, demo scripts
└── .github/workflows/ # CI/CD
```

## Deploy
See `scripts/deploy.md` for Fly.io + Vercel deployment guide.

## Hackathon
Built for the Hackathon by RISHI.
Category: Sustainability & CleanTech
