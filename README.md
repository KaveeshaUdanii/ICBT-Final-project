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
- [Data science pipeline: raw data, notebooks, models](#data-science-pipeline-raw-data-notebooks-models)
- [CSV bulk import](#csv-bulk-import)
- [Further AI & blockchain enhancements](#further-ai--blockchain-enhancements-beyond-the-original-proposal)
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
| **Supplier** (external party) | A real self-service portal: accept/decline POs, ship & confirm delivery, message procurement, manage their own profile | — | Shipments & Purchase Orders **scoped to their own linked supplier record only** | Suppliers directory, Raw Materials, AI Risk Center, Recommendations, Blockchain, Audit Trail, Scenario Simulation, User Management |

The Supplier role is treated as an external party: every router that returns
supplier-linked data (`suppliers`, `shipments`, `purchase-orders`, `notifications`)
filters at the database-query level using the caller's `User.supplier_id` — a
supplier account can never see another supplier's shipments, POs, risk scores, or
the company-wide supplier directory, even by calling the API directly.

Row-level scoping alone isn't enough for the Supplier role, though: even *within*
their own shipments and purchase orders, some fields are the company's internal
judgment about that very supplier, not something to hand back to them. `ShipmentRead`,
`PurchaseOrderRead`, and `SupplierRead` each have a matching `*ExternalRead` schema
(`app/schemas/shipment.py`, `purchase_order.py`, `supplier.py`) that a Supplier caller
is served instead, field-for-field, at the router layer — dropped, not just hidden in
the UI:
- Shipments: `predicted_delay_days`, `delay_probability` (Delay Prediction Model output),
  `is_anomaly`, `anomaly_score` (Anomaly Detection Model output).
- Purchase Orders: `risk_flag`, `risk_notes` (the smart-contract engine's auto-flagging
  notes, which can literally read *"supplier 'X' is HIGH risk (score Y%)"*), `approved_by`.
- Suppliers: `risk_score`, `risk_level`, `last_scored_at` (the AI Risk Prediction Engine's
  classification of them). Their own performance metrics (on-time delivery rate, defect
  rate, etc.) are kept — that's a factual record of their own transaction history, not an
  internal judgment.

In exchange, the Supplier Portal dashboard (`GET /api/analytics/my-dashboard`) surfaces
genuinely useful, non-leaking features built for an external party: a vendor-scorecard
style partnership snapshot (their own on-time rate, defect rate, cancellation rate, lead
time, order volume, total PO value), an upcoming-shipments list, and a recent-purchase-orders
list — all scoped to their own linked supplier record, none of it the AI's internal risk
scoring. It goes well beyond a read-only viewer:

- **PO acceptance workflow** — `POST /api/purchase-orders/{id}/respond` lets the supplier
  accept or decline a PO (with a required reason on decline), logged to the blockchain and
  notified to procurement, instead of a PO just silently appearing.
- **Supplier-side shipment updates** — `POST /api/shipments/{id}/ship` lets the supplier mark
  their own shipment in transit and attach carrier/tracking info; internal staff still confirms
  delivery on receipt. `POST /api/shipments/{id}/confirm-delivery` implements **multi-party
  delivery confirmation**: both the supplier and staff must independently confirm before a
  shipment auto-flips to `delivered` (two boolean+timestamp fields on the `Shipment` model). A
  staff override that sets `delivered` without the supplier's confirmation is still permitted,
  but is logged as a *distinct*, differently-named blockchain event
  (`shipment.delivered_without_supplier_confirmation`) so it stays auditable rather than
  indistinguishable from a normal two-party confirmation.
- **Per-PO/shipment message thread** — `app/routers/messages.py`, a lightweight comment thread
  scoped to one PO or shipment, so a delay or question is logged in-app instead of over email,
  directly targeting the "communication breakdowns between suppliers and merchandisers" problem
  the proposal's own literature review cites.
- **Document upload with blockchain hash anchoring** — `app/routers/documents.py` /
  `app/services/document_service.py`: a supplier or staff member uploads a compliance
  certificate, spec sheet, or invoice; its SHA-256 hash is computed and appended to the
  blockchain ledger (`document.uploaded`). `GET /api/documents/{id}/verify` recomputes the hash
  from the file currently on disk and compares it against the anchored value, so a disputed
  paper/PDF document can be cryptographically verified against history — closing the "difficult
  to verify facts" gap the proposal identifies.
- **Editable company profile** — `PATCH /api/suppliers/me/profile` lets the supplier maintain
  their own contact email/phone, rather than requiring an admin to do it for them.
- **Own performance trend** — `performance_trend` in the dashboard payload: on-time delivery
  rate and average delay, grouped by month, computed purely from the supplier's own delivered
  shipment history (never the AI's internal `risk_score`/`risk_level`) — the same "monitor
  reliability over time" gap the proposal identifies, answered from the supplier's own side.
- **Aggregated forward demand** — `materials_demand_forecast` in the dashboard payload:
  "expected order volume, next 30 days," derived from the Demand Forecasting model for
  materials linked to that supplier only — without exposing the full Raw Materials catalog,
  stock levels, or reorder thresholds.
- **Export own history** — client-side CSV download of the supplier's own shipments/purchase
  orders (mirrors the CSV import feature already built for staff, see below).
- **Local chatbot** — a floating assistant available on every supplier-portal page
  (`app/ai/chatbot.py`, `POST /api/chatbot/message`), answering shipment/PO status and
  performance questions from the caller's own scoped data. No external API — see the
  [models table](#engineering-notes--honest-limitations) below for how it's trained.

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
| 6 | AI Risk Prediction Engine | `app/ai/` — Delay Prediction, Supplier Risk Scoring, Anomaly Detection, **Demand Forecasting**, **Stockout Risk**, plus a **Data-Entry Anomaly Check** (statistics-based, catches implausible quantity/price entries at PO/shipment creation time — see below) and the **Supplier Portal Chatbot** (6th trained model) |
| 7 | Recommendation Engine | `app/services/recommendation_service.py` |
| 8 | Explainable AI (XAI) | `app/ai/explain.py` — custom LIME-style local surrogate explainer |
| 9 | Blockchain Trust Module | `app/services/blockchain_service.py` |
| 10 | Smart Contract Automation | `app/services/smart_contract_service.py` |
| 11 | Analytics & Dashboard | `app/routers/analytics.py` + `frontend/src/pages/dashboards/` (one dashboard per role) |
| 12 | Notification System | `app/routers/notifications.py`, in-app bell + `/notifications` page |
| 13 | Scenario Simulation | `app/services/scenario_service.py`, `/scenarios` page |
| 14 | Production Impact Analysis | `app/services/production_impact_service.py` |
| 15 | Blockchain Audit Trail | `app/routers/audit.py`, `/audit-trail` page |

## Data science pipeline: raw data, notebooks, models

Genuine, company-collected supply chain data is confidential and was never available for this
student project (also true of the original synthetic-data approach, see the honest limitations
below). To give the preprocessing/EDA/modeling work real substance instead of hiding it inside a
single script, the pipeline is now a proper three-stage one, all under `backend/ml_pipeline/`:

1. **Raw, deliberately messy data** (`ml_pipeline/build_source_datasets.py`,
   `ml_pipeline/data_quality_simulator.py`) — builds on the same underlying generative logic in
   `app/ai/data_generation.py` (so the learnable signal is genuine, not random noise) and then
   engineers realistic ERP-export mess on top: missing values, exact/near-duplicate rows,
   inconsistent country/category text (case, whitespace, typos, abbreviations), numbers stored as
   formatted strings (currency symbols, thousands separators, percentages), domain-rule outliers
   (negative quantities, out-of-range rates), and — in the shipment logistics file — **five
   different mixed date formats** in the same column. Output:
   `ml_pipeline/data/raw/{supplier_performance_records,shipment_logistics_records,inventory_demand_records}.csv`,
   roughly 1,000 + 60,000 + 45,000 rows.
2. **Three executed Jupyter notebooks** (`ml_pipeline/notebooks/`) — one per dataset, each doing
   real, substantial cleaning (missing-value audits with an informed imputation strategy per
   column, duplicate detection, a structural-pattern date parser rather than a blind
   `pd.to_datetime(..., format="mixed")` guess, domain-rule outlier correction), saving a cleaned
   CSV to `ml_pipeline/data/processed/`, an **advanced feature validation pass** on every feature
   list used for training (a correlation/multicollinearity matrix, mutual information scoring as a
   non-linear-relationship-aware complement to Pearson correlation, and a 5-fold cross-validated
   ablation test that empirically checks whether dropping the weakest-scoring feature actually
   costs held-out performance), then EDA driven by specific supply-chain-risk questions (not
   undirected plotting) with a "Finding" and "So what" after every chart, then training the same
   models the live app uses. The EDA is intentionally reported honestly, including a case where the
   new ML demand forecast **did not beat** the company's existing manual forecast baseline on
   held-out data — with a diagnosed reason and a concrete next step, not adjusted until it looked
   better.
3. **Algorithm benchmarking, cross-validation, and interactive interpretability** — every
   supervised target (Supplier Risk, Delay Prediction classifier + regressor, Demand Forecasting,
   Stockout Risk) is benchmarked with 5-fold cross-validation (`StratifiedKFold` for
   classification, `KFold` for regression) against XGBoost, LightGBM, CatBoost, and Random Forest,
   reporting mean ± std per algorithm rather than a single train/test split — plus a before/after
   comparison of balanced sample weighting (`compute_sample_weight`) on whichever target is most
   class-imbalanced. Reported honestly: across all five targets, no challenger beat the existing
   baseline by more than a pre-registered 1-point F1 / 3%-MAE margin **on which algorithm to use**
   — see each notebook's "Algorithm choice" note in its Conclusion for the exact numbers. Every
   benchmark comparison is also backed by a **Wilcoxon signed-rank significance test** on the
   paired per-fold scores (is the gap real or fold noise?) and a genuine **`GridSearchCV`
   hyperparameter-tuning pass** on the winning algorithm (is the *tuning*, not just the algorithm
   choice, already close to optimal?) — one tuning pass *did* find a meaningful, adopted
   improvement: Demand Forecasting's Gradient Boosting Regressor now runs with
   `GridSearchCV`-found hyperparameters in `app/ai/train.py`, a genuine ~13% MAE reduction. A
   **time-based validation split** (train on early months, test on the most recent ones) checks
   each seasonal model's random-CV numbers against a stricter, forward-looking robustness test.
   Each notebook also renders an **interactive Plotly LIME waterfall** for one real held-out
   prediction, calling the live app's own from-scratch LIME implementation (`app/ai/explain.py`)
   directly, so the same case-specific "why was this flagged?" explanation the AI Risk Center UI
   shows is also reproducible and inspectable natively in Python.
4. **Techniques beyond supervised classification/regression** — the notebooks also demonstrate:
   **K-Means supplier segmentation** (`01_suppliers_...ipynb`, Section 9g) — unsupervised
   clustering on raw supplier metrics, silhouette-selected `k`, profiled into procurement
   archetypes (e.g. "high-volume-but-unstable" vs. "small-but-reliable") independent of the
   supervised risk label; a **subgroup error audit** in all three notebooks checking whether each
   model's accuracy/error is stable across supplier country, category, or material category, not
   just its headline metric; and a classical **`statsmodels` seasonal decomposition** (trend /
   seasonal / residual) plus a **SARIMA** aggregate-demand forecast in the materials notebook,
   confirming the Aug-Dec seasonal pattern structurally rather than only through a tabular
   feature's importance score.
5. **A standalone interactive model dashboard** (`ml_pipeline/model_dashboard.py`) — a lightweight
   Streamlit app (`streamlit run model_dashboard.py` from `ml_pipeline/`) that reuses the live
   app's own trained models and LIME implementation directly: pick any real supplier, shipment, or
   material from the seeded database and see its live risk/delay/stockout prediction and LIME
   waterfall rendered on demand, alongside each model's benchmark context from the notebooks —
   the interactive, point-at-any-record view the fixed notebook examples don't provide on their
   own.
6. **The live app trains from the cleaned output** — `app/ai/train.py` reads
   `ml_pipeline/data/processed/*.csv` (not a second, independently-generated copy), so the model
   serving predictions in the running app is provably trained on the exact dataset the notebooks
   document and analyze. Feature engineering is shared code (`app/ai/features.py`), imported
   directly into the notebooks too, guaranteeing the notebook's features and the live app's
   features can never silently drift apart.

Reopen/rerun the notebooks locally with `pip install -r ml_pipeline/requirements.txt` (adds
Jupyter, matplotlib, seaborn, lightgbm, catboost, plotly, statsmodels, and streamlit on top of
the main `requirements.txt` — none of these are needed to run the live app, only to rerun the
notebooks' benchmarking/interpretability/time-series sections or the standalone dashboard), then
`jupyter notebook ml_pipeline/notebooks/` (or `streamlit run ml_pipeline/model_dashboard.py` for
the interactive dashboard). The processed CSVs and trained notebook-local models are committed
to the repo, so none of this is required just to run the app — `python -m app.ai.train` already
works against the committed processed data.

## CSV bulk import

Most real ERP systems bring data in via a file upload, not one row at a time through a form. Every
core entity supports it: `POST /api/{suppliers,raw-materials,shipments,purchase-orders}/import-csv`
(multipart file upload, same permission as that entity's own "create"). Each row is validated
against the same Pydantic schema the manual-entry form uses and imported inside its own database
SAVEPOINT, so one malformed row is reported and skipped without discarding the rows around it —
the response is `{imported, failed, errors: [{row, error}]}`. Raw Materials, Shipments, and
Purchase Orders accept either the numeric `*_id` column or a human-friendly `*_name` column
(e.g. `supplier_name`, `raw_material_name`), resolved by exact match, since that's what a person
filling in a spreadsheet by hand actually has on hand. One summary block is written to the
blockchain ledger per import batch (not one per row) to avoid ledger bloat; Purchase Orders still
get the same high-risk-supplier auto-flag and manager notification a manually created PO would.
In the UI, an **Import CSV** button next to "Add ..." on each management page opens a modal with a
downloadable sample template and a post-import results summary.

## Further AI & blockchain enhancements beyond the original proposal

- **Data-entry anomaly check at input time** (`app/ai/data_entry_check.py`) — a lightweight,
  statistics-based check (not a trained model — there isn't enough per-supplier history yet for
  one to learn from) that flags a new PO or shipment as unusual *before* it's committed: a
  z-score check against the entering supplier's own history, falling back to the material
  category's history, then the whole dataset's, whichever tier first has enough samples (≥5) to
  be statistically meaningful. This is the direct fix for the proposal's human-error problem
  (wrong quantity, implausible unit price) — distinct from the existing Anomaly Detection model,
  which only scores a shipment's delay risk *after* the fact. A flagged PO/shipment sets
  `data_entry_flag`/`data_entry_warning` and notifies the creator, but is not blocked — it's a
  warning, not a hard stop.
- **Supplier risk history & trend** (`GET /api/suppliers/{id}/risk-history`) — every AI scoring
  run was already being persisted as a `RiskPrediction` row; this endpoint surfaces that history
  as a queryable trend so a manager can see a supplier's risk drifting upward over time, not just
  its latest snapshot — directly targeting the proposal's "lack a structured system to monitor
  reliability over time" gap.
- **Risk-aware alternate-supplier suggestion** — `recommend_alternative_suppliers()`
  (`app/services/recommendation_service.py`) was already wired into the AI scoring flow for
  HIGH-risk suppliers; it now orders candidates to prefer a same-country backup first (shorter
  logistics disruption) before falling back to the lowest-risk match regardless of country.
- **On-chain SLA / penalty terms** — `app/services/smart_contract_service.py:compute_penalty_exposure()`
  computes `penalty_exposure = po.total_value × (penalty_rate_pct / 100) × days_late` against a
  per-PO `penalty_rate_pct` set at creation, both proactively (when predicted delay risk is high)
  and reactively (on an actually-late delivery), logs the computation to the blockchain, and
  raises a warning notification — closer to what "smart contract" means in the literature the
  proposal cites than pure event-logging alone.
- **Change-notification log** — `app/services/change_log_service.py` diffs a tracked set of
  fields (quantity, expected delivery date, unit price) on every PO/shipment update, logs the
  before/after values to the blockchain audit trail, and raises a targeted notification to
  whichever side (supplier or staff) didn't make the change — directly targeting the proposal's
  citation that late change notifications cause line stoppages.
- **Search** on the Raw Materials, Shipments, and Purchase Orders management pages — client-side
  filtering by code/name/supplier/status, since browsing a long unfiltered table doesn't scale.

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

Everything else — the six trained AI/ML models, the 15 CRUD/business modules, the
smart contract rule engine, scenario simulation, and the full UI — is real, working
code, not a mock.

**Data**: real historical data from Sri Lankan apparel exporters is confidential and
unavailable to a student project (acknowledged in the proposal, section 11.1). Supplier
metrics are sampled from distributions calibrated to the industry figures in the
proposal's literature review, and shipment delays/anomalies are produced by a
documented generative process with noise — so the models have genuine, learnable
signal rather than a memorizable formula. See
[Data science pipeline](#data-science-pipeline-raw-data-notebooks-models) above for how
this raw signal is turned into large, deliberately messy CSVs and then cleaned, analyzed,
and modeled through real notebooks rather than trained on directly. Current out-of-sample
performance (see the AI Risk Center page or `GET /api/ai/model-performance`):

| Model | Algorithm | Metric |
|---|---|---|
| Supplier Risk Scoring | Logistic Regression + Random Forest ensemble | ~82% accuracy / 0.87 ROC-AUC |
| Delay Prediction | XGBoost | ~84% accuracy / 0.91 F1 |
| Anomaly Detection | Isolation Forest (unsupervised) | evaluated against injected anomalies for validation only |
| **Demand Forecasting** *(added beyond the proposal's 3 required models)* | Gradient Boosting Regressor (`GridSearchCV`-tuned) | MAE ≈ 26.3 units (22.6% of mean demand) — tuned hyperparameters found in the notebook's benchmarking section, a ~13% error reduction over the untuned defaults; see the notebook's honest comparison against the existing manual forecast below |
| **Stockout Risk** *(added beyond the proposal's 3 required models)* | Gradient Boosting Classifier | ~91% accuracy / 0.89 ROC-AUC |
| **Supplier Portal Chatbot** *(6th model, local — no external API)* | TF-IDF (1-2 grams) + Logistic Regression intent classifier | ~100% accuracy on its own held-out examples |

(Exact figures shift slightly each time `python -m app.ai.train` is rerun against the same
committed processed data, since train/test splits are randomized; see
`app/ml_models/training_report.json` for the numbers from the most recent run.)

**Honest caveat on the chatbot**: it is trained on a small, hand-written set of ~50 example
phrases across 7 intents (`app/ai/chatbot.py`), not a general-purpose language model — its
~100% accuracy reflects how clean-cut that small training set is, not real-world robustness to
arbitrary phrasing. A confidence threshold (0.25) makes it fall back to an honest "I'm not sure
how to help with that" rather than guessing on an out-of-distribution question, and it only ever
answers from the caller's own scoped data (shipment/PO status, pending orders, performance) —
it cannot access anything a Supplier account couldn't already see through the rest of the portal.

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
| Admin | `admin@gmail.com` | `admin123` |
| Supply Chain Manager | `manager@gmail.com` | `manager123` |
| Warehouse Manager | `warehouse@gmail.com` | `warehouse123` |
| Supplier (external portal) | `supplier@gmail.com` | `supplier123` |

The Supplier account is linked to one specific supplier record (Colombo Textile
Mills) so its scoped views have real data to show.

### Onboarding a new Supplier portal account

A **Supplier record** (company name, contact info, performance metrics — managed under
Supplier Management) and a **Supplier-portal login** (an account with role `supplier`) are
two different things, created two different ways:

1. An Admin or Supply Chain Manager creates the company record first, via
   **Suppliers > Add Supplier**.
2. The portal login is created either by that person registering their own account from the
   **Sign In > Create account** screen (choosing role "Supplier"), or by an Admin creating it
   directly.
3. **An Admin then links the two** under **User Management**, using the "Linked Supplier"
   dropdown next to that account — this is what makes the account's shipments/purchase
   orders/dashboard show real, scoped data instead of "no supplier profile linked".

Registering with role "Supplier" on its own does **not** create a company record or
automatically show up anywhere in the Suppliers directory — it only creates the login. If a
new Supplier account's data isn't showing up anywhere, step 3 above (the linking) is almost
always the missing piece.

## Project structure

```
backend/
  app/
    core/          # config, database session, JWT security, RBAC dependencies
    models/         # SQLAlchemy models (one file per entity)
    schemas/        # Pydantic request/response schemas
    routers/        # FastAPI routers — one per module (incl. messages, documents, chatbot)
    services/       # blockchain, smart contracts, notifications, recommendations,
                     # production impact, scenario simulation, change-log, documents
    ai/             # feature engineering, synthetic data, training, inference, XAI,
                     # data-entry anomaly check, local chatbot intent classifier
    ml_models/       # trained model artifacts (generated, gitignored)
  ml_pipeline/
    build_source_datasets.py, data_quality_simulator.py   # large, deliberately messy raw CSV builder
    data/raw/            # raw source CSVs (committed)
    data/processed/       # notebook-cleaned CSVs app/ai/train.py trains from (committed)
    notebooks/            # 3 executed preprocessing/EDA/modeling notebooks + their own models/
  seed.py            # demo dataset generator
  tests/             # pytest suite (auth, CRUD, blockchain integrity, AI, CSV import)
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

20 tests cover authentication & RBAC, supplier/raw-material CRUD, blockchain hash-chain
integrity (including a test that tampers with a block and asserts detection), AI
scoring/prediction/explanation shape, scenario simulation, and CSV bulk import (successful
import, partial-failure row isolation, RBAC rejection, name-to-id resolution).

## API overview

All endpoints are under `/api` and (except `/api/auth/*`) require a `Bearer` JWT
obtained from `POST /api/auth/login`. Interactive documentation: `/docs`.

Key endpoint groups: `/api/auth`, `/api/users`, `/api/suppliers` (incl. `/{id}/risk-history`,
`/me/profile`), `/api/raw-materials`, `/api/shipments` (incl. `/{id}/ship`,
`/{id}/confirm-delivery`), `/api/purchase-orders` (incl. `/{id}/respond`) — each of the four
core entities also has a `/import-csv` bulk-import variant, see
[CSV bulk import](#csv-bulk-import) — `/api/ai/*` (scoring, prediction, model performance),
`/api/recommendations`, `/api/blockchain/*`, `/api/audit-logs`, `/api/notifications`,
`/api/scenarios`, `/api/analytics/*` (incl. `/my-dashboard` for the Supplier Portal),
`/api/messages`, `/api/documents` (incl. `/{id}/verify`, `/{id}/download`), and
`/api/chatbot/message`.
