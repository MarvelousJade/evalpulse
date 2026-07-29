"""Small cookie-aware HTTP client shared by EvalPulse's command-line checks."""

from __future__ import annotations

import http.cookiejar
import json
import urllib.error
import urllib.request
from typing import Any


class EvalPulseHttpClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.cookies = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(
        self,
        path: str,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        **headers: str,
    ) -> Any:
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            body,
            {"Content-Type": "application/json", **headers},
            method=method,
        )
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"{method} {path} failed: {exc.code} {detail}") from exc

    def post(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
        **headers: str,
    ) -> Any:
        return self.request(
            path,
            "POST",
            payload,
            **{"X-CSRF-Token": self._csrf_token(), **headers},
        )

    def _csrf_token(self) -> str:
        return next(cookie.value for cookie in self.cookies if cookie.name == "evalpulse_csrf")
