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
