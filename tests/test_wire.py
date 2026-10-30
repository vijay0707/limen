import pytest

from limen import ChoiceAnswer, NoulAnswer, ProviderError, ScoreAnswer
from limen._wire import decode_response, encode_request

RESPONSE = {
    "model": "jev-1.13.0",
    "answers": {
        "destructive": {"type": "noul", "noul": 0.91},
        "risk": {
            "type": "score",
            "score": 2.4,
            "confidence": 0.7,
            "legend": {"0": "Trivial", "1": "Routine", "2": "Needs care", "3": "Dangerous"},
            "probabilities": {"0": 0.0, "1": 0.1, "2": 0.4, "3": 0.5},
        },
        "kind": {
            "type": "choice",
            "choice": "schema",
            "confidence": 0.88,
            "probabilities": {"schema": 0.9, "data": 0.08, "other": 0.02},
        },
    },
    "usage": {"input_tokens": 120, "output_tokens": 3},
}


def test_encode_request(qs):
    body = encode_request(qs, {"sql": "DROP TABLE x"}, "jev-latest")
    assert body["model"] == "jev-latest"
    assert body["state"] == {"sql": "DROP TABLE x"}
    assert body["questions"]["destructive"] == {
        "type": "noul",
        "instructions": qs.questions["destructive"].instructions,
    }
    assert body["questions"]["risk"]["criteria"] == [
        "Trivial",
        "Routine",
        "Needs care",
        "Dangerous",
    ]
    assert body["questions"]["kind"]["criteria"] == {
        "schema": "DDL changes.",
        "data": "DML backfills.",
        "other": None,
    }


def test_decode_response(qs):
    result = decode_response(qs, RESPONSE, latency_ms=12.5)
    assert result.model == "jev-1.13.0"
    assert result.answers["destructive"] == NoulAnswer(0.91)
    assert result.answers["risk"] == ScoreAnswer(2.4, 0.7, (0.0, 0.1, 0.4, 0.5))
    kind = result.answers["kind"]
    assert isinstance(kind, ChoiceAnswer)
    assert kind.choice == "schema"
    assert kind.probabilities["data"] == 0.08
    assert (result.input_tokens, result.output_tokens, result.latency_ms) == (120, 3, 12.5)


def test_noul_answer_has_no_confidence(qs):
    answer = decode_response(qs, RESPONSE).answers["destructive"]
    assert not hasattr(answer, "confidence")


def test_missing_answer_is_provider_error(qs):
    body = {**RESPONSE, "answers": {k: v for k, v in RESPONSE["answers"].items() if k != "risk"}}
    with pytest.raises(ProviderError, match="risk"):
        decode_response(qs, body)


def test_type_mismatch_is_provider_error(qs):
    answers = {**RESPONSE["answers"], "destructive": RESPONSE["answers"]["kind"]}
    with pytest.raises(ProviderError, match="expected 'noul'"):
        decode_response(qs, {**RESPONSE, "answers": answers})


def test_unknown_choice_is_provider_error(qs):
    kind = {**RESPONSE["answers"]["kind"], "choice": "nope"}
    with pytest.raises(ProviderError, match="not one of the options"):
        decode_response(qs, {**RESPONSE, "answers": {**RESPONSE["answers"], "kind": kind}})


def test_garbage_body_is_provider_error(qs):
    with pytest.raises(ProviderError):
        decode_response(qs, ["not", "a", "dict"])
