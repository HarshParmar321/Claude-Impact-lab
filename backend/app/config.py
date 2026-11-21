"""Runtime configuration loaded from environment / backend/.env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = Path(os.getenv("NAGARLENS_DATA_DIR", BACKEND_DIR / "data"))
CACHE_PATH = Path(os.getenv("NAGARLENS_CACHE_PATH", BACKEND_DIR / "cache" / "claude_responses.json"))
DATABASE_URL = os.getenv("NAGARLENS_DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'nagarlens.db'}")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
# Any current Claude model ID works; set ANTHROPIC_MODEL in backend/.env to choose.
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "").strip() or "claude-sonnet-4-5"
ANTHROPIC_TIMEOUT_S = float(os.getenv("ANTHROPIC_TIMEOUT_S", "45"))

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
# Set NAGARLENS_DISABLE_LIVE_CLAUDE=1 to force cache/template mode (used by tests).
DISABLE_LIVE_CLAUDE = os.getenv("NAGARLENS_DISABLE_LIVE_CLAUDE", "") == "1"


def live_claude_enabled() -> bool:
    return bool(ANTHROPIC_API_KEY) and not DISABLE_LIVE_CLAUDE
