from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from bigg_cli import cli


@pytest.fixture(autouse=True)
def no_real_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("BIGG_BASE_URL", raising=False)
    monkeypatch.delenv("BIGG_TIMEOUT", raising=False)
    monkeypatch.delenv("BIGG_OUTPUT", raising=False)


def _run(argv: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.run(argv)
    return code, out.getvalue(), err.getvalue()


def test_bare_invocation_prints_help() -> None:
    code, out, err = _run([])
    assert code == 0
    assert "usage:" in out
    assert err == ""


def test_top_level_help() -> None:
    code, out, err = _run(["--help"])
    assert code == 0
    assert "Command-line interface for the BiGG Models API" in out
    assert "default: http://bigg.ucsd.edu" in out
    assert err == ""


def test_docs_command_lists_commands() -> None:
    code, out, err = _run(["docs"])
    assert code == 0
    assert "BiGG CLI command documentation" in out
    assert "version" in out
    assert "docs" in out
    assert "models download-static" in out
    assert "universal where-reaction" in out
    assert "api get" in out
    assert err == ""


def test_usage_error_exit_code_2() -> None:
    code, out, err = _run(["search"])
    assert code == 2
    assert out == ""
    assert "Error:" in err


def test_version_json_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(cli, "op_version", lambda _client: {"api_version": "v2"})

    code, out, err = _run(["--output", "json", "version"])
    assert code == 0
    assert json.loads(out) == {"api_version": "v2"}
    assert err == ""


def test_search_text_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())

    def fake_search(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "results_count": 1,
            "results": [
                {
                    "model_bigg_id": "Universal",
                    "bigg_id": "g3p",
                    "name": "Glyceraldehyde 3-phosphate",
                    "organism": "",
                }
            ],
        }

    monkeypatch.setattr(cli, "op_search", fake_search)

    code, out, err = _run(["search", "g3p", "--type", "metabolites"])
    assert code == 0
    assert "g3p" in out
    assert err == ""


def test_find_command(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(
        cli, "op_find", lambda *_args, **_kwargs: {"groups": {}, "total_results": 0}
    )
    code, _out, err = _run(["--output", "json", "find", "g3p"])
    assert code == 0
    assert err == ""


def test_show_command(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(cli, "op_show", lambda *_args, **_kwargs: {"kind": "model"})
    code, out, _err = _run(["--output", "json", "show", "iND750"])
    assert code == 0
    assert "model" in out


def test_models_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(cli, "op_models_summary", lambda *_args, **_kwargs: {"model_id": "iND750"})
    code, out, _err = _run(["--output", "json", "models", "summary", "iND750"])
    assert code == 0
    assert "iND750" in out


def test_models_reaction_equation(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(
        cli,
        "op_model_reaction_equation",
        lambda *_args, **_kwargs: {"equation": "a_c -> b_c"},
    )
    code, out, _err = _run(["models", "reaction-equation", "iND750", "R1"])
    assert code == 0
    assert "a_c -> b_c" in out


def test_models_exists_false_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(
        cli,
        "op_models_exists",
        lambda *_args, **_kwargs: {"exists": False, "checks": {"model": False}},
    )
    code, _out, _err = _run(["models", "exists", "missing"])
    assert code == 1


def test_models_export_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(
        cli,
        "op_model_export_ids",
        lambda *_args, **_kwargs: {"ids": ["g1", "g2"]},
    )
    code, out, _err = _run(["models", "export-ids", "iND750", "--type", "genes"])
    assert code == 0
    assert "g1" in out


def test_models_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(cli, "op_model_stats", lambda *_args, **_kwargs: {"model_count": 2})
    code, out, _err = _run(["--output", "json", "models", "stats"])
    assert code == 0
    assert "model_count" in out


def test_universal_where_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(
        cli,
        "op_universal_where_reaction",
        lambda *_args, **_kwargs: {"models": [{"bigg_id": "iA"}]},
    )
    monkeypatch.setattr(
        cli,
        "op_universal_where_metabolite",
        lambda *_args, **_kwargs: {"models": [{"bigg_id": "iA"}]},
    )
    code_r, out_r, _err_r = _run(["--output", "json", "universal", "where-reaction", "ADA"])
    code_m, out_m, _err_m = _run(["--output", "json", "universal", "where-metabolite", "g3p"])
    assert code_r == 0 and code_m == 0
    assert "models" in out_r
    assert "models" in out_m


def test_fetch_command(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(
        cli,
        "op_fetch",
        lambda *_args, **_kwargs: [{"field": "results[].bigg_id", "value": "x"}],
    )
    code, out, _err = _run(
        [
            "--output",
            "json",
            "fetch",
            "/api/v2/search",
            "--field",
            "results[].bigg_id",
        ]
    )
    assert code == 0
    assert "results[].bigg_id" in out


def test_models_download_static(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    out_file = tmp_path / "model.xml"
    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(cli, "op_models_download_static", lambda *_args, **_kwargs: b"<xml/>")
    code, _out, _err = _run(
        [
            "models",
            "download-static",
            "iND750",
            "--format",
            "xml",
            "--out",
            str(out_file),
        ]
    )
    assert code == 0
    assert out_file.read_bytes() == b"<xml/>"


def test_namespace_commands(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(cli, "op_namespace_reactions", lambda *_args, **_kwargs: b"rxn\n")
    monkeypatch.setattr(cli, "op_namespace_metabolites", lambda *_args, **_kwargs: b"met\n")
    monkeypatch.setattr(cli, "op_namespace_universal_model", lambda *_args, **_kwargs: b"{}")

    rxn = tmp_path / "r.txt"
    met = tmp_path / "m.txt"
    uni = tmp_path / "u.json"

    c1, _o1, _e1 = _run(["namespace", "reactions", "--out", str(rxn)])
    c2, _o2, _e2 = _run(["namespace", "metabolites", "--out", str(met)])
    c3, _o3, _e3 = _run(["namespace", "universal-model", "--out", str(uni)])

    assert c1 == c2 == c3 == 0
    assert rxn.read_bytes() == b"rxn\n"
    assert met.read_bytes() == b"met\n"
    assert uni.read_bytes() == b"{}"


def test_compare_models_command(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(
        cli,
        "op_compare_models",
        lambda *_args, **_kwargs: {"reactions": {"overlap_count": 1}},
    )
    code, out, _err = _run(["--output", "json", "compare", "models", "i1", "i2"])
    assert code == 0
    assert "overlap_count" in out


def test_where_gene_command(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(cli, "op_where_gene", lambda *_args, **_kwargs: {"results_count": 1})
    code, out, _err = _run(["--output", "json", "where", "gene", "g1"])
    assert code == 0
    assert "results_count" in out


def test_links_command(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(cli, "op_links", lambda *_args, **_kwargs: {"results_count": 1})
    code, out, _err = _run(["--output", "json", "links", "reaction", "ADA"])
    assert code == 0
    assert "results_count" in out


def test_batch_show_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    id_file = tmp_path / "ids.txt"
    id_file.write_text("i1\nmissing\n", encoding="utf-8")

    monkeypatch.setattr(cli, "BiggApiClient", lambda _settings: FakeClient())
    monkeypatch.setattr(cli, "op_batch_show", lambda *_args, **_kwargs: {"results_count": 2})
    code, out, _err = _run(
        [
            "--output",
            "json",
            "batch",
            "show",
            "model",
            "--from-file",
            str(id_file),
        ]
    )
    assert code == 0
    assert "results_count" in out
