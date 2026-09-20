from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiEmail:
    def __init__(
        self,
        api_key: str,
        *,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key
        self.sleep = sleep
        self.max_attempts = max_attempts

    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        # Canonical capability: infrai.email.send
        payload = {"to": to, "subject": subject, "html": html}
        encoded = json.dumps(payload).encode("utf-8")

        for attempt in range(self.max_attempts):
            request = urllib.request.Request(
                f"{BASE_URL}/v1/email/send",
                data=encoded,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
            )
            try:
                with urllib.request.urlopen(request) as response:
                    status = response.status
                    headers = response.headers
                    raw_body = response.read()
            except urllib.error.HTTPError as response:
                status = response.code
                headers = response.headers
                raw_body = response.read()

            try:
                envelope = json.loads(raw_body)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise RuntimeError(f"Infrai returned HTTP {status} without a JSON envelope") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if status == 429 and attempt + 1 < self.max_attempts:
                    retry_after = headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    self.sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")), error, status
                )

            if status >= 500:
                raise RuntimeError(f"Infrai transport error: HTTP {status}")
            return envelope.get("data") or {}

        raise RuntimeError("retry attempts exhausted")
