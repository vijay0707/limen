"""Providers turn a question set and a state into typed answers, in one request."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

import httpx

from limen._state import prepare_state
from limen._wire import decode_response, encode_request
from limen.answers import ProviderResult
from limen.errors import (
    ProviderError,
    ProviderRequestError,
    ProviderUnavailable,
    StateTooLarge,
)
from limen.questions import QuestionSet

MAX_REQUEST_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_FIELD_CHARS = 20_000
_RETRYABLE_STATUS = {429, 529}


@runtime_checkable
class Provider(Protocol):
    def answer(
        self, qs: QuestionSet, state: Any, *, timeout_s: float | None = None
    ) -> ProviderResult:
        """Answer every question in ``qs`` against ``state`` in a single request."""
        ...


def _error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:500]
    if isinstance(body, dict) and "detail" in body:
        return json.dumps(body["detail"])[:500]
    return json.dumps(body)[:500]


class SystemOneProvider:
    """HTTP provider for any compatible ``/v1/systemone`` endpoint.

    ``redact`` and ``max_field_chars`` live here rather than at call sites: the redaction
    list is a compliance artifact, configured once.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        redact: Iterable[str] = (),
        max_field_chars: int = DEFAULT_MAX_FIELD_CHARS,
        client: httpx.Client | None = None,
    ) -> None:
        if max_field_chars < 1:
            raise ValueError("max_field_chars must be >= 1")
        self.url = base_url.rstrip("/")
        self.model = model
        self.redact = frozenset(redact)
        self.max_field_chars = max_field_chars
        self._api_key = api_key
        self._client = client or httpx.Client()

    @classmethod
    def from_env(
        cls,
        *,
        redact: Iterable[str] = (),
        max_field_chars: int = DEFAULT_MAX_FIELD_CHARS,
        client: httpx.Client | None = None,
    ) -> SystemOneProvider:
        names = ("LIMEN_BASE_URL", "LIMEN_API_KEY", "LIMEN_MODEL")
        values = {name: os.environ.get(name, "") for name in names}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError(f"missing environment variables: {', '.join(missing)}")
        return cls(
            values["LIMEN_BASE_URL"],
            values["LIMEN_API_KEY"],
            values["LIMEN_MODEL"],
            redact=redact,
            max_field_chars=max_field_chars,
            client=client,
        )

    def __repr__(self) -> str:
        return f"SystemOneProvider(url={self.url!r}, model={self.model!r})"

    def answer(
        self, qs: QuestionSet, state: Any, *, timeout_s: float | None = None
    ) -> ProviderResult:
        prepared = prepare_state(state, redact=self.redact, max_field_chars=self.max_field_chars)
        try:
            body = json.dumps(
                encode_request(qs, prepared, self.model), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ProviderRequestError(f"state is not JSON-serializable: {exc}") from exc
        if len(body) > MAX_REQUEST_BYTES:
            raise StateTooLarge(f"request is {len(body)} bytes; limit is {MAX_REQUEST_BYTES}")

        started = time.perf_counter()
        try:
            response = self._client.post(
                self.url,
                content=body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=timeout_s,
            )
        except httpx.TimeoutException as exc:
            raise ProviderUnavailable(f"timed out after {timeout_s}s") from exc
        except httpx.TransportError as exc:
            raise ProviderUnavailable(f"could not reach provider: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000

        status = response.status_code
        if status in _RETRYABLE_STATUS or status >= 500:
            raise ProviderUnavailable(f"HTTP {status}: {_error_detail(response)}")
        if status >= 400:
            raise ProviderRequestError(f"HTTP {status}: {_error_detail(response)}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("response is not valid JSON") from exc
        return decode_response(qs, payload, latency_ms=latency_ms)


_default: Provider | None = None


def default_provider() -> Provider:
    """The provider built from ``LIMEN_*`` environment variables, created on first use."""
    global _default
    if _default is None:
        _default = SystemOneProvider.from_env()
    return _default
