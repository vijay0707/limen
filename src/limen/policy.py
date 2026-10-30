"""Outcomes, gates, policies and ``decide``: where probabilities become decisions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from limen.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from limen.errors import PolicyError, ProviderError
from limen.providers import Provider, default_provider
from limen.questions import Choice, Noul, QuestionSet, Score


class Outcome(str, Enum):
    ACT = "ACT"
    ABSTAIN = "ABSTAIN"
    ESCALATE = "ESCALATE"


ACT = Outcome.ACT
ABSTAIN = Outcome.ABSTAIN
ESCALATE = Outcome.ESCALATE


def _unit(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be a number in [0, 1], got {value!r}")
    return float(value)


def _outcome(then: Outcome) -> Outcome:
    if not isinstance(then, Outcome):
        raise TypeError(f"then must be an Outcome, got {then!r}")
    return then


def _one_bound(gte: float | None, lte: float | None) -> None:
    if (gte is None) == (lte is None):
        raise ValueError("pass exactly one of gte= or lte=")


def _bound_text(gte: float | None, lte: float | None) -> str:
    return f">= {gte:g}" if gte is not None else f"<= {lte:g}"


def _within(value: float, gte: float | None, lte: float | None) -> bool:
    return value >= gte if gte is not None else value <= lte  # type: ignore[operator]


@dataclass(frozen=True)
class NoulGate:
    key: str
    gte: float | None
    lte: float | None
    then: Outcome

    def matches(self, answer: NoulAnswer) -> bool:
        return _within(answer.probability, self.gte, self.lte)

    def describe(self) -> str:
        return f"noul_gate({self.key} {_bound_text(self.gte, self.lte)}) -> {self.then.value}"


@dataclass(frozen=True)
class ChoiceGate:
    key: str
    equals: str | None
    not_equals: str | None
    min_confidence: float
    then: Outcome

    def matches(self, answer: ChoiceAnswer) -> bool:
        if answer.confidence < self.min_confidence:
            return False
        if self.equals is not None:
            return answer.choice == self.equals
        return answer.choice != self.not_equals

    def describe(self) -> str:
        cmp = f"== {self.equals}" if self.equals is not None else f"!= {self.not_equals}"
        return (
            f"choice_gate({self.key} {cmp}, confidence >= {self.min_confidence:g})"
            f" -> {self.then.value}"
        )


@dataclass(frozen=True)
class ScoreGate:
    key: str
    gte: float | None
    lte: float | None
    min_confidence: float
    then: Outcome

    def matches(self, answer: ScoreAnswer) -> bool:
        return answer.confidence >= self.min_confidence and _within(
            answer.score, self.gte, self.lte
        )

    def describe(self) -> str:
        return (
            f"score_gate({self.key} {_bound_text(self.gte, self.lte)},"
            f" confidence >= {self.min_confidence:g}) -> {self.then.value}"
        )


Rule = NoulGate | ChoiceGate | ScoreGate


def noul_gate(
    key: str, *, gte: float | None = None, lte: float | None = None, then: Outcome
) -> NoulGate:
    """Fire when the probability of yes crosses a bound.

    There is no ``min_confidence``: a Noul has no confidence value.
    """
    _one_bound(gte, lte)
    return NoulGate(
        key,
        None if gte is None else _unit("gte", gte),
        None if lte is None else _unit("lte", lte),
        _outcome(then),
    )


def choice_gate(
    key: str,
    *,
    equals: str | None = None,
    not_equals: str | None = None,
    min_confidence: float,
    then: Outcome,
) -> ChoiceGate:
    """Fire when the selected option matches and confidence is at least ``min_confidence``."""
    if (equals is None) == (not_equals is None):
        raise ValueError("pass exactly one of equals= or not_equals=")
    return ChoiceGate(
        key, equals, not_equals, _unit("min_confidence", min_confidence), _outcome(then)
    )


def score_gate(
    key: str,
    *,
    gte: float | None = None,
    lte: float | None = None,
    min_confidence: float,
    then: Outcome,
) -> ScoreGate:
    """Fire when the score crosses a bound and confidence is at least ``min_confidence``.

    Bounds are on the level-index scale, 0 to n-1.
    """
    _one_bound(gte, lte)
    for name, bound in (("gte", gte), ("lte", lte)):
        if bound is not None and (isinstance(bound, bool) or not isinstance(bound, (int, float))):
            raise ValueError(f"{name} must be a number, got {bound!r}")
    return ScoreGate(
        key,
        None if gte is None else float(gte),
        None if lte is None else float(lte),
        _unit("min_confidence", min_confidence),
        _outcome(then),
    )


_GATE_QUESTION: dict[type, type] = {NoulGate: Noul, ChoiceGate: Choice, ScoreGate: Score}


@dataclass(frozen=True, kw_only=True)
class Policy:
    """Ordered rules, a default, and an explicit failure direction.

    ``on_failure="open"`` abstains when the provider fails (a router falls through to the
    LLM); ``"closed"`` escalates (a guardrail lets nothing through). There is no default.
    """

    on_failure: Literal["open", "closed"]
    rules: Sequence[Rule]
    default: Outcome
    timeout_ms: int | None = None

    def __post_init__(self) -> None:
        if self.on_failure not in ("open", "closed"):
            raise ValueError("on_failure must be 'open' or 'closed'")
        if not all(isinstance(r, (NoulGate, ChoiceGate, ScoreGate)) for r in self.rules):
            raise TypeError("rules must be built with noul_gate, choice_gate or score_gate")
        if self.timeout_ms is not None and self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        _outcome(self.default)
        object.__setattr__(self, "rules", tuple(self.rules))

    @property
    def failure_outcome(self) -> Outcome:
        return ABSTAIN if self.on_failure == "open" else ESCALATE

    def check(self, qs: QuestionSet) -> None:
        """Raise ``PolicyError`` if any rule names a missing question or the wrong primitive."""
        for rule in self.rules:
            question = qs.questions.get(rule.key)
            if question is None:
                raise PolicyError(f"{rule.describe()}: {qs.ref} has no question {rule.key!r}")
            expected = _GATE_QUESTION[type(rule)]
            if not isinstance(question, expected):
                raise PolicyError(
                    f"{rule.describe()}: {rule.key!r} in {qs.ref} is a "
                    f"{type(question).__name__}, not a {expected.__name__}"
                )
            if isinstance(rule, ChoiceGate) and isinstance(question, Choice):
                option = rule.equals if rule.equals is not None else rule.not_equals
                if option not in question.options:
                    raise PolicyError(f"{rule.describe()}: {option!r} is not an option")

    def evaluate(self, answers: Mapping[str, Answer]) -> tuple[Outcome, Rule | None]:
        """First matching rule wins; otherwise the default. Pure and deterministic."""
        for rule in self.rules:
            if rule.matches(answers[rule.key]):  # type: ignore[arg-type]
                return rule.then, rule
        return self.default, None


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    question_set: str
    answers: Mapping[str, Answer] = field(default_factory=dict)
    rule: str | None = None
    model: str | None = None
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    error: ProviderError | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None


def decide(
    qs: QuestionSet, state: Any, *, policy: Policy, provider: Provider | None = None
) -> Verdict:
    """Ask every question in ``qs`` in one request, then apply ``policy``."""
    policy.check(qs)
    provider = provider if provider is not None else default_provider()
    timeout_s = None if policy.timeout_ms is None else policy.timeout_ms / 1000
    try:
        result = provider.answer(qs, state, timeout_s=timeout_s)
    except ProviderError as exc:
        return Verdict(outcome=policy.failure_outcome, question_set=qs.ref, error=exc)

    outcome, rule = policy.evaluate(result.answers)
    return Verdict(
        outcome=outcome,
        question_set=qs.ref,
        answers=result.answers,
        rule=None if rule is None else rule.describe(),
        model=result.model,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
