"""Core orchestration and rendering logic for bigg-cli."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .client import BiggApiClient
from .errors import UsageError
from .types import JsonArray, JsonData, JsonObject, JsonValue, is_json_array, is_json_object

VALID_SEARCH_TYPES = {"models", "reactions", "metabolites", "genes"}
VALID_OUTPUTS = {"text", "json", "jsonl"}


@dataclass(frozen=True)
class RenderedOutput:
    content: str


def _expect_object(data: JsonData, *, context: str) -> JsonObject:
    if is_json_object(data):
        return data
    raise UsageError(f"Expected object response for {context}")


def _expect_array(data: JsonData, *, context: str) -> JsonArray:
    if is_json_array(data):
        return data
    raise UsageError(f"Expected array response for {context}")


def _slice_results(items: JsonArray, limit: int | None) -> JsonArray:
    if limit is None:
        return items
    if limit < 1:
        raise UsageError("--limit must be >= 1")
    return items[:limit]


def _as_str(value: JsonValue | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _render_list_lines(items: JsonArray, fields: tuple[str, ...]) -> str:
    lines: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            lines.append(_as_str(item))
            continue
        values = [_as_str(item.get(field)) for field in fields]
        lines.append("\t".join(values))
    return "\n".join(lines)


def _render_text(data: JsonData, context: str) -> str:
    if context == "version" and isinstance(data, dict):
        return (
            f"BiGG models version: {_as_str(data.get('bigg_models_version'))}\n"
            f"API version: {_as_str(data.get('api_version'))}\n"
            f"Last updated: {_as_str(data.get('last_updated'))}"
        )

    if context in {"models.list", "search"} and isinstance(data, dict):
        results_raw = data.get("results", [])
        results = results_raw if isinstance(results_raw, list) else []
        if not results:
            return "No results"
        return _render_list_lines(results, ("model_bigg_id", "bigg_id", "name", "organism"))

    if context.endswith(".list") and isinstance(data, list):
        if not data:
            return "No results"
        return _render_list_lines(data, ("model_bigg_id", "bigg_id", "name", "organism"))

    return json.dumps(data, indent=2, sort_keys=True)


def render_output(data: JsonData, *, output: str, context: str) -> RenderedOutput:
    if output not in VALID_OUTPUTS:
        expected = ", ".join(sorted(VALID_OUTPUTS))
        raise UsageError(f"Invalid output format '{output}'. Expected one of: {expected}")

    if output == "json":
        return RenderedOutput(content=json.dumps(data, indent=2, sort_keys=True))

    if output == "jsonl":
        if is_json_array(data):
            return RenderedOutput(
                content="\n".join(json.dumps(item, sort_keys=True) for item in data)
            )
        if is_json_object(data):
            results = data.get("results")
            if isinstance(results, list):
                return RenderedOutput(
                    content="\n".join(json.dumps(item, sort_keys=True) for item in results)
                )
        raise UsageError(
            "jsonl output requires a list response (or object with list field 'results')"
        )

    return RenderedOutput(content=_render_text(data, context))


def ensure_search_type(search_type: str) -> str:
    normalized = search_type.lower()
    if normalized not in VALID_SEARCH_TYPES:
        expected = ", ".join(sorted(VALID_SEARCH_TYPES))
        raise UsageError(f"Invalid search type '{search_type}'. Expected one of: {expected}")
    return normalized


def parse_query_params(items: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise UsageError(f"Invalid --query value '{item}'. Expected KEY=VALUE")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise UsageError(f"Invalid --query key in '{item}'")
        parsed[key] = value
    return parsed


def write_download(path: Path, data: JsonData) -> None:
    content = json.dumps(data, indent=2, sort_keys=True)
    path.write_text(content, encoding="utf-8")


def op_version(client: BiggApiClient) -> JsonObject:
    data = client.get_database_version()
    return _expect_object(data, context="version")


def op_search(
    client: BiggApiClient, *, query: str, search_type: str, limit: int | None
) -> JsonObject:
    data = client.search(query=query, search_type=ensure_search_type(search_type))
    obj = _expect_object(data, context="search")
    if limit is None:
        return obj
    results = obj.get("results")
    if isinstance(results, list):
        sliced = _slice_results(results, limit)
        reduced = dict(obj)
        reduced["results"] = sliced
        reduced["results_count"] = len(sliced)
        return reduced
    return obj


def op_models_list(client: BiggApiClient, *, limit: int | None) -> JsonObject:
    data = client.list_models()
    obj = _expect_object(data, context="models.list")
    if limit is None:
        return obj
    results = obj.get("results")
    if isinstance(results, list):
        sliced = _slice_results(results, limit)
        reduced = dict(obj)
        reduced["results"] = sliced
        reduced["results_count"] = len(sliced)
        return reduced
    return obj


def op_models_show(client: BiggApiClient, *, model_id: str) -> JsonObject:
    return _expect_object(client.get_model(model_id), context="models.show")


def op_models_download(client: BiggApiClient, *, model_id: str) -> JsonObject:
    return _expect_object(client.download_model(model_id), context="models.download")


def op_model_reactions(client: BiggApiClient, *, model_id: str, limit: int | None) -> JsonArray:
    items = _expect_array(client.list_model_reactions(model_id), context="models.reactions")
    return _slice_results(items, limit)


def op_model_reaction(client: BiggApiClient, *, model_id: str, reaction_id: str) -> JsonObject:
    return _expect_object(
        client.get_model_reaction(model_id, reaction_id),
        context="models.reaction",
    )


def op_model_metabolites(client: BiggApiClient, *, model_id: str, limit: int | None) -> JsonArray:
    items = _expect_array(client.list_model_metabolites(model_id), context="models.metabolites")
    return _slice_results(items, limit)


def op_model_metabolite(client: BiggApiClient, *, model_id: str, metabolite_id: str) -> JsonObject:
    return _expect_object(
        client.get_model_metabolite(model_id, metabolite_id),
        context="models.metabolite",
    )


def op_model_genes(client: BiggApiClient, *, model_id: str, limit: int | None) -> JsonArray:
    items = _expect_array(client.list_model_genes(model_id), context="models.genes")
    return _slice_results(items, limit)


def op_model_gene(client: BiggApiClient, *, model_id: str, gene_id: str) -> JsonObject:
    return _expect_object(client.get_model_gene(model_id, gene_id), context="models.gene")


def op_universal_reactions(client: BiggApiClient, *, limit: int | None) -> JsonArray:
    items = _expect_array(client.list_universal_reactions(), context="universal.reactions")
    return _slice_results(items, limit)


def op_universal_reaction(client: BiggApiClient, *, reaction_id: str) -> JsonObject:
    return _expect_object(client.get_universal_reaction(reaction_id), context="universal.reaction")


def op_universal_metabolites(client: BiggApiClient, *, limit: int | None) -> JsonArray:
    items = _expect_array(client.list_universal_metabolites(), context="universal.metabolites")
    return _slice_results(items, limit)


def op_universal_metabolite(client: BiggApiClient, *, metabolite_id: str) -> JsonObject:
    return _expect_object(
        client.get_universal_metabolite(metabolite_id), context="universal.metabolite"
    )


def op_api_get(client: BiggApiClient, *, path: str, query: list[str]) -> JsonData:
    parsed_query = parse_query_params(query)
    return client.api_get(path, parsed_query)
