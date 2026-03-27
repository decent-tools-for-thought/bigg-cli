from __future__ import annotations

from typing import Any, cast

from bigg_cli.client import BiggApiClient
from bigg_cli.core import (
    op_batch_show,
    op_compare_models,
    op_fetch,
    op_find,
    op_links,
    op_model_export_ids,
    op_model_reaction_equation,
    op_model_stats,
    op_models_download_static,
    op_models_exists,
    op_models_summary,
    op_namespace_metabolites,
    op_namespace_reactions,
    op_namespace_universal_model,
    op_show,
    op_universal_where_metabolite,
    op_universal_where_reaction,
    op_where_gene,
)
from bigg_cli.errors import ApiError


class FakeClient:
    def search(self, query: str, search_type: str) -> dict[str, Any]:
        if search_type == "genes":
            return {"results_count": 1, "results": [{"bigg_id": query, "model_bigg_id": "i1"}]}
        return {"results_count": 1, "results": [{"bigg_id": f"{search_type}_{query}"}]}

    def get_model(self, model_id: str) -> dict[str, Any]:
        if model_id in {"iND750", "i1", "i2"}:
            return {"bigg_id": model_id, "organism": "Saccharomyces"}
        raise ApiError("not found", status_code=404)

    def list_model_reactions(self, _model_id: str) -> list[dict[str, Any]]:
        if _model_id == "i1":
            return [{"bigg_id": "R1"}, {"bigg_id": "R2"}]
        if _model_id == "i2":
            return [{"bigg_id": "R2"}, {"bigg_id": "R3"}]
        return [{"bigg_id": "R1"}, {"bigg_id": "R2"}]

    def list_model_metabolites(self, _model_id: str) -> list[dict[str, Any]]:
        if _model_id == "i1":
            return [{"bigg_id": "m1"}, {"bigg_id": "m2"}]
        if _model_id == "i2":
            return [{"bigg_id": "m2"}, {"bigg_id": "m3"}]
        return [{"bigg_id": "m1"}, {"bigg_id": "m2"}]

    def list_model_genes(self, _model_id: str) -> list[dict[str, Any]]:
        if _model_id == "i1":
            return [{"bigg_id": "g1"}, {"bigg_id": "g2"}]
        if _model_id == "i2":
            return [{"bigg_id": "g2"}, {"bigg_id": "g3"}]
        return [{"bigg_id": "g1"}, {"bigg_id": "g2"}]

    def get_model_reaction(self, _model_id: str, reaction_id: str) -> dict[str, Any]:
        return {
            "bigg_id": reaction_id,
            "metabolites": [
                {"bigg_id": "a", "compartment_bigg_id": "c", "stoichiometry": -1},
                {"bigg_id": "b", "compartment_bigg_id": "c", "stoichiometry": 2},
            ],
        }

    def get_model_metabolite(self, _model_id: str, metabolite_id: str) -> dict[str, Any]:
        return {"bigg_id": metabolite_id}

    def get_model_gene(self, _model_id: str, gene_id: str) -> dict[str, Any]:
        return {
            "bigg_id": gene_id,
            "database_links": {"X": [{"id": "1", "link": "http://x"}]},
            "reactions": [{"bigg_id": "R1"}],
        }

    def get_universal_reaction(self, reaction_id: str) -> dict[str, Any]:
        return {
            "bigg_id": reaction_id,
            "models_containing_reaction": [{"bigg_id": "iA", "organism": "OrgA"}],
            "database_links": {"Y": [{"id": "2", "link": "http://y"}]},
        }

    def get_universal_metabolite(self, metabolite_id: str) -> dict[str, Any]:
        return {
            "bigg_id": metabolite_id,
            "compartments_in_models": [{"model_bigg_id": "iA", "organism": "OrgA"}],
        }

    def list_models(self) -> dict[str, Any]:
        return {
            "results_count": 2,
            "results": [
                {"bigg_id": "i1", "organism": "OrgA", "reaction_count": 100},
                {"bigg_id": "i2", "organism": "OrgB", "reaction_count": 200},
            ],
        }

    def api_get(self, path: str, query: dict[str, str]) -> dict[str, Any]:
        return {"results": [{"bigg_id": "x"}], "path": path, "query": query}

    def download_static_model(self, model_id: str, fmt: str) -> bytes:
        return f"{model_id}:{fmt}".encode()

    def download_namespace_reactions(self) -> bytes:
        return b"rxn\n"

    def download_namespace_metabolites(self) -> bytes:
        return b"met\n"

    def download_universal_model(self) -> bytes:
        return b"{}"


