"""
Streamlit API client — wraps all FastAPI backend calls.
"""

import os
import requests
from typing import Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class APIClient:
    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = 120  # 2 min for AI pipeline

    def _headers(self, token: Optional[str] = None) -> dict:
        h = {"Content-Type": "application/json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    # ── Auth ─────────────────────────────────────────────────────────────────

    def register(self, email: str, password: str, full_name: str = "") -> dict:
        try:
            resp = self.session.post(
                f"{self.base_url}/auth/register",
                json={"email": email, "password": password, "full_name": full_name},
            )
            if resp.status_code == 201:
                return {"success": True, "user": resp.json()}
            return {"success": False, "error": resp.json().get("detail", resp.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def login(self, email: str, password: str) -> dict:
        try:
            resp = self.session.post(
                f"{self.base_url}/auth/login",
                json={"email": email, "password": password},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"success": True, "token": data["access_token"]}
            return {"success": False, "error": resp.json().get("detail", resp.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_me(self, token: str) -> dict:
        try:
            resp = self.session.get(
                f"{self.base_url}/auth/me",
                headers=self._headers(token),
            )
            if resp.status_code == 200:
                return {"success": True, "user": resp.json()}
            return {"success": False, "error": resp.json().get("detail", resp.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Upload ────────────────────────────────────────────────────────────────

    def upload_pdf(self, token: str, file_bytes: bytes, filename: str) -> dict:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (filename, file_bytes, "application/pdf")},
                timeout=180,
            )
            if resp.status_code == 201:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": resp.json().get("detail", resp.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_uploads(self, token: str) -> dict:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/uploads",
                headers=self._headers(token),
            )
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": resp.json().get("detail", resp.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Analysis ─────────────────────────────────────────────────────────────

    def analyze(self, token: str, upload_id: int) -> dict:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/analyze",
                json={"upload_id": upload_id},
                headers=self._headers(token),
                timeout=300,  # 5 min for multi-agent pipeline
            )
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": resp.json().get("detail", resp.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Deductions ────────────────────────────────────────────────────────────

    def get_deductions(self, token: str, upload_id: int) -> dict:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/deductions",
                params={"upload_id": upload_id},
                headers=self._headers(token),
            )
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": resp.json().get("detail", resp.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_deduction_transactions(self, token: str, upload_id: int,
                                   tax_relevant_only: bool = False) -> dict:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/deductions/transactions",
                params={"upload_id": upload_id, "tax_relevant_only": tax_relevant_only},
                headers=self._headers(token),
            )
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": resp.json().get("detail", resp.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_deductions_summary(self, token: str) -> dict:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/deductions/summary",
                headers=self._headers(token),
            )
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": resp.json().get("detail", resp.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(self, token: str, question: str) -> dict:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/query",
                json={"question": question},
                headers=self._headers(token),
                timeout=60,
            )
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": resp.json().get("detail", resp.text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Health ────────────────────────────────────────────────────────────────

    def health(self) -> dict:
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=5)
            return {"success": resp.status_code == 200, "data": resp.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
