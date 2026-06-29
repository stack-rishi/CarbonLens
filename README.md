<div align="center">

<img src="assets/banner.png" alt="CarbonLens Banner" width="100%"/>

<br/>

# 🌿 CarbonLens

### **AI-Powered Scope 3 Supply Chain Carbon Intelligence Platform**

> *Stop guessing your carbon footprint. Start optimizing it.*

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-carbonlens--app.vercel.app-00C853?style=for-the-badge&labelColor=1a1a2e)](https://carbonlens-app.vercel.app)
[![API Docs](https://img.shields.io/badge/📡_API-carbonlens--backend.onrender.com-7C4DFF?style=for-the-badge&labelColor=1a1a2e)](https://carbonlens-backend.onrender.com/docs)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/stack-rishi/CarbonLens/ci.yml?branch=main&style=for-the-badge&label=CI%2FCD&labelColor=1a1a2e&color=00C853)](https://github.com/stack-rishi/CarbonLens/actions)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a2e)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-3178C6?style=for-the-badge&logo=typescript&logoColor=white&labelColor=1a1a2e)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge&labelColor=1a1a2e)](LICENSE)

<br/>

**🏆 Built for OSF HackOne 2K26 — Final Round | Category: Sustainability & CleanTech**

**👨‍💻 Team Last Brain Cell**

<br/>

[✨ Key Features](#-key-features) · [🏗️ Architecture](#️-architecture) · [🧠 Innovation](#-innovation--originality) · [🚀 Quick Start](#-quick-start) · [📊 API Reference](#-api-reference) · [🌍 Impact](#-real-world-impact--scalability)

</div>

---

## 🎯 The Problem

**Scope 3 emissions account for 70-90% of a company's total carbon footprint** — yet they remain the hardest to track, buried across fragmented supplier data, complex logistics networks, and inconsistent reporting standards.

Today's sustainability teams rely on:
- ❌ **Manual spreadsheets** that are error-prone and static
- ❌ **Expensive enterprise tools** ($50K+/year) inaccessible to SMEs
- ❌ **Disconnected data** with no supply chain visibility
- ❌ **Zero predictive capabilities** — only backward-looking reports

> **The result?** Organizations can't identify their biggest emission hotspots, optimize logistics routes, or make data-driven decarbonization decisions — leaving billions of tonnes of CO₂ unoptimized.

---

## 💡 Our Solution

**CarbonLens** is a full-stack AI-powered platform that transforms how organizations track, forecast, and optimize Scope 1, 2 & 3 carbon emissions across their entire supply chain — **for free**.

<div align="center">

| Pain Point | CarbonLens Solution |
|:---|:---|
| Manual data entry | ✅ Bulk CSV import + automated emission factor calculations |
| No supply chain visibility | ✅ Interactive graph visualization with emission heat mapping |
| Backward-looking reports only | ✅ AI-powered forecasting per supplier + org-wide trends |
| Can't optimize logistics | ✅ OR-Tools linear programming solver for route optimization |
| Expensive enterprise tools | ✅ 100% free, open-source, self-hostable |
| Complex GHG standards | ✅ GHG Protocol-aligned PDF reports, one-click generation |
| No expert guidance | ✅ AI Co-Pilot trained on DEFRA, GHG Protocol, EU CSRD, SBTi |

</div>

---

## ✨ Key Features

### 📊 Real-Time Emission Dashboard
Track Scope 1, 2 & 3 emissions with interactive charts, trend analysis, and category breakdowns — all updating in real-time.

### 🔗 Interactive Supply Chain Visualization
Full-graph visualization powered by **React Flow** with:
- **Emission intensity heat mapping** (green → yellow → red nodes)
- **Trend indicators** (↑ ↓ →) per supplier based on 30-day rolling analysis
- **Transport mode visualization** on edges (road/rail/sea/air)
- **Dagre auto-layout** for optimal graph positioning

### 🤖 AI-Powered Carbon Co-Pilot
Conversational AI assistant powered by **Groq LLaMA 3.3 70B** with intelligent fallback to **Anthropic Claude 3 Haiku**:
- Grounded in your actual emission data
- Trained on DEFRA emission factors, GHG Protocol, EU CSRD, CBAM, SEC Climate Rules, India BRSR, TCFD, SBTi frameworks
- Provides actionable reduction strategies, not generic advice

### 🔮 Emission Forecasting
ML-powered predictions per supplier and org-wide, enabling proactive decarbonization planning.

### ⚡ Carbon Route Optimizer
**Google OR-Tools GLOP Linear Programming solver** that minimizes total carbon footprint across your supply chain:
- Decision variables: allocation (tonnes) per supplier
- Constraints: total demand satisfaction + minimum ESG score threshold
- Multi-modal transport comparison (road vs rail vs sea vs air)
- Quantified CO₂ savings per optimization run

### 📑 GHG Protocol-Aligned PDF Reports
Professional PDF reports generated via **ReportLab + Matplotlib** with:
- Scope breakdown donut charts
- Monthly emission trend area charts
- Top 10 supplier contributor tables with ESG scores
- Methodology & standard reference appendix
- Background async generation with status tracking

### 🛡️ Enterprise-Grade Security
- **Dual authentication**: Supabase primary + local JWT (HS256) fallback
- **RBAC**: Admin / Analyst / Viewer role hierarchy
- **Rate limiting** on auth endpoints (SlowAPI)
- **Security headers**: CSP, HSTS, X-Frame-Options, X-XSS-Protection
- **IDOR prevention**: org-scoped queries on all endpoints
- **Non-root Docker container** for production deployment
- **Production startup validation** for secrets

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Vercel)                          │
│  React 18 • TypeScript • Tailwind CSS • shadcn/ui • Zustand        │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │Dashboard │ │Emissions  │ │Suppliers │ │ Supply Chain Graph   │  │
│  │  Page    │ │  Ledger   │ │  Manager │ │  (React Flow+Dagre)  │  │
│  └──────────┘ └───────────┘ └──────────┘ └──────────────────────┘  │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐                          │
│  │AI Chat   │ │  Reports  │ │Onboarding│                          │
│  │ Co-Pilot │ │   Page    │ │  Wizard  │                          │
│  └──────────┘ └───────────┘ └──────────┘                          │
├────────────────────────┬────────────────────────────────────────────┤
│     Axios + Bearer     │  TanStack React Query (cache/invalidation)│
│     Token Auth         │  Sentry Error Tracking                    │
├────────────────────────┴────────────────────────────────────────────┤
│                       BACKEND API (Render)                         │
│  FastAPI • Python 3.11 • Poetry • Async SQLAlchemy • Alembic       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Middleware Stack                          │   │
│  │  Request Logging (structlog) → Security Headers → UUID IDs  │   │
│  │  Rate Limiting (SlowAPI) → CORS                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │Auth API  │ │Emission   │ │Supplier  │ │Supply Chain API      │ │
│  │/register │ │  API      │ │  API     │ │  /graph /edges       │ │
│  │/login    │ │/records   │ │/CRUD     │ │  /forecast /optimize │ │
│  │/me       │ │/summary   │ │/bulk     │ │                      │ │
│  └──────────┘ │/trend     │ │/optimize │ └──────────────────────┘ │
│               └───────────┘ └──────────┘                          │
│  ┌──────────┐ ┌───────────┐ ┌──────────────────────────────────┐  │
│  │Report    │ │AI Service │ │  Optimizer Service               │  │
│  │Generator │ │Groq→Claude│ │  Google OR-Tools GLOP LP Solver  │  │
│  │(ReportLab│ │→MockChain │ │  Multi-modal Route Comparison    │  │
│  │+Matplotlib│ └───────────┘ └──────────────────────────────────┘  │
│  └──────────┘                                                     │
├───────────────────────────────────────────────────────────────────┤
│                    DATABASE (Supabase)                             │
│  PostgreSQL + asyncpg • Connection Pool (10+20) • RLS             │
│  7 Tables: Organization, User, Supplier, EmissionRecord,          │
│  SupplyChainEdge, Report, AIConversation                          │
└───────────────────────────────────────────────────────────────────┘
```

### 📁 Project Structure

```
carbonlens/
├── frontend/                    # Vite + React 18 + TypeScript
│   ├── src/
│   │   ├── pages/               # 8 full pages (Dashboard, Emissions, etc.)
│   │   ├── components/          # Reusable components + 15 shadcn/ui primitives
│   │   ├── store/               # Zustand auth state management
│   │   ├── hooks/               # Custom React hooks
│   │   └── lib/                 # API client (Axios) + utilities
│   └── package.json
├── backend/                     # Python FastAPI + Poetry
│   ├── api/                     # Route handlers (auth, emissions, ai, etc.)
│   ├── services/                # Business logic layer
│   │   ├── ai_service.py        #   Multi-provider LLM (Groq → Claude → Mock)
│   │   ├── emission_service.py  #   Transport/energy/material calculations
│   │   ├── optimizer_service.py #   OR-Tools LP solver + route comparison
│   │   └── report_service.py    #   PDF generation (ReportLab + Matplotlib)
│   ├── models/                  # SQLAlchemy ORM + Pydantic schemas
│   ├── workers/                 # Background tasks (report compilation)
│   ├── core/                    # Config, DB connection, auth middleware
│   └── pyproject.toml
├── docker/                      # Multi-stage Dockerfile (non-root user)
├── scripts/                     # Dev server, deploy guides, setup docs
├── .github/workflows/ci.yml     # CI/CD: lint + typecheck + test (parallel)
└── assets/                      # Repository assets (banner, etc.)
```

---

## 🧠 Innovation & Originality

CarbonLens isn't just another dashboard — it combines **5 distinct technical innovations** in a single platform:

| # | Innovation | Technology | Why It Matters |
|:-:|:---|:---|:---|
| 1 | **Supply Chain Graph Intelligence** | React Flow + Dagre + rolling 30-day trend analysis | First platform to visualize emission *intensity & trends* as an interactive graph — not just numbers in a table |
| 2 | **Linear Programming Carbon Optimizer** | Google OR-Tools GLOP Solver | Mathematically optimal supplier allocation that minimizes CO₂ while satisfying demand & ESG constraints |
| 3 | **Multi-Provider AI with Domain Grounding** | Groq LLaMA 3.3 70B → Claude 3 Haiku → Mock | Resilient AI chain with 100% uptime guarantee; grounded in actual emission data + regulatory frameworks |
| 4 | **Real-Time Emission Factor Engine** | DEFRA-sourced factors (transport/energy/material) | Automated calculations using verified government emission factors, not user guesses |
| 5 | **Zero-Cost Full-Stack SaaS** | Vercel + Render + Supabase free tiers | Enterprise-grade platform running at $0/month — democratizing carbon intelligence for SMEs |

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology | Purpose |
|:---|:---|:---|
| **Frontend** | React 18 · TypeScript · Tailwind CSS · shadcn/ui | Type-safe, accessible UI with 15+ Radix primitives |
| **State** | Zustand · TanStack React Query | Lightweight global state + server state caching |
| **Visualization** | Recharts · React Flow · Dagre · Matplotlib | Charts, interactive graphs, PDF chart generation |
| **Backend** | FastAPI · Python 3.11 · Poetry · Pydantic v2 | Async API with full input validation |
| **Database** | Supabase (PostgreSQL) · Async SQLAlchemy · asyncpg | Connection pooling (10+20), Alembic migrations |
| **AI/ML** | Groq (LLaMA 3.3 70B) · Anthropic (Claude 3 Haiku) | Multi-provider with automatic failover |
| **Optimization** | Google OR-Tools (GLOP LP Solver) | Linear programming for carbon minimization |
| **Reports** | ReportLab · Matplotlib | Professional GHG Protocol-aligned PDFs |
| **Auth** | Supabase Auth + JWT (HS256) · bcrypt · RBAC | Dual auth with role-based access control |
| **Monitoring** | Sentry · structlog · SlowAPI | Error tracking, structured logging, rate limiting |
| **CI/CD** | GitHub Actions (2 parallel jobs) | Backend: ruff + mypy + pytest · Frontend: eslint + tsc |
| **Deploy** | Vercel (frontend) · Render (backend) | Zero-cost production deployment |
| **Container** | Docker (multi-stage, non-root) | Production-ready containerization |

</div>

---

## 📊 API Reference

### Base URL: `https://carbonlens-backend.onrender.com/api/v1`

<details>
<summary><b>🔐 Authentication (3 endpoints)</b></summary>

| Method | Endpoint | Description | Rate Limit |
|:---:|:---|:---|:---:|
| `POST` | `/auth/register` | Register organization + admin user | 5/min |
| `POST` | `/auth/login` | Login (Supabase + local JWT fallback) | 10/min |
| `GET` | `/auth/me` | Get current user profile | — |

</details>

<details>
<summary><b>📈 Emissions (6 endpoints)</b></summary>

| Method | Endpoint | Description | Role |
|:---:|:---|:---|:---:|
| `GET` | `/emissions/` | List records (paginated, date-filterable) | Any |
| `POST` | `/emissions/` | Create emission record | Admin/Analyst |
| `DELETE` | `/emissions/{id}` | Delete emission record | Admin |
| `GET` | `/emissions/summary` | Aggregated by scope/category/supplier | Any |
| `GET` | `/emissions/trend` | Monthly emission trends | Any |
| `POST` | `/emissions/bulk-import` | Bulk CSV import | Admin/Analyst |

</details>

<details>
<summary><b>🏭 Suppliers (8 endpoints)</b></summary>

| Method | Endpoint | Description | Role |
|:---:|:---|:---|:---:|
| `GET` | `/suppliers/` | List suppliers (paginated) | Any |
| `POST` | `/suppliers/` | Create supplier | Admin/Analyst |
| `DELETE` | `/suppliers/{id}` | Delete supplier | Admin |
| `GET` | `/suppliers/edges` | List supply chain edges | Any |
| `POST` | `/suppliers/edges` | Create supply chain edge | Admin/Analyst |
| `POST` | `/suppliers/optimize-sourcing` | OR-Tools LP optimization | Any |
| `POST` | `/suppliers/compare-routes` | Transport mode comparison | Any |
| `POST` | `/suppliers/bulk-import` | Bulk import suppliers | Admin/Analyst |

</details>

<details>
<summary><b>🤖 AI, Forecast, Optimize, Reports (8 endpoints)</b></summary>

| Method | Endpoint | Description |
|:---:|:---|:---|
| `GET` | `/ai/conversations` | List user's AI conversations |
| `POST` | `/ai/conversations` | Send message + get AI response |
| `GET` | `/forecast/{supplier_id}` | Forecast supplier emissions |
| `GET` | `/forecast/org/summary` | Org-wide emission forecast |
| `POST` | `/optimize/route` | Optimize transport route |
| `POST` | `/optimize/suppliers` | Optimize supplier sourcing (LP) |
| `POST` | `/reports/` | Generate PDF report (async) |
| `GET` | `/reports/` | List all reports |

</details>

---

## 🔐 Security Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Security Layers                      │
├──────────────────────────────────────────────────────┤
│  🔒 Dual Auth      │ Supabase + Local JWT (HS256)    │
│  👤 RBAC           │ Admin → Analyst → Viewer        │
│  🛡️ Rate Limiting  │ SlowAPI (5-10 req/min on auth)  │
│  🔑 Password Hash  │ bcrypt (passlib)                │
│  📋 Input Validation│ Pydantic v2 (regex, ranges)     │
│  🚫 IDOR Prevention│ org_id scoped queries            │
│  🌐 Security Headers│ CSP, HSTS, X-Frame-Options     │
│  📝 Request IDs    │ UUID per request (traceability)  │
│  🐳 Container      │ Non-root user in production      │
│  🔐 Startup Check  │ Fails fast on unsafe secrets     │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- **Node.js** ≥ 18 · **Python** ≥ 3.11 · **Poetry** · **Git**
- **Supabase** account (free tier) · **Groq** API key (free)

### 1. Clone & Setup
```bash
git clone https://github.com/stack-rishi/CarbonLens.git
cd CarbonLens
cp .env.example .env
# Fill in your Supabase + Groq keys in .env
```

### 2. Backend
```bash
cd backend
poetry install
poetry run alembic upgrade head
poetry run python seed.py          # Seeds demo data (5 suppliers, 24 months of emissions)
```

### 3. Frontend
```bash
cd frontend
npm install
```

### 4. Run Development Servers
```bash
python scripts/dev.py              # Starts both servers concurrently
```

### 5. Open & Explore
```
🌐 Frontend:  http://localhost:5173
📡 API Docs:  http://localhost:8000/docs
👤 Demo Login: admin@acmecorp.com / password123
```

> **Seed data includes**: Acme Corp organization, 5 international suppliers (India, Germany, Japan, US, UK), 24 months of historical emission records with seasonal trends, and 4 supply chain edges forming a connected logistics graph.

---

## 🐳 Docker Deployment

```bash
# Build production image (multi-stage, non-root)
docker build -f docker/Dockerfile.backend -t carbonlens-api .

# Run
docker run -p 8080:8080 --env-file .env carbonlens-api
```

The Dockerfile uses a **multi-stage build** for minimal image size:
- **Stage 1 (builder)**: Installs Poetry + production dependencies only
- **Stage 2 (final)**: Copies virtualenv, runs as non-root `appuser`

---

## 🧪 Testing & CI/CD

### Automated CI Pipeline (GitHub Actions)

Two **parallel** jobs run on every push and PR:

| Job | Steps |
|:---|:---|
| **backend-ci** | Python 3.11 → Poetry install → `ruff check` → `mypy --ignore-missing-imports` → `pytest` |
| **frontend-ci** | Node.js 18 → `npm ci` → `npm run lint` → `npm run typecheck` |

### Run Locally
```bash
# Backend
cd backend
poetry run ruff check .
poetry run mypy . --ignore-missing-imports
poetry run pytest

# Frontend
cd frontend
npm run lint
npm run typecheck
```

---

## 📐 Database Schema

```mermaid
erDiagram
    Organization ||--o{ User : has
    Organization ||--o{ Supplier : manages
    Organization ||--o{ EmissionRecord : tracks
    Organization ||--o{ SupplyChainEdge : connects
    Organization ||--o{ Report : generates
    Organization ||--o{ AIConversation : initiates

    Supplier ||--o{ EmissionRecord : produces
    Supplier ||--o{ SupplyChainEdge : "from/to"

    User ||--o{ Report : creates
    User ||--o{ AIConversation : chats

    Organization {
        uuid id PK
        string name
        string sector
        string country
        enum plan "free/pro/enterprise"
    }

    User {
        uuid id PK
        uuid org_id FK
        string email UK
        string password_hash
        enum role "admin/analyst/viewer"
    }

    Supplier {
        uuid id PK
        uuid org_id FK
        string name
        string country
        float emission_factor
        float esg_score "0-100"
        float lat
        float lng
    }

    EmissionRecord {
        uuid id PK
        uuid org_id FK
        uuid supplier_id FK
        int scope "1/2/3"
        string category
        float amount_tco2e
        date period_start
        date period_end
    }

    SupplyChainEdge {
        uuid id PK
        uuid org_id FK
        uuid from_supplier FK
        uuid to_supplier FK
        enum transport_mode "air/sea/road/rail"
        float distance_km
        float weight_tonnes
    }
```

---

## 🌍 Real-World Impact & Scalability

### Impact Metrics

| Metric | Value |
|:---|:---|
| **Target Users** | SMEs, mid-market enterprises, sustainability consultants |
| **Cost Reduction** | $0 vs $50K+/year enterprise alternatives |
| **Emission Scopes** | Full Scope 1 + 2 + 3 coverage |
| **Supported Standards** | GHG Protocol, DEFRA, EU CSRD, CBAM, SEC, BRSR, TCFD, SBTi |
| **Emission Factors** | 15+ verified factors (transport, energy, material) across 5+ countries |

### Scalability Architecture

| Component | Scaling Strategy |
|:---|:---|
| **Frontend** | Vercel Edge Network — global CDN, auto-scaling |
| **Backend** | Stateless FastAPI — horizontal pod scaling on any container platform |
| **Database** | Supabase PostgreSQL — connection pooling (10+20 overflow), async queries |
| **AI Layer** | Multi-provider failover (Groq → Anthropic → Mock) — 100% uptime |
| **Reports** | Async background workers — non-blocking PDF generation |
| **Auth** | JWT stateless tokens — no session storage bottleneck |

### Future Roadmap
- 🔄 **IoT Sensor Integration** — Real-time emission data from factory IoT devices
- 📊 **Advanced ML Forecasting** — Prophet/LSTM models per emission category
- 🌐 **Multi-org Benchmarking** — Compare your carbon intensity against industry peers
- 📱 **Mobile App** — React Native companion for on-the-go monitoring
- 🔗 **API Marketplace** — Third-party integrations (SAP, Oracle, ERP systems)
- 📜 **Regulatory Compliance Engine** — Auto-generate EU CSRD / SEC disclosure reports

---

## 📋 Environment Variables

```env
# Database (Required)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Security (Required)
SECRET_KEY=your-256-bit-secret-key

# AI Providers (Optional — mock fallback available)
GROQ_API_KEY=your-groq-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Deployment
ENVIRONMENT=development          # development | production
FRONTEND_URL=http://localhost:5173
SENTRY_DSN=your-sentry-dsn       # Optional
```

---

## 🤖 AI Tools Disclosure

> **Mandatory disclosure as per OSF HackOne 2K26 Rules (Section 3)**

| AI Tool | Usage Area | How It Was Used |
|:---|:---|:---|
| **Claude (Anthropic)** | Code Assistance | Used for code generation, debugging, architecture decisions, and README documentation. All AI-generated code was reviewed, understood, and modified by team members before integration. |
| **Gemini (Google)** | Code Assistance | Used as an AI coding assistant for development support, code suggestions, and project scaffolding. |

> ⚠️ **Disclaimer**: All AI-assisted code was thoroughly reviewed, tested, and validated by team members. The core logic, architecture design, and problem-solving approach are original work by Team Last Brain Cell. AI tools were used as productivity aids, not as a substitute for understanding.

---

## 🏆 Hackathon Submission — OSF HackOne 2K26

<div align="center">

| Criteria | Score | Our Approach |
|:---|:---:|:---|
| **Innovation & Originality** | /25 | OR-Tools LP optimization + multi-provider AI chain + supply chain graph intelligence — novel combination |
| **Technical Implementation** | /20 | Full-stack async architecture, 7 SQLAlchemy models, 25+ API endpoints, CI/CD, Docker, dual auth |
| **Problem-Solving Relevance** | /15 | Addresses $50K+ enterprise gap — free Scope 3 tracking for the 99% who can't afford SAP Sustainability |
| **Completeness of Build** | /15 | 8 pages, bulk import, PDF reports, AI chat, forecasting, optimization, role-based access, onboarding wizard |
| **UI/UX & Functionality** | /10 | Tailwind + shadcn/ui design system, dark mode, animated onboarding, interactive graph, toast notifications |
| **Presentation & Q&A** | /10 | Clean README, architecture diagrams, live deployed demo, comprehensive documentation |
| **Scalability & Impact** | /5 | Stateless backend, edge CDN, async workers, connection pooling, multi-provider failover, IoT-ready roadmap |

</div>

---

## 👥 Team Members & Roles

<div align="center">

### Team Last Brain Cell 🧠

| Member | Role | Responsibilities |
|:---|:---:|:---|
| **Rishi Sharma** | Full Stack Developer | Backend architecture, API design, AI/ML integration, DevOps, deployment |
| **Anshika Roy** | Full Stack Developer | Frontend development, UI/UX design, component architecture, testing |

[![GitHub](https://img.shields.io/badge/GitHub-stack--rishi-181717?style=for-the-badge&logo=github)](https://github.com/stack-rishi)

</div>

---

<div align="center">

**Built with 💚 for a sustainable future**

*CarbonLens — Because you can't reduce what you can't measure.*

</div>
