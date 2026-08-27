"""
app/config.py — Centralised configuration management.

All settings are loaded from environment variables (or a .env file).
Pydantic-settings validates and coerces types at startup.
"""
from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Any, List, Optional

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----------------------------------------------------------
    # Application
    # ----------------------------------------------------------
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    PROJECT_NAME: str = "Tourist Safety Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "http://localhost:5173", "http://127.0.0.1:5173"]

    # ----------------------------------------------------------
    # Database — PostgreSQL
    # ----------------------------------------------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "tourist_safety"
    POSTGRES_USER: str = "tourist_user"
    POSTGRES_PASSWORD: str = ""

    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""

    @model_validator(mode="after")
    def build_database_urls(self) -> "Settings":
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if not self.DATABASE_URL_SYNC:
            self.DATABASE_URL_SYNC = (
                f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ----------------------------------------------------------
    # JWT Authentication
    # ----------------------------------------------------------
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ----------------------------------------------------------
    # Encryption
    # ----------------------------------------------------------
    ENCRYPTION_KEY: Optional[str] = None  # Fernet base64 key

    # ----------------------------------------------------------
    # OpenWeatherMap
    # ----------------------------------------------------------
    OPENWEATHER_API_KEY: Optional[str] = None
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5"
    WEATHER_MOCK_MODE: bool = False
    WEATHER_REQUEST_TIMEOUT: int = 10
    WEATHER_MAX_RETRIES: int = 3

    # ----------------------------------------------------------
    # SMS Provider
    # ----------------------------------------------------------
    SMS_PROVIDER: str = "twilio"
    SMS_ACCOUNT_SID: Optional[str] = None
    SMS_AUTH_TOKEN: Optional[str] = None
    SMS_FROM_NUMBER: Optional[str] = None
    SMS_MOCK_MODE: bool = False
    SMS_REQUEST_TIMEOUT: int = 15
    SMS_MAX_RETRIES: int = 3

    # ----------------------------------------------------------
    # Internet Alert Provider
    # ----------------------------------------------------------
    ALERT_PROVIDER_URL: Optional[str] = None
    ALERT_PROVIDER_API_KEY: Optional[str] = None
    ALERT_MOCK_MODE: bool = False
    ALERT_REQUEST_TIMEOUT: int = 10
    ALERT_MAX_RETRIES: int = 3

    # ----------------------------------------------------------
    # Blockchain
    # ----------------------------------------------------------
    BLOCKCHAIN_PROVIDER_URL: str = "http://localhost:8545"
    BLOCKCHAIN_CHAIN_ID: int = 1337
    BLOCKCHAIN_PRIVATE_KEY: Optional[str] = None
    BLOCKCHAIN_CONTRACT_ADDRESS: Optional[str] = None
    BLOCKCHAIN_MOCK_MODE: bool = False
    BLOCKCHAIN_GAS_LIMIT: int = 300_000

    # ----------------------------------------------------------
    # GPS Anomaly Detection
    # ----------------------------------------------------------
    GPS_MOVEMENT_THRESHOLD_METERS: float = 50.0
    GPS_CHECK_INTERVAL_MINUTES: int = 10
    GPS_ANOMALY_LIMIT: int = 3
    GPS_ROUTE_DEVIATION_THRESHOLD_METERS: float = 200.0
    GPS_MAX_CONSECUTIVE_DEVIATIONS: int = 3

    # ----------------------------------------------------------
    # Environmental Risk Weights
    # ----------------------------------------------------------
    RISK_WEIGHT_WEATHER: float = 0.30
    RISK_WEIGHT_NEWS: float = 0.40
    RISK_WEIGHT_HISTORICAL: float = 0.30

    RISK_LEVEL_LOW_MAX: float = 3.0
    RISK_LEVEL_MEDIUM_MAX: float = 6.0
    RISK_LEVEL_HIGH_MAX: float = 8.0
    # Above HIGH_MAX → CRITICAL

    # ----------------------------------------------------------
    # Adaptive AI Threshold
    # ----------------------------------------------------------
    ADAPTIVE_THRESHOLD_MIN: float = 0.30
    ADAPTIVE_THRESHOLD_MAX: float = 0.90
    ADAPTIVE_THRESHOLD_BASE: float = 0.70

    # ----------------------------------------------------------
    # Audio Classification
    # ----------------------------------------------------------
    AUDIO_MODEL_PATH: str = "models/audio/mobilenetv2_distress.pt"
    AUDIO_SAMPLE_RATE: int = 22050
    AUDIO_DURATION_SECONDS: int = 3
    AUDIO_N_MELS: int = 128
    AUDIO_HOP_LENGTH: int = 512
    AUDIO_N_FFT: int = 2048
    AUDIO_MOCK_MODE: bool = False

    # ----------------------------------------------------------
    # Background Workers (APScheduler)
    # ----------------------------------------------------------
    WEATHER_UPDATE_INTERVAL_MINUTES: int = 30
    NEWS_UPDATE_INTERVAL_MINUTES: int = 15
    RISK_RECALC_INTERVAL_MINUTES: int = 30
    MESH_RETRY_INTERVAL_MINUTES: int = 5
    CLEANUP_INTERVAL_HOURS: int = 6

    # ----------------------------------------------------------
    # Rate Limiting
    # ----------------------------------------------------------
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_SOS_PER_MINUTE: int = 10

    # ----------------------------------------------------------
    # Logging
    # ----------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" | "text"

    # ----------------------------------------------------------
    # Research
    # ----------------------------------------------------------
    RESEARCH_RESULTS_DIR: str = "tests/results"
    RESEARCH_PLOTS_DIR: str = "research/plots"
    RESEARCH_TABLES_DIR: str = "research/tables"
    EXPERIMENTS_CONFIGS_DIR: str = "experiments/configs"

    @field_validator("RISK_WEIGHT_WEATHER", "RISK_WEIGHT_NEWS", "RISK_WEIGHT_HISTORICAL")
    @classmethod
    def validate_weights_positive(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("Risk weights must be between 0 and 1")
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


# Convenience singleton used throughout the app
settings = get_settings()
