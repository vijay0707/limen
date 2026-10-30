import json

import httpx
import pytest

from limen import (
    Noul,
    ProviderError,
    ProviderRequestError,
    ProviderUnavailable,
    QuestionSet,
    StateTooLarge,
    SystemOneProvider,
)
from limen._state import REDACTED, prepare_state
from limen.providers import MAX_REQUEST_BYTES

from .test_wire import RESPONSE

URL = "https://example.test/v1/systemone"


def make(handler, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SystemOneProvider(URL, "sk-test", "jev-latest", client=client, **kwargs)


def test_sends_one_authenticated_request(qs):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=RESPONSE)

    result = make(handler).answer(qs, {"sql": "DROP TABLE x"}, timeout_s=0.4)
    assert len(seen) == 1
    assert str(seen[0].url) == URL
    assert seen[0].headers["authorization"] == "Bearer sk-test"
    assert set(json.loads(seen[0].content)["questions"]) == set(qs.questions)
    assert result.model == "jev-1.13.0"
    assert result.latency_ms >= 0


@pytest.mark.parametrize("status", [429, 500, 503, 529])
def test_transient_status_is_unavailable(qs, status):
    provider = make(lambda r: httpx.Response(status, json={"detail": "busy"}))
    with pytest.raises(ProviderUnavailable, match=str(status)):
        provider.answer(qs, "x")


@pytest.mark.parametrize("status", [400, 401, 413, 422])
def test_client_status_is_request_error(qs, status):
    provider = make(lambda r: httpx.Response(status, json={"detail": [{"msg": "bad field"}]}))
    with pytest.raises(ProviderRequestError, match="bad field"):
        provider.answer(qs, "x")


@pytest.mark.parametrize("exc", [httpx.ReadTimeout("slow"), httpx.ConnectError("refused")])
def test_transport_failures_are_unavailable(qs, exc):
    def handler(request):
        raise exc

    with pytest.raises(ProviderUnavailable):
        make(handler).answer(qs, "x")


def test_non_json_response_is_provider_error(qs):
    with pytest.raises(ProviderError):
        make(lambda r: httpx.Response(200, text="<html>")).answer(qs, "x")


def test_redaction_and_truncation_happen_before_sending(qs):
    sent = {}

    def handler(request):
        sent.update(json.loads(request.content))
        return httpx.Response(200, json=RESPONSE)

    provider = make(handler, redact={"email", "ssn"}, max_field_chars=10)
    provider.answer(qs, {"email": "a@b.c", "nested": [{"ssn": "123"}], "sql": "x" * 50})
    assert sent["state"]["email"] == REDACTED
    assert sent["state"]["nested"][0]["ssn"] == REDACTED
    assert sent["state"]["sql"].startswith("xxxxx…[40 chars truncated]…")


def test_oversized_state_is_never_sent(qs):
    def handler(request):
        raise AssertionError("should not send")

    provider = make(handler, max_field_chars=MAX_REQUEST_BYTES * 2)
    with pytest.raises(StateTooLarge):
        provider.answer(qs, "x" * (MAX_REQUEST_BYTES + 1))


def test_unserializable_state_is_request_error(qs):
    with pytest.raises(ProviderRequestError):
        make(lambda r: httpx.Response(200, json=RESPONSE)).answer(qs, {"x": object()})


def test_from_env_names_missing_variables(monkeypatch):
    for name in ("LIMEN_BASE_URL", "LIMEN_API_KEY", "LIMEN_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIMEN_MODEL", "jev-latest")
    with pytest.raises(ValueError, match="LIMEN_BASE_URL, LIMEN_API_KEY"):
        SystemOneProvider.from_env()


def test_from_env(monkeypatch):
    monkeypatch.setenv("LIMEN_BASE_URL", URL + "/")
    monkeypatch.setenv("LIMEN_API_KEY", "sk-test")
    monkeypatch.setenv("LIMEN_MODEL", "jev-latest")
    provider = SystemOneProvider.from_env()
    assert provider.url == URL
    assert "sk-test" not in repr(provider)


def test_prepare_state_leaves_short_values_alone():
    state = {"a": "short", "b": 3, "c": None, "d": [True, 1.5]}
    assert prepare_state(state, redact=frozenset(), max_field_chars=100) == state


def test_prepare_state_truncates_head_and_tail():
    out = prepare_state("abcdefghij", redact=frozenset(), max_field_chars=4)
    assert out == "ab…[6 chars truncated]…ij"


def test_question_set_fixture_shape():
    # Guard: a one-question set encodes and decodes too.
    one = QuestionSet(name="s", version=1, questions={"d": Noul("x?")})
    body = {"model": "m", "answers": {"d": {"type": "noul", "noul": 0.2}}, "usage": {}}
    result = make(lambda r: httpx.Response(200, json=body)).answer(one, "x")
    assert result.answers["d"].probability == 0.2
