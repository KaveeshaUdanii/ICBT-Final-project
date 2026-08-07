import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    PROJECT_NAME: str = "SupplyChain AI-Blockchain Platform"
    API_V1_PREFIX: str = "/api"

    # PostgreSQL by default (matches the project proposal's §8.1 tooling table). Override
    # with DATABASE_URL for a different host/user, or point it at a sqlite:/// URL for
    # quick local testing with zero setup.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://supplychain:supplychain@localhost:5432/supplychain"
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-9f8a7d6c5b4e3a2f1")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ]

    ML_MODELS_DIR: Path = BASE_DIR / "app" / "ml_models"
    HIGH_RISK_THRESHOLD: float = 80.0  # % risk score that triggers smart-contract auto-alert
    ANOMALY_CONTAMINATION: float = 0.07


settings = Settings()
settings.ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)
