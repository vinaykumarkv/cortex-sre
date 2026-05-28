# ollama_client.py — Local LLM patches via Ollama (llama3.2)
import logging
import re

import httpx

from config import ollama_base_url, ollama_model

logger = logging.getLogger(__name__)


def generate_patch(source_code: str, traceback_logs: str, model: str | None = None) -> tuple[str | None, str | None]:
    """
    Ask Ollama to return the full fixed file contents.
    Returns (patched_source, explanation) or (None, None) on failure.
    """
    model = model or ollama_model()
    base = ollama_base_url()

    prompt = f"""You are an expert Python SRE engineer. A pytest suite failed.

## Test / traceback output
{traceback_logs[-8000:]}

## Current source file (fix this completely)
{source_code}

Instructions:
1. Fix the bug so tests would pass.
2. Return ONLY the complete corrected Python source code.
3. Do not wrap the answer in markdown code fences.
4. Keep the same module structure and function names unless required.
"""

    logger.info("Requesting patch from Ollama model=%s at %s", model, base)
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(
            f"{base}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "")

    if not content or not content.strip():
        return None, None

    patched = _strip_fences(content.strip())
    explanation = f"Ollama ({model}) generated patch from pytest traceback."
    return patched, explanation


def _strip_fences(text: str) -> str:
    """Remove ```python ... ``` wrappers if the model adds them."""
    match = re.search(r"```(?:python)?\s*\n?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def is_available() -> bool:
    """Quick health check — Ollama running and model listed."""
    try:
        base = ollama_base_url()
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{base}/api/tags")
            if resp.status_code != 200:
                return False
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            wanted = ollama_model()
            return any(wanted in name for name in models)
    except Exception:
        return False
