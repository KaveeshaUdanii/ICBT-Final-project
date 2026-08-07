# SupplyChain AI — AI-Driven Blockchain System for Predictive Supply Chain Risk and Delay Management

A full-stack implementation of the final year project proposal *"AI-Driven Blockchain
System for Predictive Supply Chain Risk and Delay Management"* — a platform for Sri
Lankan apparel manufacturers (and beyond) that predicts supply chain delays and supplier
risk before they happen, explains every prediction in plain language, records every
critical action on a tamper-evident ledger, and automates responses through smart
contract rules.

## Contents

- [Architecture](#architecture)
- [User roles & role-based dashboards](#user-roles--role-based-dashboards)
- [The 15 modules](#the-15-modules-from-the-proposal)
- [Engineering notes & honest limitations](#engineering-notes--honest-limitations)
- [Quick start](#quick-start)
- [Demo accounts](#demo-accounts)
- [Project structure](#project-structure)
- [Testing](#testing)
- [API overview](#api-overview)

## Architecture

| Layer | Technology |
|---|---|
| Frontend | React 19 + TypeScript + Vite, Tailwind CSS v4 (glassmorphism design system), Recharts, Zustand, React Router |
| Backend | FastAPI (Python), SQLAlchemy 2.0, Pydantic v2, JWT auth (PyJWT + bcrypt) |
| Database | **PostgreSQL by default** (via `psycopg2`) — set `DATABASE_URL` to a SQLite URL instead for zero-setup local exploration |
| AI / ML | scikit-learn, XGBoost, a from-scratch LIME-style explainer, Faker + NumPy synthetic data generation |
| Blockchain | A custom permissioned, SHA-256 hash-chained ledger (see below) |

## User roles & role-based dashboards

The platform has four user roles, each with its own dashboard, navigation, and
backend data access — enforced server-side (not just hidden in the UI), because a
determined user could otherwise call the API directly.

| Role | Dashboard focus | Full access | Read-only / scoped | No access |
|---|---|---|---|---|
| **Admin** | Full system view, platform health, user management | Everything | — | — |
| **Supply Chain Manager** | Supplier risk, delay predictions, PO approvals | Suppliers, Raw Materials, Shipments, Purchase Orders, AI Risk Center, Recommendations, Blockchain Explorer, Audit Trail, Scenario Simulation | — | User Management |
| **Warehouse Manager** | Inventory, reorder alerts, demand & stockout forecasts | Raw Materials, Shipments (status updates) | Suppliers (view only, via API) | Purchase Orders, AI Risk Center, Recommendations, Blockchain, Audit Trail, Scenario Simulation, User Management |
| **Supplier** (external party) | Their own shipments & purchase orders only | — | Shipments & Purchase Orders **scoped to their own linked supplier record only** | Suppliers directory, Raw Materials, AI Risk Center, Recommendations, Blockchain, Audit Trail, Scenario Simulation, User Management |

The Supplier role is treated as an external party: every router that returns
supplier-linked data (`suppliers`, `shipments`, `purchase-orders`, `notifications`)
filters at the database-query level using the caller's `User.supplier_id` — a
supplier account can never see another supplier's shipments, POs, risk scores, or
the company-wide supplier directory, even by calling the API directly.

The proposal names Node.js/Express or FastAPI as acceptable backend choices; FastAPI was
used so the entire stack — API, ORM, and the AI Risk Prediction Engine — lives in one
Python codebase, which keeps the AI/ML pieces (the core of a data-science project)
first-class rather than bolted on as a separate microservice.

## The 15 modules (from the proposal)

| # | Module | Where it lives |
|---|---|---|
| 1 | User & Role Management | `app/routers/auth.py`, `app/routers/users.py`, RBAC in `app/core/deps.py` |
| 2 | Supplier Management | `app/routers/suppliers.py` — CRUD + risk scoring + blockchain records |
| 3 | Raw Material Management | `app/routers/raw_materials.py` — inventory, reorder alerts |
| 4 | Shipment Management | `app/routers/shipments.py` — tracking, delay prediction, blockchain logging |
| 5 | Purchase Order Management | `app/routers/purchase_orders.py` — approval workflow, AI risk evaluation |
| 6 | AI Risk Prediction Engine | `app/ai/` — Delay Prediction, Supplier Risk Scoring, Anomaly Detection, **Demand Forecasting**, **Stockout Risk** (5 models total) |
| 7 | Recommendation Engine | `app/services/recommendation_service.py` |
| 8 | Explainable AI (XAI) | `app/ai/explain.py` — custom LIME-style local surrogate explainer |
| 9 | Blockchain Trust Module | `app/services/blockchain_service.py` |
| 10 | Smart Contract Automation | `app/services/smart_contract_service.py` |
| 11 | Analytics & Dashboard | `app/routers/analytics.py` + `frontend/src/pages/dashboards/` (one dashboard per role) |
| 12 | Notification System | `app/routers/notifications.py`, in-app bell + `/notifications` page |
| 13 | Scenario Simulation | `app/services/scenario_service.py`, `/scenarios` page |
| 14 | Production Impact Analysis | `app/services/production_impact_service.py` |
| 15 | Blockchain Audit Trail | `app/routers/audit.py`, `/audit-trail` page |

## Engineering notes & honest limitations

Two components were deliberately re-engineered from the proposal's original tooling
choices, for reasons documented in-line in the code:

- **Blockchain layer.** Running a real Hyperledger Fabric network requires Docker,
  Go chaincode, and a multi-node permissioned setup that is out of scope for a
  single-developer academic project (the proposal itself acknowledges this under
  *"11.2 Blockchain Scalability"*). Instead, `app/services/blockchain_service.py`
  implements a lightweight permissioned ledger: every critical event (supplier
  scored, shipment delivered, PO approved, smart-contract rule fired...) is appended
  as an immutable block, SHA-256-linked to its predecessor. `verify_chain()`
  recomputes every hash and confirms the chain of `previous_hash` links, so any
  historical tampering with the database is instantly detectable — the same
  tamper-evidence property Hyperledger Fabric provides, without the infrastructure.
- **Explainable AI.** The `lime` PyPI package's legacy `setup.py` is incompatible
  with this environment's patched `distutils` and could not be installed. Rather
  than skip XAI, `app/ai/explain.py` implements the same methodology described in
  Ribeiro, Singh & Guestrin (2016) — the paper the proposal itself cites — from
  first principles: perturb the instance, query the real model, weight samples by
  proximity with an RBF kernel, fit a weighted Ridge surrogate, and read off each
  feature's local contribution.

Everything else — the five trained ML models, the 15 CRUD/business modules, the
smart contract rule engine, scenario simulation, and the full UI — is real, working
code, not a mock.

**Data**: real historical data from Sri Lankan apparel exporters is confidential and
unavailable to a student project (acknowledged in the proposal, section 11.1).
`app/ai/data_generation.py` generates a realistic synthetic dataset instead: supplier
metrics are sampled from distributions calibrated to the industry figures in the
proposal's literature review, and shipment delays/anomalies are produced by a
documented generative process with noise — so the models have genuine, learnable
signal rather than a memorizable formula. Current out-of-sample performance (see the
AI Risk Center page or `GET /api/ai/model-performance`):

| Model | Algorithm | Metric |
|---|---|---|
| Supplier Risk Scoring | Logistic Regression + Random Forest ensemble | ~81% accuracy / 0.90 ROC-AUC |
| Delay Prediction | XGBoost | ~81-84% accuracy / 0.89 F1 |
| Anomaly Detection | Isolation Forest (unsupervised) | evaluated against injected anomalies for validation only |
| **Demand Forecasting** *(added beyond the proposal's 3 required models)* | Gradient Boosting Regressor | MAE ≈ 27 units (22.6% of mean demand) |
| **Stockout Risk** *(added beyond the proposal's 3 required models)* | Gradient Boosting Classifier | ~90.5% accuracy / 0.90 ROC-AUC |

The Demand Forecasting and Stockout Risk models form a small stacked pipeline: the
Stockout Risk classifier consumes the Demand Forecasting model's own prediction as one
of its input features, then answers a materially different question ("will this
specific material run out in the next replenishment cycle, given its lead time and
supplier reliability?") — they power the Warehouse Manager dashboard's proactive
reorder planning.

## Quick start

Requires Python 3.11+, Node.js 20+, and a running PostgreSQL server (or use the SQLite
fallback below for zero-setup local exploration).

### 1. Database

```bash
# Create the database (adjust user/password to taste, or reuse an existing role)
createdb supplychain
# or: psql -c "CREATE DATABASE supplychain;"
```

Set `DATABASE_URL` in `backend/.env` (copy `backend/.env.example`) to point at it, e.g.
`postgresql+psycopg2://supplychain:supplychain@localhost:5432/supplychain`. No local
Postgres available? Set `DATABASE_URL=sqlite:///./supplychain.db` instead — every model
uses `native_enum=False` specifically so the schema is portable between the two with no
migration step.

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python3 seed.py          # populates demo suppliers, materials, shipments, POs, users
uvicorn app.main:app --reload --port 8000
```

The first server startup automatically trains the five ML models (a few seconds) if
`app/ml_models/*.joblib` don't exist yet — no separate training step is required. To
retrain manually: `python3 -m app.ai.train`.

API docs (Swagger UI) are then available at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to
`http://127.0.0.1:8000`, so no CORS configuration is needed locally.

### 4. Log in

Use one of the [demo accounts](#demo-accounts) below, or register a new account from
the login screen. Each role lands on a different dashboard (see
[User roles & role-based dashboards](#user-roles--role-based-dashboards)).

## Demo accounts

Created by `python3 seed.py`:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@supplychain.ai` | `admin123` |
| Supply Chain Manager | `manager@supplychain.ai` | `manager123` |
| Warehouse Manager | `warehouse@supplychain.ai` | `warehouse123` |
| Supplier (external portal) | `supplier@supplychain.ai` | `supplier123` |

The Supplier account is linked to one specific supplier record (Colombo Textile
Mills) so its scoped views have real data to show.

## Project structure

```
backend/
  app/
    core/          # config, database session, JWT security, RBAC dependencies
    models/         # SQLAlchemy models (one file per entity)
    schemas/        # Pydantic request/response schemas
    routers/        # FastAPI routers — one per module
    services/       # blockchain, smart contracts, notifications, recommendations,
                     # production impact, scenario simulation
    ai/             # feature engineering, synthetic data, training, inference, XAI
    ml_models/       # trained model artifacts (generated, gitignored)
  seed.py            # demo dataset generator
  tests/             # pytest suite (auth, CRUD, blockchain integrity, AI)
frontend/
  src/
    api/            # axios client + typed endpoint functions
    store/          # zustand auth & theme stores
    components/     # layout (sidebar/topbar, role-filtered nav) + reusable glass UI
                     # primitives + shared dashboard chart components
    pages/
      dashboards/    # one dashboard component per role (Admin/Manager/Warehouse/Supplier)
                     # module pages (Suppliers, Shipments, AI Risk Center, etc.)
    types/          # TypeScript types mirroring the backend schemas
```

## Testing

```bash
cd backend
pytest tests/ -v
```

17 tests cover authentication & RBAC, supplier/raw-material CRUD, blockchain hash-chain
integrity (including a test that tampers with a block and asserts detection), AI
scoring/prediction/explanation shape, and scenario simulation.

## API overview

All endpoints are under `/api` and (except `/api/auth/*`) require a `Bearer` JWT
obtained from `POST /api/auth/login`. Interactive documentation: `/docs`.

Key endpoint groups: `/api/auth`, `/api/users`, `/api/suppliers`, `/api/raw-materials`,
`/api/shipments`, `/api/purchase-orders`, `/api/ai/*` (scoring, prediction, model
performance), `/api/recommendations`, `/api/blockchain/*`, `/api/audit-logs`,
`/api/notifications`, `/api/scenarios`, `/api/analytics/*`.
