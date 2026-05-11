"""Configuration loading with CLI/env/file precedence."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .errors import ConfigError

DEFAULT_BASE_URL = "http://bigg.ucsd.edu"
DEFAULT_TIMEOUT = 20.0
DEFAULT_OUTPUT = "text"
VALID_OUTPUTS = {"text", "json", "jsonl"}


@dataclass(frozen=True)
class Config:
    base_url: str
    timeout: float
    output: str


def get_default_config_path() -> Path:
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "bigg-cli" / "config.toml"
    return Path.home() / ".config" / "bigg-cli" / "config.toml"


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            loaded = tomllib.load(handle)
        if not isinstance(loaded, dict):
            raise ConfigError(f"Config file must contain a table: {path}")
        return loaded
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in config file {path}: {exc}") from exc


def _normalize_base_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ConfigError("base_url cannot be empty")
    if not value.startswith(("http://", "https://")):
        raise ConfigError("base_url must start with http:// or https://")
    return value.rstrip("/")


def _normalize_timeout(raw: str | int | float) -> float:
    try:
        timeout = float(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"timeout must be numeric, got: {raw!r}") from exc
    if timeout <= 0:
        raise ConfigError("timeout must be greater than 0")
    return timeout


def _normalize_output(raw: str) -> str:
    value = raw.strip().lower()
    if value not in VALID_OUTPUTS:
        expected = ", ".join(sorted(VALID_OUTPUTS))
        raise ConfigError(f"output must be one of: {expected}")
    return value


def load_config(
    *,
    cli_base_url: str | None = None,
    cli_timeout: float | None = None,
    cli_output: str | None = None,
    config_path: Path | None = None,
) -> Config:
    file_path = config_path or get_default_config_path()
    file_data = _load_toml(file_path)

    env_base_url = os.getenv("BIGG_BASE_URL")
    env_timeout = os.getenv("BIGG_TIMEOUT")
    env_output = os.getenv("BIGG_OUTPUT")

    base_url_raw = cast(
        str,
        cli_base_url or env_base_url or file_data.get("base_url", DEFAULT_BASE_URL),
    )
    timeout_raw: str | int | float = (
        cli_timeout
        if cli_timeout is not None
        else env_timeout
        if env_timeout is not None
        else cast(str | int | float, file_data.get("timeout", DEFAULT_TIMEOUT))
    )
    output_raw = cast(str, cli_output or env_output or file_data.get("output", DEFAULT_OUTPUT))

    return Config(
        base_url=_normalize_base_url(base_url_raw),
        timeout=_normalize_timeout(timeout_raw),
        output=_normalize_output(output_raw),
    )
