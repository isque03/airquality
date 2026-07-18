import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _optional_float(value: str | None) -> float | None:
    return float(value) if value and value.strip() else None


def _color_enabled() -> bool:
    if os.getenv("NO_COLOR") is not None:
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


@dataclass(frozen=True)
class Config:
    latitude: float
    longitude: float
    zip_code: str
    radius_km: int
    poll_interval_seconds: float
    request_timeout_seconds: float
    provider_timeout_seconds: float
    max_retries: int
    retry_base_seconds: float
    history_hours: float
    plot_width: int
    plot_height: int
    database_path: str
    alert_threshold: float | None
    alert_cooldown_seconds: float
    color_enabled: bool
    color_theme: str
    default_metric: str
    airnow_key: str
    openaq_key: str
    purpleair_key: str
    iqair_key: str
    enabled_providers: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Config":
        providers = os.getenv("ENABLED_PROVIDERS", "openmeteo,airnow,openaq,purpleair,iqair")
        return cls(
            latitude=float(os.getenv("LATITUDE", "42.296")),
            longitude=float(os.getenv("LONGITUDE", "-71.292")),
            zip_code=os.getenv("ZIP_CODE", "02481"),
            radius_km=int(os.getenv("SEARCH_RADIUS_KM", "25")),
            poll_interval_seconds=float(os.getenv("POLL_INTERVAL_SECONDS", "300")),
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
            provider_timeout_seconds=float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "10")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_base_seconds=float(os.getenv("RETRY_BASE_SECONDS", "1")),
            history_hours=float(os.getenv("HISTORY_HOURS", "24")),
            plot_width=int(os.getenv("PLOT_WIDTH", "72")),
            plot_height=int(os.getenv("PLOT_HEIGHT", "20")),
            database_path=os.getenv("DATABASE_PATH", ".data/airquality.db"),
            alert_threshold=_optional_float(os.getenv("PM25_ALERT_THRESHOLD")),
            alert_cooldown_seconds=float(os.getenv("ALERT_COOLDOWN_SECONDS", "3600")),
            color_enabled=_color_enabled(),
            color_theme=os.getenv("COLOR_THEME", "auto").lower(),
            default_metric=os.getenv("DEFAULT_METRIC", "pm25"),
            airnow_key=os.getenv("AIRNOW_KEY", ""),
            openaq_key=os.getenv("OPENAQ_KEY", ""),
            purpleair_key=os.getenv("PURPLEAIR_KEY", ""),
            iqair_key=os.getenv("IQAIR_KEY", ""),
            enabled_providers=tuple(p.strip().lower() for p in providers.split(",") if p.strip()),
        )


CONFIG = Config.from_env()
