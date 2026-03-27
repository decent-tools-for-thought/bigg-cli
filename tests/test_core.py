from __future__ import annotations

import json

import pytest

from bigg_cli.core import ensure_search_type, parse_query_params, render_output
from bigg_cli.errors import UsageError
from bigg_cli.types import JsonData


def test_ensure_search_type_valid() -> None:
    assert ensure_search_type("MODELS") == "models"


def test_ensure_search_type_invalid() -> None:
    with pytest.raises(UsageError):
        ensure_search_type("unknown")


def test_parse_query_params() -> None:
    parsed = parse_query_params(["query=g3p", "search_type=metabolites"])
    assert parsed == {"query": "g3p", "search_type": "metabolites"}


def test_parse_query_params_invalid() -> None:
    with pytest.raises(UsageError):
        parse_query_params(["broken"])


def test_render_jsonl_from_results_object() -> None:
    data: JsonData = {
        "results_count": 2,
        "results": [{"bigg_id": "a"}, {"bigg_id": "b"}],
    }
    rendered = render_output(data, output="jsonl", context="search")
    lines = rendered.content.splitlines()
    assert json.loads(lines[0]) == {"bigg_id": "a"}
    assert json.loads(lines[1]) == {"bigg_id": "b"}


def test_render_jsonl_requires_list_like() -> None:
    with pytest.raises(UsageError):
        render_output({"x": 1}, output="jsonl", context="obj")
