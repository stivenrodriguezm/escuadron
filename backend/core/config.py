"""Configuración global cargada desde variables de entorno / .env."""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


class ExecutionMode(str, Enum):
    PAPER_LIVE = "PAPER_LIVE"
    TESTNET = "TESTNET"
    LIVE = "LIVE"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    # LLM: proveedor y modelo por agente (01, 04 y 05 son deterministas por diseño)
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")  # gemini | anthropic
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")  # clave Anthropic
    llm_effort: str = Field(default="medium", alias="LLM_EFFORT")  # solo Anthropic
    strategist_model: str = Field(default="gemini-3.5-flash", alias="STRATEGIST_MODEL")
    strategist_fallback_models: list[str] = Field(
        default=["gemini-3-flash-preview", "gemini-3.5-flash-lite"], alias="STRATEGIST_FALLBACK_MODELS")
    sentiment_model: str = Field(default="gemini-3.5-flash-lite", alias="SENTIMENT_MODEL")
    sentiment_fallback_models: list[str] = Field(default=["gemini-3.5-flash"], alias="SENTIMENT_FALLBACK_MODELS")
    llm_timeout_s: float = Field(default=45.0, alias="LLM_TIMEOUT_S")
    binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", alias="BINANCE_API_SECRET")

    # Modo y capital
    execution_mode: ExecutionMode = Field(default=ExecutionMode.PAPER_LIVE, alias="EXECUTION_MODE")
    default_virtual_capital: float = Field(default=10_000.0, alias="DEFAULT_VIRTUAL_CAPITAL")

    # Riesgo
    max_risk_per_trade: float = Field(default=0.01, alias="MAX_RISK_PER_TRADE")
    max_daily_drawdown: float = Field(default=0.03, alias="MAX_DAILY_DRAWDOWN")
    max_portfolio_risk: float = Field(default=0.03, alias="MAX_PORTFOLIO_RISK")
    max_leverage: float = Field(default=3.0, alias="MAX_LEVERAGE")
    min_reward_risk: float = Field(default=2.0, alias="MIN_REWARD_RISK")
    min_notional_usdt: float = Field(default=5.0, alias="MIN_NOTIONAL_USDT")

    # Fricción (Binance USDⓈ-M Futures, nivel VIP0)
    taker_fee: float = Field(default=0.0005, alias="TAKER_FEE")
    maker_fee: float = Field(default=0.0002, alias="MAKER_FEE")
    latency_ms: float = Field(default=150.0, alias="LATENCY_MS")
    min_latency_slippage: float = Field(default=0.00002, alias="MIN_LATENCY_SLIPPAGE")

    # Mercado (los pares e intervalos operados se definen en backend/core/params.py)
    ws_base_url: str = Field(default="wss://fstream.binance.com", alias="BINANCE_WS_URL")
    rest_base_url: str = Field(default="https://fapi.binance.com", alias="BINANCE_REST_URL")

    # Agentes
    # 0 = desactivado: la calibración mostró que mover el stop a 1.5R corta las tendencias (Sección 8.3)
    breakeven_r: float = Field(default=0.0, alias="BREAKEVEN_R")
    sentiment_cache_minutes: int = Field(default=30, alias="SENTIMENT_CACHE_MINUTES")

    # Infraestructura
    database_url: str = Field(default=f"sqlite:///{DATA_DIR / 'ledger.db'}", alias="DATABASE_URL")
    watch_interval_ms: int = Field(default=500, alias="WATCH_INTERVAL_MS")
    api_port: int = Field(default=8000, alias="API_PORT")
    # Orígenes que pueden usar la API: Vite en desarrollo y el dashboard publicado en GitHub Pages
    cors_origins: list[str] = Field(default=["http://localhost:5173", "https://stivenrodriguezm.github.io"],
                                    alias="CORS_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
