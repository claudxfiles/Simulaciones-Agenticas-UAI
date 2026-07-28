"""Carga de prompts desde YAML con interpolación de variables."""
from functools import lru_cache
from pathlib import Path

import yaml

_PROMPTS_FILE = Path(__file__).parent / "prompts.yaml"


@lru_cache
def _raw() -> dict:
    return yaml.safe_load(_PROMPTS_FILE.read_text(encoding="utf-8"))


def get_prompt(name: str, **overrides: str) -> str:
    data = _raw()
    variables = {**data.get("variables", {}), **overrides}
    template: str = data[name]
    return template.format(**variables)
