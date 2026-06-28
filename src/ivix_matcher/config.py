from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default_matching_config.json"


class ConfigError(ValueError):
    """Raised when matching configuration is invalid."""


@dataclass(frozen=True)
class MatchingConfig:
    raw: dict[str, Any]
    path: Path

    @property
    def schemas(self) -> dict[str, Any]:
        return self.raw["schemas"]

    @property
    def blocking(self) -> dict[str, Any]:
        return self.raw["blocking"]

    @property
    def name_variants(self) -> dict[str, Any]:
        return self.raw["name_variants"]

    @property
    def decision_rules(self) -> list[dict[str, Any]]:
        return self.raw["decision_rules"]

    @property
    def default_decision(self) -> str:
        return self.raw["default_decision"]


def load_config(path: str | Path | None = None) -> MatchingConfig:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Could not read config file {config_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON config {config_path}: {exc}") from exc
    config = MatchingConfig(raw=raw, path=config_path)
    validate_config(config)
    return config


def _require_mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"Config key '{key}' must be an object")
    return value


def _require_list(parent: dict[str, Any], key: str) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        raise ConfigError(f"Config key '{key}' must be a list")
    return value


def validate_config(config: MatchingConfig) -> None:
    raw = config.raw
    schemas = _require_mapping(raw, "schemas")
    for schema_name in ("full_address", "split_address"):
        if schema_name not in schemas or not isinstance(schemas[schema_name], dict):
            raise ConfigError(f"Config schemas.{schema_name} must be an object")
    blocking = _require_mapping(raw, "blocking")
    _require_list(blocking, "scope_fields")
    _require_list(blocking, "address_keys")
    variants = _require_mapping(raw, "name_variants")
    if not isinstance(variants.get("token_replacements", {}), dict):
        raise ConfigError("Config name_variants.token_replacements must be an object")
    if int(variants.get("max_variants_per_name", 0)) <= 0:
        raise ConfigError("Config name_variants.max_variants_per_name must be positive")
    rules = _require_list(raw, "decision_rules")
    for rule in rules:
        if not isinstance(rule, dict) or "name" not in rule or "decision" not in rule or not isinstance(rule.get("conditions"), dict):
            raise ConfigError("Each decision rule must have name, decision, and conditions object")
    if not isinstance(raw.get("default_decision"), str):
        raise ConfigError("Config default_decision must be a string")