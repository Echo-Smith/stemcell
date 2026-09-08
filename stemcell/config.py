"""Load only explicitly needed model variables, without executing .env text."""

from __future__ import annotations

import os
import shlex
from pathlib import Path

MODEL_ENV_KEYS = {
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "JUDGE_API_KEY",
    "JUDGE_BASE_URL",
    "JUDGE_MODEL",
}


def load_env_file(path: str | Path) -> None:
    values = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, raw = line.partition("=")
        name = name.strip()
        if not separator or name not in MODEL_ENV_KEYS:
            continue
        try:
            parts = shlex.split(raw.strip(), comments=True, posix=True)
        except ValueError:
            raise ValueError(f"Invalid quoted value for {name}") from None
        if len(parts) > 1:
            raise ValueError(f"Quote values with spaces for {name}")
        value = parts[0] if parts else ""
        if "$" in value or "`" in value:
            raise ValueError(f"Variable interpolation is not supported for {name}")
        values[name] = value
    os.environ.update(values)
