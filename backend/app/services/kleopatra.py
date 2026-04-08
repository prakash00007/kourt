from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from app.core.config import Settings


class KleopatraClient:
    def __init__(self, settings: Settings):
        if not settings.kleopatra_api_key:
            raise ValueError("KLEOPATRA_API_KEY is required to use the Kleopatra API connector")

        self.settings = settings
        self.base_url = settings.kleopatra_base_url.rstrip("/")
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0, connect=15.0),
            headers={
                "Authorization": f"Bearer {settings.kleopatra_api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self.client.close()

    def get_high_court_states(self) -> dict[str, Any]:
        return self._request("GET", "/core/static/high-court/states")

    def get_high_court_benches(
        self,
        *,
        state_id: str | None = None,
        state_ids: Iterable[str] | None = None,
        all_states: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if state_id:
            payload["stateId"] = state_id
        if state_ids:
            payload["stateIds"] = list(state_ids)
        if all_states:
            payload["all"] = True
        return self._request("POST", "/core/static/high-court/benches", json=payload)

    def get_district_states(self) -> dict[str, Any]:
        return self._request("GET", "/core/static/district-court/states")

    def get_district_districts(
        self,
        *,
        state_id: str | None = None,
        state_ids: Iterable[str] | None = None,
        all_states: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if state_id:
            payload["stateId"] = state_id
        if state_ids:
            payload["stateIds"] = list(state_ids)
        if all_states:
            payload["all"] = True
        return self._request("POST", "/core/static/district-court/districts", json=payload)

    def get_district_complexes(
        self,
        *,
        district_id: str | None = None,
        district_ids: Iterable[str] | None = None,
        all_districts: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if district_id:
            payload["districtId"] = district_id
        if district_ids:
            payload["districtIds"] = list(district_ids)
        if all_districts:
            payload["all"] = True
        return self._request("POST", "/core/static/district-court/complexes", json=payload)

    def get_district_courts(
        self,
        *,
        complex_id: str | None = None,
        complex_ids: Iterable[str] | None = None,
        all_complexes: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if complex_id:
            payload["complexId"] = complex_id
        if complex_ids:
            payload["complexIds"] = list(complex_ids)
        if all_complexes:
            payload["all"] = True
        return self._request("POST", "/core/static/district-court/courts", json=payload)

    def search_party(
        self,
        court: str,
        *,
        name: str,
        stage: str,
        year: str,
        bench_id: str | None = None,
        district_id: str | None = None,
        complex_id: str | None = None,
        party_type: str | None = None,
    ) -> dict[str, Any]:
        court = court.lower().strip()
        path_map = {
            "supreme": "/core/live/supreme-court/search/party",
            "high": "/core/live/high-court/search/party",
            "district": "/core/live/district-court/search/party",
        }
        if court not in path_map:
            raise ValueError("court must be one of: supreme, high, district")

        payload: dict[str, Any] = {
            "name": name,
            "stage": stage,
            "year": str(year),
        }
        if court == "high":
            if bench_id:
                payload["benchId"] = bench_id
        elif court == "district":
            if district_id:
                payload["districtId"] = district_id
            if complex_id:
                payload["complexId"] = complex_id
        elif party_type:
            payload["type"] = party_type

        return self._request("POST", path_map[court], json=payload)

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.client.request(method, path, json=json)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        return {"data": data}