def test_op_find() -> None:
    data = op_find(cast(BiggApiClient, FakeClient()), query="g3p", limit=1)
    assert data["total_results"] == 4


def test_op_show_model() -> None:
    data = op_show(cast(BiggApiClient, FakeClient()), identifier="iND750")
    assert data["kind"] == "model"


def test_op_models_summary() -> None:
    data = op_models_summary(cast(BiggApiClient, FakeClient()), model_id="iND750")
    assert data["model_id"] == "iND750"


def test_op_model_reaction_equation() -> None:
    data = op_model_reaction_equation(
        cast(BiggApiClient, FakeClient()),
        model_id="iND750",
        reaction_id="R",
    )
    assert "a_c -> 2 b_c" in str(data["equation"])


def test_op_models_exists() -> None:
    data = op_models_exists(
        cast(BiggApiClient, FakeClient()),
        model_id="iND750",
        reaction_id="R",
        metabolite_id="m",
        gene_id="g",
    )
    assert bool(data["exists"])


def test_op_universal_where_reaction() -> None:
    data = op_universal_where_reaction(cast(BiggApiClient, FakeClient()), reaction_id="ADA")
    assert data["count"] == 1


def test_op_universal_where_metabolite() -> None:
    data = op_universal_where_metabolite(cast(BiggApiClient, FakeClient()), metabolite_id="g3p")
    assert data["count"] == 1


def test_op_model_export_ids() -> None:
    data = op_model_export_ids(
        cast(BiggApiClient, FakeClient()), model_id="iND750", export_type="genes"
    )
    assert data["ids"] == ["g1", "g2"]


def test_op_model_stats() -> None:
    data = op_model_stats(cast(BiggApiClient, FakeClient()), organism_pattern=None)
    assert data["model_count"] == 2


def test_op_fetch_field_extract() -> None:
    data = op_fetch(
        cast(BiggApiClient, FakeClient()),
        path_or_url="/api/v2/search",
        query=["query=g3p"],
        fields=["results[].bigg_id"],
    )
    assert isinstance(data, list)
    assert data[0] == {"field": "results[].bigg_id", "value": "x"}


def test_op_models_download_static() -> None:
    payload = op_models_download_static(
        cast(BiggApiClient, FakeClient()), model_id="iND750", fmt="xml"
    )
    assert payload == b"iND750:xml"


def test_namespace_operations() -> None:
    client = cast(BiggApiClient, FakeClient())
    assert op_namespace_reactions(client) == b"rxn\n"
    assert op_namespace_metabolites(client) == b"met\n"
    assert op_namespace_universal_model(client) == b"{}"


def test_op_compare_models() -> None:
    data = op_compare_models(cast(BiggApiClient, FakeClient()), model_a="i1", model_b="i2")
    assert data["reactions"] == {"a_only_count": 1, "b_only_count": 1, "overlap_count": 1}


def test_op_where_gene() -> None:
    data = op_where_gene(cast(BiggApiClient, FakeClient()), gene_id="g1", limit=2)
    assert data["results_count"] == 1


def test_op_links() -> None:
    data = op_links(
        cast(BiggApiClient, FakeClient()),
        resource="reaction",
        identifier="ADA",
        model_id=None,
    )
    assert data["results_count"] == 1


def test_op_batch_show() -> None:
    data = op_batch_show(
        cast(BiggApiClient, FakeClient()),
        resource="model",
        items=["i1", "missing"],
        model_id=None,
    )
    results = data["results"]
    assert isinstance(results, list)
    assert len(results) == 2
