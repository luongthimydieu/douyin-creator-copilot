from __future__ import annotations

import json
import os
from pathlib import Path


def _find_root() -> Path:
    """Use COPILOT_HOME, the current project directory, or the repo root."""
    env = os.environ.get("COPILOT_HOME")
    if env:
        return Path(env).expanduser().resolve()
    cwd = Path.cwd()
    if (cwd / "config" / "account.json").exists():
        return cwd
    return Path(__file__).resolve().parent.parent


ROOT = _find_root()
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
EPISODES_DIR = DATA_DIR / "episodes"
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "copilot.db"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def account() -> dict:
    return load_json(CONFIG_DIR / "account.json")


def pricing() -> dict:
    return load_json(CONFIG_DIR / "pricing.json")


def ensure_dirs() -> None:
    for path in (DATA_DIR, EPISODES_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def episode_dir(slug: str) -> Path:
    return EPISODES_DIR / slug
