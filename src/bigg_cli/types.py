"""Shared type aliases and protocol-like unions."""

from __future__ import annotations

from typing import Any, TypeGuard

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]
JsonArray = list[JsonValue]
JsonData = JsonObject | JsonArray

Primitive = str | int | float | bool


def is_json_object(value: JsonValue) -> TypeGuard[JsonObject]:
    return isinstance(value, dict)


def is_json_array(value: JsonValue) -> TypeGuard[JsonArray]:
    return isinstance(value, list)


def as_any(value: JsonValue) -> Any:
    return value
