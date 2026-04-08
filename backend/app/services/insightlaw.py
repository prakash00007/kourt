from __future__ import annotations

from typing import Any

import httpx


class InsightLawClient:
    def __init__(self, base_url: str = "https://insightlaw.in/api"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0, connect=15.0),
            headers={
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        self.client.close()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def constitution_article(self, number: str | int) -> dict[str, Any]:
        return self._request("GET", f"/constitution/article/{number}")

    def constitution_search(self, query: str) -> dict[str, Any]:
        return self._request("GET", "/search", params={"q": query})

    def ipc_section(self, number: str | int) -> dict[str, Any]:
        return self._request("GET", f"/ipc/section/{number}")

    def ipc_search(self, query: str) -> dict[str, Any]:
        return self._request("GET", "/ipc/search", params={"q": query})

    def bns_section(self, number: str | int) -> dict[str, Any]:
        return self._request("GET", f"/bns/section/{number}")

    def bns_search(self, query: str) -> dict[str, Any]:
        return self._request("GET", "/bns/search", params={"q": query})

    def search(self, query: str) -> dict[str, Any]:
        return self._request("GET", "/search", params={"q": query})

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.client.request(method, path, params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        return {"data": data}
