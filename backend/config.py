# config.py - Environment and feature flags
import os


def get_mode() -> str:
    raw = os.getenv("CORTEX_ENV", "demo").lower().strip()
    if raw in ("production", "prod", "productioon"):
        return "production"
    return "demo"


def is_production() -> bool:
    return get_mode() == "production"


def use_ollama() -> bool:
    return os.getenv("USE_OLLAMA", "true").lower() in ("1", "true", "yes")


def ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.2")


def ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def http_timeout() -> float:
    """Read timeout in seconds for external APIs (Sentry, GitHub, Slack)."""
    return float(os.getenv("HTTP_TIMEOUT_SEC", "60"))


def production_cache_ttl() -> int:
    """Seconds to cache live Sentry/GitHub/Slack data (status polling)."""
    return int(os.getenv("PRODUCTION_CACHE_TTL_SEC", "45"))


def sentry_fetch_events() -> bool:
    """Extra per-issue Sentry API call for stack frames (slow)."""
    return os.getenv("SENTRY_FETCH_EVENTS", "false").lower() in ("1", "true", "yes")
