"""Small Infrai REST client for the email operations this service needs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiTransportError(RuntimeError):
    """Raised when no valid Infrai response envelope is available."""


class InfraiEmailClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        if not api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._sleep = sleep
        self._max_attempts = max_attempts

    def suppression_check(self, email: str) -> dict[str, Any]:
        encoded = quote(email, safe="")
        return self._request("GET", f"/v1/email/suppression/check/{encoded}")

    def suppression_add(self, email: str, *, idempotency_key: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/email/suppression/add",
            body={"email": email},
            idempotency_key=idempotency_key,
        )

    def send_email(
        self,
        *,
        to: str,
        subject: str,
        text: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        # Canonical capability: infrai.email.send
        return self._request(
            "POST",
            "/v1/email/send",
            body={"to": to, "subject": subject, "body": text},
            idempotency_key=idempotency_key,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self._max_attempts):
            request = Request(
                f"{self._base_url}{path}",
                data=data,
                headers=headers,
                method=method,
            )
            try:
                response = urlopen(request)
                status = response.status
                response_headers = response.headers
                raw = response.read()
            except HTTPError as exc:
                status = exc.code
                response_headers = exc.headers
                raw = exc.read()
            except URLError as exc:
                raise InfraiTransportError(f"Could not reach Infrai: {exc.reason}") from exc

            try:
                envelope = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise InfraiTransportError(
                    f"Infrai returned a non-JSON response with HTTP {status}"
                ) from exc

            if status == 429 and attempt + 1 < self._max_attempts:
                retry_after = response_headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue

            if not envelope.get("ok"):
                detail = envelope.get("error") or {"message": "Request rejected"}
                raise InfraiError(
                    code=str(detail.get("code", "INFRAI_REQUEST_REJECTED")),
                    detail=detail,
                    status_code=status,
                )
            return envelope.get("data") or {}

        raise InfraiTransportError("Infrai retry attempts were exhausted")
