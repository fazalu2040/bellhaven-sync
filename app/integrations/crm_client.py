from __future__ import annotations

from typing import Any

import requests

from app.config import settings


class CRMClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or settings.crm_base_url).rstrip("/")
        self.token = token or settings.crm_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def fetch_accounts(self) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/accounts", timeout=30)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            data = payload.get("data") or payload.get("results") or payload.get("accounts") or []
        else:
            data = payload
        return data if isinstance(data, list) else []

    def create_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(f"{self.base_url}/accounts", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def update_account(self, account_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        if not account_id:
            raise ValueError("account_id is required for CRM update operations.")

        url = f"{self.base_url}/accounts/{account_id}"
        last_error: Exception | None = None
        clean_payload = {key: value for key, value in (payload or {}).items() if value not in (None, "", [], {})}

        for method in ("PATCH", "PUT", "POST"):
            try:
                response = self.session.request(method, url, json=clean_payload, timeout=30)
                if response.status_code in {200, 201, 202, 204}:
                    try:
                        return response.json()
                    except ValueError:
                        return {"status": "success", "status_code": response.status_code, "method": method}

                if response.status_code == 405:
                    last_error = requests.HTTPError(f"405 Method Not Allowed for {method} {url}")
                    continue

                response.raise_for_status()
                try:
                    return response.json()
                except ValueError:
                    return {"status": "success", "status_code": response.status_code, "method": method}
            except requests.RequestException as exc:
                last_error = exc
                if getattr(exc, "response", None) is not None and exc.response.status_code == 405:
                    continue
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"No valid update strategy succeeded for account {account_id}.")
