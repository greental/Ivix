from __future__ import annotations

import json
from pathlib import Path

import pytest

from ivix_matcher.config import ConfigError, load_config


def test_loads_default_config() -> None:
    config = load_config()
    assert config.schemas["full_address"]["id"] == "id"
    assert config.blocking["address_keys"]


def test_loads_explicit_config_path(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(load_config().raw), encoding="utf-8")
    assert load_config(config_path).path == config_path


def test_invalid_config_fails_clearly(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.json"
    config_path.write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigError, match="schemas"):
        load_config(config_path)