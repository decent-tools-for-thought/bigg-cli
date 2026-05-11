from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest
from httpx import MockTransport, Request, Response

from bigg_cli.client import BiggApiClient, ClientSettings
from bigg_cli.errors import ApiError


def _build_client(handler: Callable[[Request], Response]) -> BiggApiClient:
    settings = ClientSettings(base_url="http://bigg.ucsd.edu", timeout=5)
    http_client = httpx.Client(transport=MockTransport(handler), timeout=5)
    client = BiggApiClient(settings, http_client=http_client)
    return client


def test_get_database_version_success() -> None:
    def handler(request: Request) -> Response:
        assert request.url.path == "/api/v2/database_version"
        return Response(200, json={"api_version": "v2"})

    client = _build_client(handler)
    try:
        result = client.get_database_version()
        assert result == {"api_version": "v2"}
    finally:
        client.close()


def test_http_error_raises_api_error() -> None:
    def handler(_: Request) -> Response:
        return Response(404, text="not found")

    client = _build_client(handler)
    try:
        with pytest.raises(ApiError) as exc:
            client.get_model("missing")
        assert "HTTP 404" in str(exc.value)
    finally:
        client.close()


def test_invalid_json_raises_api_error() -> None:
    def handler(_: Request) -> Response:
        return Response(200, content=b"not-json", headers={"content-type": "application/json"})

    client = _build_client(handler)
    try:
        with pytest.raises(ApiError) as exc:
            client.get_database_version()
        assert "Invalid JSON response" in str(exc.value)
    finally:
        client.close()
