"""Core orchestration and rendering logic for bigg-cli."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import cast
from urllib.parse import parse_qsl, urlparse

from .client import BiggApiClient
from .errors import ApiError, UsageError
from .types import JsonArray, JsonData, JsonObject, JsonValue, is_json_array, is_json_object

VALID_SEARCH_TYPES = {"models", "reactions", "metabolites", "genes"}
VALID_OUTPUTS = {"text", "json", "jsonl"}
VALID_EXPORT_TYPES = {"reactions", "metabolites", "genes"}
VALID_MODEL_FILE_FORMATS = {"xml", "xml.gz", "json", "mat"}


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

    if context == "models.reaction_equation" and isinstance(data, dict):
        equation = _as_str(data.get("equation"))
        return equation or "No equation available"

    if context == "models.exists" and isinstance(data, dict):
        exists = bool(data.get("exists", False))
        lines = [f"exists={str(exists).lower()}"]
        checks = data.get("checks")
        if isinstance(checks, dict):
            for key, value in checks.items():
                lines.append(f"{key}={str(bool(value)).lower()}")
        return "\n".join(lines)

    if context == "models.export_ids" and isinstance(data, dict):
        ids = data.get("ids")
        if isinstance(ids, list):
            return "\n".join(_as_str(item) for item in ids)
        return "No results"

    if context in {"universal.where_reaction", "universal.where_metabolite"} and isinstance(
        data, dict
    ):
        models = data.get("models")
        if not isinstance(models, list) or not models:
            return "No results"
        return _render_list_lines(models, ("bigg_id", "organism"))

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


def write_bytes(path: Path, data: bytes) -> None:
    path.write_bytes(data)


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


def _safe_get_object(getter: Callable[..., JsonData], *args: str) -> JsonObject | None:
    try:
        data = getter(*args)
        if isinstance(data, dict):
            return data
        return None
    except ApiError as exc:
        if exc.status_code == 404:
            return None
        raise


def op_find(client: BiggApiClient, *, query: str, limit: int | None) -> JsonObject:
    grouped: JsonObject = {}
    total = 0
    for search_type in sorted(VALID_SEARCH_TYPES):
        result = op_search(client, query=query, search_type=search_type, limit=limit)
        grouped[search_type] = result
        count = result.get("results_count")
        total += int(count) if isinstance(count, int) else 0
    return {"query": query, "total_results": total, "groups": grouped}


def op_show(client: BiggApiClient, *, identifier: str) -> JsonObject:
    model = _safe_get_object(client.get_model, identifier)
    if model is not None:
        return {
            "kind": "model",
            "id": identifier,
            "resolved": model,
        }

    reaction = _safe_get_object(client.get_universal_reaction, identifier)
    if reaction is not None:
        return {
            "kind": "universal_reaction",
            "id": identifier,
            "resolved": reaction,
        }

    metabolite = _safe_get_object(client.get_universal_metabolite, identifier)
    if metabolite is not None:
        return {
            "kind": "universal_metabolite",
            "id": identifier,
            "resolved": metabolite,
        }

    genes = op_search(client, query=identifier, search_type="genes", limit=25)
    gene_results = genes.get("results")
    if isinstance(gene_results, list):
        exact = [
            item
            for item in gene_results
            if isinstance(item, dict) and _as_str(item.get("bigg_id")) == identifier
        ]
        if exact:
            first = exact[0]
            model_id = _as_str(first.get("model_bigg_id"))
            if model_id:
                gene = _safe_get_object(client.get_model_gene, model_id, identifier)
                if gene is not None:
                    return {
                        "kind": "model_gene",
                        "id": identifier,
                        "model_bigg_id": model_id,
                        "resolved": gene,
                    }

    raise UsageError(f"No object resolved for ID: {identifier}")


def op_models_summary(client: BiggApiClient, *, model_id: str) -> JsonObject:
    model = op_models_show(client, model_id=model_id)
    reactions = op_model_reactions(client, model_id=model_id, limit=5)
    metabolites = op_model_metabolites(client, model_id=model_id, limit=5)
    genes = op_model_genes(client, model_id=model_id, limit=5)
    return {
        "model_id": model_id,
        "model": model,
        "preview": {
            "reactions": reactions,
            "metabolites": metabolites,
            "genes": genes,
        },
    }


def _format_term(metabolite: JsonObject, coeff: float) -> str:
    comp = _as_str(metabolite.get("compartment_bigg_id"))
    base = _as_str(metabolite.get("bigg_id"))
    token = f"{base}_{comp}" if comp else base
    mag = abs(coeff)
    if mag == 1:
        return token
    if float(int(mag)) == mag:
        return f"{int(mag)} {token}"
    return f"{mag:g} {token}"


def _build_equation(metabolites: JsonArray) -> str:
    left: list[str] = []
    right: list[str] = []
    for item in metabolites:
        if not isinstance(item, dict):
            continue
        raw = item.get("stoichiometry")
        if not isinstance(raw, (int, float)):
            continue
        coeff = float(raw)
        if coeff < 0:
            left.append(_format_term(item, coeff))
        elif coeff > 0:
            right.append(_format_term(item, coeff))
    return f"{' + '.join(left) if left else '∅'} -> {' + '.join(right) if right else '∅'}"


def op_model_reaction_equation(
    client: BiggApiClient, *, model_id: str, reaction_id: str
) -> JsonObject:
    reaction = op_model_reaction(client, model_id=model_id, reaction_id=reaction_id)
    metabolites_raw = reaction.get("metabolites")
    metabolites = metabolites_raw if isinstance(metabolites_raw, list) else []
    equation = _build_equation(metabolites)
    return {
        "model_id": model_id,
        "reaction_id": reaction_id,
        "equation": equation,
        "reaction": reaction,
    }


def _exists_check(getter: Callable[..., JsonData], *args: str) -> bool:
    try:
        getter(*args)
        return True
    except ApiError as exc:
        if exc.status_code == 404:
            return False
        raise


def op_models_exists(
    client: BiggApiClient,
    *,
    model_id: str,
    reaction_id: str | None,
    metabolite_id: str | None,
    gene_id: str | None,
) -> JsonObject:
    checks: JsonObject = {}
    model_exists = _exists_check(client.get_model, model_id)
    checks["model"] = model_exists

    if reaction_id is not None:
        checks["reaction"] = model_exists and _exists_check(
            client.get_model_reaction, model_id, reaction_id
        )
    if metabolite_id is not None:
        checks["metabolite"] = model_exists and _exists_check(
            client.get_model_metabolite,
            model_id,
            metabolite_id,
        )
    if gene_id is not None:
        checks["gene"] = model_exists and _exists_check(client.get_model_gene, model_id, gene_id)

    exists = all(bool(v) for v in checks.values())
    return {
        "exists": exists,
        "model_id": model_id,
        "checks": checks,
    }


def op_universal_where_reaction(client: BiggApiClient, *, reaction_id: str) -> JsonObject:
    reaction = op_universal_reaction(client, reaction_id=reaction_id)
    models_raw = reaction.get("models_containing_reaction")
    models = models_raw if isinstance(models_raw, list) else []
    return {
        "reaction_id": reaction_id,
        "count": len(models),
        "models": models,
    }


def op_universal_where_metabolite(client: BiggApiClient, *, metabolite_id: str) -> JsonObject:
    metabolite = op_universal_metabolite(client, metabolite_id=metabolite_id)
    models_raw = metabolite.get("compartments_in_models")
    models = models_raw if isinstance(models_raw, list) else []
    return {
        "metabolite_id": metabolite_id,
        "count": len(models),
        "models": models,
    }


def op_model_export_ids(client: BiggApiClient, *, model_id: str, export_type: str) -> JsonObject:
    normalized = export_type.lower()
    if normalized not in VALID_EXPORT_TYPES:
        expected = ", ".join(sorted(VALID_EXPORT_TYPES))
        raise UsageError(f"Invalid export type '{export_type}'. Expected one of: {expected}")

    items: JsonArray
    if normalized == "reactions":
        items = op_model_reactions(client, model_id=model_id, limit=None)
    elif normalized == "metabolites":
        items = op_model_metabolites(client, model_id=model_id, limit=None)
    else:
        items = op_model_genes(client, model_id=model_id, limit=None)

    ids: list[str] = []
    for item in items:
        if isinstance(item, dict):
            value = item.get("bigg_id")
            if isinstance(value, str) and value:
                ids.append(value)

    ids_json: JsonArray = list(ids)
    return {
        "model_id": model_id,
        "type": normalized,
        "count": len(ids),
        "ids": ids_json,
    }


def op_model_stats(client: BiggApiClient, *, organism_pattern: str | None) -> JsonObject:
    listed = op_models_list(client, limit=None)
    results_raw = listed.get("results")
    models = (
        [item for item in results_raw if isinstance(item, dict)]
        if isinstance(results_raw, list)
        else []
    )

    if organism_pattern:
        query = organism_pattern.lower()
        models = [m for m in models if query in _as_str(m.get("organism")).lower()]

    reaction_counts = [
        int(v) for model in models for v in [model.get("reaction_count")] if isinstance(v, int)
    ]
    organisms = [
        _as_str(model.get("organism")) for model in models if _as_str(model.get("organism"))
    ]
    top = Counter(organisms).most_common(10)
    top_organisms: JsonArray = [{"organism": organism, "count": count} for organism, count in top]

    summary: JsonObject = {
        "model_count": len(models),
        "organism_pattern": organism_pattern or "",
        "top_organisms": top_organisms,
    }
    if reaction_counts:
        summary["reaction_count_min"] = min(reaction_counts)
        summary["reaction_count_max"] = max(reaction_counts)
        summary["reaction_count_median"] = float(median(reaction_counts))
    return summary


def _extract_by_path(data: JsonData, field: str) -> JsonArray:
    parts = field.split(".")
    current: list[JsonValue] = [cast(JsonValue, data)]
    for part in parts:
        is_list = part.endswith("[]")
        key = part[:-2] if is_list else part
        next_values: list[JsonValue] = []
        for value in current:
            if not isinstance(value, dict):
                continue
            child = value.get(key)
            if is_list:
                if isinstance(child, list):
                    next_values.extend(child)
            elif child is not None:
                next_values.append(child)
        current = next_values
    return current


def _normalize_fetch_path_and_query(
    path_or_url: str, query: dict[str, str]
) -> tuple[str, dict[str, str]]:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        parsed = urlparse(path_or_url)
        merged = dict(parse_qsl(parsed.query))
        merged.update(query)
        return parsed.path or "/", merged
    return path_or_url, query


def op_fetch(
    client: BiggApiClient,
    *,
    path_or_url: str,
    query: list[str],
    fields: list[str],
) -> JsonData:
    parsed_query = parse_query_params(query)
    path, merged_query = _normalize_fetch_path_and_query(path_or_url, parsed_query)
    data = client.api_get(path, merged_query)
    if not fields:
        return data
    extracted: JsonArray = []
    for field in fields:
        values = _extract_by_path(data, field)
        for value in values:
            extracted.append({"field": field, "value": value})
    return extracted


def op_models_download_static(client: BiggApiClient, *, model_id: str, fmt: str) -> bytes:
    normalized = fmt.lower()
    if normalized not in VALID_MODEL_FILE_FORMATS:
        expected = ", ".join(sorted(VALID_MODEL_FILE_FORMATS))
        raise UsageError(f"Invalid model format '{fmt}'. Expected one of: {expected}")
    return client.download_static_model(model_id, normalized)


def op_namespace_reactions(client: BiggApiClient) -> bytes:
    return client.download_namespace_reactions()


def op_namespace_metabolites(client: BiggApiClient) -> bytes:
    return client.download_namespace_metabolites()


def op_namespace_universal_model(client: BiggApiClient) -> bytes:
    return client.download_universal_model()


def _extract_bigg_ids(items: JsonArray) -> set[str]:
    ids: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            value = item.get("bigg_id")
            if isinstance(value, str) and value:
                ids.add(value)
    return ids


def op_compare_models(client: BiggApiClient, *, model_a: str, model_b: str) -> JsonObject:
    a_reactions = _extract_bigg_ids(op_model_reactions(client, model_id=model_a, limit=None))
    b_reactions = _extract_bigg_ids(op_model_reactions(client, model_id=model_b, limit=None))
    a_metabolites = _extract_bigg_ids(op_model_metabolites(client, model_id=model_a, limit=None))
    b_metabolites = _extract_bigg_ids(op_model_metabolites(client, model_id=model_b, limit=None))
    a_genes = _extract_bigg_ids(op_model_genes(client, model_id=model_a, limit=None))
    b_genes = _extract_bigg_ids(op_model_genes(client, model_id=model_b, limit=None))

    return {
        "model_a": model_a,
        "model_b": model_b,
        "reactions": {
            "a_only_count": len(a_reactions - b_reactions),
            "b_only_count": len(b_reactions - a_reactions),
            "overlap_count": len(a_reactions & b_reactions),
        },
        "metabolites": {
            "a_only_count": len(a_metabolites - b_metabolites),
            "b_only_count": len(b_metabolites - a_metabolites),
            "overlap_count": len(a_metabolites & b_metabolites),
        },
        "genes": {
            "a_only_count": len(a_genes - b_genes),
            "b_only_count": len(b_genes - a_genes),
            "overlap_count": len(a_genes & b_genes),
        },
    }


def op_where_gene(client: BiggApiClient, *, gene_id: str, limit: int | None) -> JsonObject:
    search = op_search(client, query=gene_id, search_type="genes", limit=limit)
    results_raw = search.get("results")
    results = (
        [item for item in results_raw if isinstance(item, dict)]
        if isinstance(results_raw, list)
        else []
    )

    resolved: JsonArray = []
    for item in results:
        model_id = item.get("model_bigg_id")
        if not isinstance(model_id, str) or not model_id:
            continue
        gene = _safe_get_object(client.get_model_gene, model_id, gene_id)
        if gene is None:
            continue
        reactions_raw = gene.get("reactions")
        reactions = reactions_raw if isinstance(reactions_raw, list) else []
        resolved.append(
            {
                "model_bigg_id": model_id,
                "gene": gene,
                "reaction_count": len(reactions),
            }
        )

    return {
        "gene_id": gene_id,
        "results_count": len(resolved),
        "results": resolved,
    }


def _flatten_database_links(resource_id: str, database_links: JsonValue) -> JsonArray:
    rows: JsonArray = []
    if not isinstance(database_links, dict):
        return rows
    for db_name, entries in database_links.items():
        if not isinstance(db_name, str) or not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                rows.append(
                    {
                        "resource_id": resource_id,
                        "database": db_name,
                        "id": _as_str(entry.get("id")),
                        "link": _as_str(entry.get("link")),
                    }
                )
    return rows


def op_links(
    client: BiggApiClient, *, resource: str, identifier: str, model_id: str | None
) -> JsonObject:
    normalized = resource.lower()
    if normalized == "model":
        obj = op_models_show(client, model_id=identifier)
    elif normalized == "reaction":
        obj = (
            op_model_reaction(client, model_id=model_id, reaction_id=identifier)
            if model_id
            else op_universal_reaction(client, reaction_id=identifier)
        )
    elif normalized == "metabolite":
        obj = (
            op_model_metabolite(client, model_id=model_id, metabolite_id=identifier)
            if model_id
            else op_universal_metabolite(client, metabolite_id=identifier)
        )
    elif normalized == "gene":
        if not model_id:
            raise UsageError("--model-id is required for gene links")
        obj = op_model_gene(client, model_id=model_id, gene_id=identifier)
    else:
        raise UsageError("resource must be one of: model, reaction, metabolite, gene")

    database_links = obj.get("database_links")
    rows = _flatten_database_links(identifier, database_links)
    return {
        "resource": normalized,
        "id": identifier,
        "model_id": model_id or "",
        "results_count": len(rows),
        "results": rows,
    }


def op_batch_show(
    client: BiggApiClient, *, resource: str, items: list[str], model_id: str | None
) -> JsonObject:
    normalized = resource.lower()
    rows: JsonArray = []
    for raw in items:
        item = raw.strip()
        if not item:
            continue
        try:
            if normalized == "model":
                resolved = op_models_show(client, model_id=item)
            elif normalized == "reaction":
                resolved = (
                    op_model_reaction(client, model_id=model_id, reaction_id=item)
                    if model_id
                    else op_universal_reaction(client, reaction_id=item)
                )
            elif normalized == "metabolite":
                resolved = (
                    op_model_metabolite(client, model_id=model_id, metabolite_id=item)
                    if model_id
                    else op_universal_metabolite(client, metabolite_id=item)
                )
            elif normalized == "gene":
                if not model_id:
                    raise UsageError("--model-id is required for gene batch show")
                resolved = op_model_gene(client, model_id=model_id, gene_id=item)
            else:
                raise UsageError("resource must be one of: model, reaction, metabolite, gene")
            rows.append({"id": item, "ok": True, "result": resolved})
        except (ApiError, UsageError) as exc:
            rows.append({"id": item, "ok": False, "error": str(exc)})

    return {
        "resource": normalized,
        "model_id": model_id or "",
        "results_count": len(rows),
        "results": rows,
    }
