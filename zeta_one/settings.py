"""Settings and keys: from the environment, else from `.env`. Values are never printed or logged."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def setting(name: str, env_file: Path | None = None) -> str | None:
    """A setting from the environment, else from `.env`; never printed or logged."""
    if os.environ.get(name):
        return os.environ[name]
    env_file = env_file or ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip().removeprefix("export ").strip() == name and value.strip():
                return value.strip().strip("'\"")
    return None
