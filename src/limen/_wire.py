"""System One JSON encoding. The only module that knows the wire format."""

from __future__ import annotations

from typing import Any

from limen.answers import Answer, ChoiceAnswer, NoulAnswer, ProviderResult, ScoreAnswer
from limen.errors import ProviderError
from limen.questions import Choice, Noul, Question, QuestionSet, Score


def _encode_question(question: Question) -> dict[str, Any]:
    if isinstance(question, Noul):
        return {"type": "noul", "instructions": question.instructions}
    if isinstance(question, Choice):
        return {
            "type": "choice",
            "instructions": question.instructions,
            "criteria": dict(question.options),
        }
    return {
        "type": "score",
        "instructions": question.instructions,
        "criteria": list(question.levels),
    }


def encode_request(qs: QuestionSet, state: Any, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "state": state,
        "questions": {key: _encode_question(q) for key, q in qs.questions.items()},
    }


def _number(raw: dict[str, Any], field: str, key: str) -> float:
    value = raw.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderError(f"answer {key!r}: {field!r} missing or not a number")
    return float(value)


def _decode_answer(key: str, question: Question, raw: Any) -> Answer:
    if not isinstance(raw, dict):
        raise ProviderError(f"answer {key!r} is not an object")
    expected = {Noul: "noul", Choice: "choice", Score: "score"}[type(question)]
    if raw.get("type") != expected:
        raise ProviderError(f"answer {key!r} has type {raw.get('type')!r}, expected {expected!r}")

    if isinstance(question, Noul):
        return NoulAnswer(probability=_number(raw, "noul", key))

    probabilities = raw.get("probabilities")
    if not isinstance(probabilities, dict):
        raise ProviderError(f"answer {key!r}: 'probabilities' missing or not an object")
    confidence = _number(raw, "confidence", key)

    if isinstance(question, Choice):
        choice = raw.get("choice")
        if not isinstance(choice, str) or choice not in question.options:
            raise ProviderError(f"answer {key!r}: choice {choice!r} is not one of the options")
        return ChoiceAnswer(
            choice=choice,
            confidence=confidence,
            probabilities={name: _number(probabilities, name, key) for name in question.options},
        )

    return ScoreAnswer(
        score=_number(raw, "score", key),
        confidence=confidence,
        probabilities=tuple(
            _number(probabilities, str(i), key) for i in range(len(question.levels))
        ),
    )


def decode_response(qs: QuestionSet, body: Any, *, latency_ms: float = 0.0) -> ProviderResult:
    if not isinstance(body, dict) or not isinstance(body.get("answers"), dict):
        raise ProviderError("response has no 'answers' object")
    raw_answers = body["answers"]
    missing = [key for key in qs.questions if key not in raw_answers]
    if missing:
        raise ProviderError(f"response is missing answers for {missing}")

    usage = body["usage"] if isinstance(body.get("usage"), dict) else {}
    return ProviderResult(
        model=str(body.get("model", "")),
        answers={key: _decode_answer(key, q, raw_answers[key]) for key, q in qs.questions.items()},
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        latency_ms=latency_ms,
    )
