"""HTTP client for BiGG Models API transport."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from .errors import ApiError
from .types import JsonData, JsonValue, is_json_array, is_json_object


@dataclass(frozen=True)
class ClientSettings:
    base_url: str
    timeout: float


class BiggApiClient:
    """Thin wrapper around httpx with API-focused error handling."""

    def __init__(
        self, settings: ClientSettings, *, http_client: httpx.Client | None = None
    ) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> BiggApiClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self._settings.base_url}{path}"

    def _request_json(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> JsonValue:
        url = self._url(path)
        try:
            response = self._client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise ApiError(f"Request timed out: GET {url}") from exc
        except httpx.RequestError as exc:
            raise ApiError(f"Network error during GET {url}: {exc}") from exc

        if response.status_code == 429:
            raise ApiError(f"Rate limited by upstream API: GET {url}", status_code=429)

        if response.status_code in (401, 403):
            raise ApiError(
                f"Access denied by upstream API: GET {url} returned {response.status_code}",
                status_code=response.status_code,
            )

        if response.status_code >= 400:
            body_preview = response.text.strip().replace("\n", " ")[:200]
            raise ApiError(
                f"HTTP {response.status_code} for GET {url}: {body_preview or 'no response body'}",
                status_code=response.status_code,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ApiError(f"Invalid JSON response from GET {url}") from exc

        if not isinstance(data, (list, dict)):
            raise ApiError(f"Unexpected JSON type from GET {url}: {type(data).__name__}")
        return data

    def get_json(self, path: str, *, params: dict[str, str] | None = None) -> JsonData:
        data = self._request_json(path, params=params)
        if is_json_array(data) or is_json_object(data):
            return data
        raise ApiError(f"Expected object or array from {path}")

    def get_raw_bytes(self, path: str, *, params: dict[str, str] | None = None) -> bytes:
        url = self._url(path)
        try:
            response = self._client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise ApiError(f"Request timed out: GET {url}") from exc
        except httpx.RequestError as exc:
            raise ApiError(f"Network error during GET {url}: {exc}") from exc

        if response.status_code >= 400:
            body_preview = response.text.strip().replace("\n", " ")[:200]
            raise ApiError(
                f"HTTP {response.status_code} for GET {url}: {body_preview or 'no response body'}",
                status_code=response.status_code,
            )
        content = response.content
        if not isinstance(content, bytes):
            raise ApiError(f"Unexpected non-bytes response body from GET {url}")
        return content

    def get_database_version(self) -> JsonData:
        return self.get_json("/api/v2/database_version")

    def search(self, query: str, search_type: str) -> JsonData:
        return self.get_json(
            "/api/v2/search",
            params={"query": query, "search_type": search_type},
        )

    def list_models(self) -> JsonData:
        return self.get_json("/api/v2/models")

    def get_model(self, model_id: str) -> JsonData:
        return self.get_json(f"/api/v2/models/{model_id}")

    def download_model(self, model_id: str) -> JsonData:
        return self.get_json(f"/api/v2/models/{model_id}/download")

    def list_model_reactions(self, model_id: str) -> JsonData:
        return self.get_json(f"/api/v2/models/{model_id}/reactions")

    def get_model_reaction(self, model_id: str, reaction_id: str) -> JsonData:
        return self.get_json(f"/api/v2/models/{model_id}/reactions/{reaction_id}")

    def list_model_metabolites(self, model_id: str) -> JsonData:
        return self.get_json(f"/api/v2/models/{model_id}/metabolites")

    def get_model_metabolite(self, model_id: str, metabolite_id: str) -> JsonData:
        return self.get_json(f"/api/v2/models/{model_id}/metabolites/{metabolite_id}")

    def list_model_genes(self, model_id: str) -> JsonData:
        return self.get_json(f"/api/v2/models/{model_id}/genes")

    def get_model_gene(self, model_id: str, gene_id: str) -> JsonData:
        return self.get_json(f"/api/v2/models/{model_id}/genes/{gene_id}")

    def list_universal_reactions(self) -> JsonData:
        return self.get_json("/api/v2/universal/reactions")

    def get_universal_reaction(self, reaction_id: str) -> JsonData:
        return self.get_json(f"/api/v2/universal/reactions/{reaction_id}")

    def list_universal_metabolites(self) -> JsonData:
        return self.get_json("/api/v2/universal/metabolites")

    def get_universal_metabolite(self, metabolite_id: str) -> JsonData:
        return self.get_json(f"/api/v2/universal/metabolites/{metabolite_id}")

    def api_get(self, path: str, query: dict[str, str]) -> JsonData:
        return self.get_json(path, params=query if query else None)

    def download_static_model(self, model_id: str, fmt: str) -> bytes:
        ext = fmt
        if fmt == "xml.gz":
            ext = "xml.gz"
        path = f"/static/models/{model_id}.{ext}"
        return self.get_raw_bytes(path)

    def download_namespace_reactions(self) -> bytes:
        return self.get_raw_bytes("/static/namespace/bigg_models_reactions.txt")

    def download_namespace_metabolites(self) -> bytes:
        return self.get_raw_bytes("/static/namespace/bigg_models_metabolites.txt")

    def download_universal_model(self) -> bytes:
        return self.get_raw_bytes("/static/namespace/universal_model.json")

    def build_url(self, path: str, query: dict[str, str]) -> str:
        base = self._url(path)
        if not query:
            return base
        return f"{base}?{urlencode(query)}"

    @staticmethod
    def ensure_json_data(value: JsonValue) -> JsonData:
        if is_json_object(value) or is_json_array(value):
            return value
        raise ApiError("Response JSON must be object or array")
