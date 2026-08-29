from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai import predict as ai_predict
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models import *  # noqa: F401,F403  (registers all models on Base.metadata)
from app.routers import (
    ai_risk,
    analytics,
    audit,
    auth,
    blockchain,
    chatbot,
    documents,
    messages,
    notifications,
    purchase_orders,
    raw_materials,
    recommendations,
    scenarios,
    shipments,
    suppliers,
    users,
)
from app.services.smart_contract_service import ensure_rules_seeded


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        ensure_rules_seeded(db)
    finally:
        db.close()

    if not ai_predict.models_are_trained():
        from app.ai.train import main as train_models

        train_models()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Driven Blockchain System for Predictive Supply Chain Risk and Delay Management",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    users.router,
    suppliers.router,
    raw_materials.router,
    shipments.router,
    purchase_orders.router,
    ai_risk.router,
    recommendations.router,
    blockchain.router,
    audit.router,
    notifications.router,
    scenarios.router,
    analytics.router,
    messages.router,
    documents.router,
    chatbot.router,
):
    app.include_router(router)


@app.get("/api/health", tags=["System"])
def health():
    return {"status": "ok", "project": settings.PROJECT_NAME, "models_trained": ai_predict.models_are_trained()}
