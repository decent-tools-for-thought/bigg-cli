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
