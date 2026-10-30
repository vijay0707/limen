"""Deterministic test doubles. No network, no API key, no spend."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from limen.answers import Answer, ChoiceAnswer, NoulAnswer, ProviderResult, ScoreAnswer
from limen.errors import ProviderError, ProviderUnavailable
from limen.questions import Choice, Noul, Question, QuestionSet

FakeValue = float | str | tuple[float, float] | tuple[str, float] | Answer


def _unit(key: str, field: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f"fake {key!r}: {field} must be a number in [0, 1], got {value!r}")
    return float(value)


def _split(value: Any) -> tuple[Any, float]:
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError(f"fake tuple must be (value, confidence), got {value!r}")
        return value[0], value[1]
    return value, 1.0


def _build(key: str, question: Question, value: Any) -> Answer:
    if isinstance(question, Noul):
        if isinstance(value, NoulAnswer):
            return value
        if isinstance(value, tuple):
            raise TypeError(f"fake {key!r}: a Noul has no confidence; pass a bare probability")
        return NoulAnswer(probability=_unit(key, "probability", value))

    if isinstance(question, Choice):
        if isinstance(value, ChoiceAnswer):
            return value
        choice, confidence = _split(value)
        if choice not in question.options:
            raise ValueError(f"fake {key!r}: {choice!r} is not one of {list(question.options)}")
        return ChoiceAnswer(
            choice=choice,
            confidence=_unit(key, "confidence", confidence),
            probabilities={name: 1.0 if name == choice else 0.0 for name in question.options},
        )

    if isinstance(value, ScoreAnswer):
        return value
    score, confidence = _split(value)
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise TypeError(f"fake {key!r}: score must be a number, got {score!r}")
    if not 0 <= score <= question.max_score:
        raise ValueError(f"fake {key!r}: score must be in [0, {question.max_score}], got {score}")
    # Spread the mass over the two neighbouring levels so it averages back to `score`.
    low = math.floor(score)
    probabilities = [0.0] * len(question.levels)
    probabilities[low] = 1.0 - (score - low)
    if low < question.max_score:
        probabilities[low + 1] = score - low
    return ScoreAnswer(
        score=float(score),
        confidence=_unit(key, "confidence", confidence),
        probabilities=tuple(probabilities),
    )


class FakeProvider:
    """Returns fixed answers keyed by question name.

    Values: a float for a Noul; a float or ``(score, confidence)`` for a Score; an option name
    or ``(name, confidence)`` for a Choice; or an answer object for full control. Shorthand
    values without a confidence get ``confidence=1.0``.
    """

    def __init__(
        self,
        values: Mapping[str, FakeValue] | None = None,
        *,
        model: str = "fake",
        error: ProviderError | None = None,
    ) -> None:
        self.values = dict(values or {})
        self.model = model
        self.error = error
        self.calls: list[tuple[QuestionSet, Any]] = []

    @classmethod
    def failing(cls, error: ProviderError | None = None) -> FakeProvider:
        """A provider that always raises, for exercising ``Policy.on_failure``."""
        return cls(error=error or ProviderUnavailable("fake provider is down"))

    def answer(
        self, qs: QuestionSet, state: Any, *, timeout_s: float | None = None
    ) -> ProviderResult:
        self.calls.append((qs, state))
        if self.error is not None:
            raise self.error
        missing = [key for key in qs.questions if key not in self.values]
        if missing:
            raise KeyError(f"FakeProvider has no values for {missing} in {qs.ref}")
        return ProviderResult(
            model=self.model,
            answers={key: _build(key, q, self.values[key]) for key, q in qs.questions.items()},
        )
