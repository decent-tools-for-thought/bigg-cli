from __future__ import annotations

from pathlib import Path

import pytest

from bigg_cli.config import load_config
from bigg_cli.errors import ConfigError


def test_load_config_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("BIGG_BASE_URL", raising=False)
    monkeypatch.delenv("BIGG_TIMEOUT", raising=False)
    monkeypatch.delenv("BIGG_OUTPUT", raising=False)

    cfg = load_config(config_path=tmp_path / "missing.toml")
    assert cfg.base_url == "https://bigg.ucsd.edu"
    assert cfg.timeout == 20.0
    assert cfg.output == "text"


def test_precedence_cli_over_env_over_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        'base_url = "https://from-file.example"\ntimeout = 10\noutput = "json"\n',
        encoding="utf-8",
    )

    monkeypatch.setenv("BIGG_BASE_URL", "https://from-env.example")
    monkeypatch.setenv("BIGG_TIMEOUT", "15")
    monkeypatch.setenv("BIGG_OUTPUT", "jsonl")

    cfg = load_config(
        cli_base_url="https://from-cli.example",
        cli_timeout=22,
        cli_output="text",
        config_path=cfg_file,
    )
    assert cfg.base_url == "https://from-cli.example"
    assert cfg.timeout == 22
    assert cfg.output == "text"


def test_invalid_timeout_raises(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('timeout = "abc"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(config_path=cfg_file)
