"""Configuration loader with environment variable substitution for ${VAR_NAME} placeholders."""
import os
import re
import yaml
from typing import Any, Dict


_ENV_PATTERN = re.compile(r'^\$\{([A-Z0-9_]+)\}$')


def _resolve_env_placeholders(value: Any) -> Any:
    """Recursively resolve ${VAR_NAME} values from environment."""
    if isinstance(value, dict):
        return {k: _resolve_env_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(v) for v in value]
    if isinstance(value, str):
        m = _ENV_PATTERN.match(value.strip())
        if m:
            env_name = m.group(1)
            return os.getenv(env_name, "")
    return value


class Config:
    """Simple YAML config reader with dot-path get/set and env placeholder resolution."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.config_path):
            self.config = {}
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        self.config = _resolve_env_placeholders(raw)

    @property
    def trading_config(self) -> Dict[str, Any]:
        return self.config.get("trading", {})

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        cur = self.config
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return default
        return cur

    def set(self, key: str, value: Any):
        parts = key.split(".")
        cur = self.config
        for p in parts[:-1]:
            if p not in cur or not isinstance(cur[p], dict):
                cur[p] = {}
            cur = cur[p]
        cur[parts[-1]] = value