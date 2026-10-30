import pytest

from limen import (
    ABSTAIN,
    ACT,
    ESCALATE,
    Policy,
    PolicyError,
    ProviderRequestError,
    choice_gate,
    decide,
    noul_gate,
    score_gate,
)
from limen.testing import FakeProvider

GATE = Policy(
    on_failure="closed",
    timeout_ms=400,
    rules=[
        noul_gate("destructive", gte=0.30, then=ESCALATE),
        score_gate("risk", lte=1.5, min_confidence=0.80, then=ACT),
    ],
    default=ESCALATE,
)


def run(qs, policy, destructive=0.1, risk=(1.0, 0.9), kind=("schema", 0.9)):
    fake = FakeProvider({"destructive": destructive, "risk": risk, "kind": kind})
    return decide(qs, {"sql": "..."}, policy=policy, provider=fake), fake


@pytest.mark.parametrize(
    ("destructive", "risk", "expected", "rule"),
    [
        (0.30, (0.0, 1.0), ESCALATE, "noul_gate(destructive >= 0.3) -> ESCALATE"),
        (0.29, (1.5, 0.80), ACT, "score_gate(risk <= 1.5, confidence >= 0.8) -> ACT"),
        (0.29, (1.6, 0.99), ESCALATE, None),  # score too high -> default
        (0.29, (1.0, 0.79), ESCALATE, None),  # not confident enough -> default
    ],
)
def test_gate_boundaries(qs, destructive, risk, expected, rule):
    verdict, _ = run(qs, GATE, destructive=destructive, risk=risk)
    assert verdict.outcome is expected
    assert verdict.rule == rule
    assert verdict.question_set == "migration.review@3"
    assert not verdict.failed


def test_first_matching_rule_wins(qs):
    policy = Policy(
        on_failure="open",
        rules=[
            score_gate("risk", lte=3, min_confidence=0.5, then=ACT),
            noul_gate("destructive", gte=0.0, then=ESCALATE),
        ],
        default=ABSTAIN,
    )
    verdict, _ = run(qs, policy, destructive=0.99)
    assert verdict.outcome is ACT


def test_deadband_abstains(qs):
    policy = Policy(
        on_failure="open",
        rules=[
            noul_gate("destructive", gte=0.9, then=ESCALATE),
            noul_gate("destructive", lte=0.1, then=ACT),
        ],
        default=ABSTAIN,
    )
    assert run(qs, policy, destructive=0.5)[0].outcome is ABSTAIN
    assert run(qs, policy, destructive=0.05)[0].outcome is ACT
    assert run(qs, policy, destructive=0.95)[0].outcome is ESCALATE


def test_choice_gate_equals_and_not_equals(qs):
    def policy(**kw):
        return Policy(
            on_failure="open",
            rules=[choice_gate("kind", min_confidence=0.85, then=ACT, **kw)],
            default=ABSTAIN,
        )

    assert run(qs, policy(not_equals="other"), kind=("data", 0.9))[0].outcome is ACT
    assert run(qs, policy(not_equals="other"), kind=("other", 0.9))[0].outcome is ABSTAIN
    assert run(qs, policy(not_equals="other"), kind=("data", 0.84))[0].outcome is ABSTAIN
    assert run(qs, policy(equals="schema"), kind=("schema", 0.85))[0].outcome is ACT
    assert run(qs, policy(equals="schema"), kind=("data", 0.99))[0].outcome is ABSTAIN


def test_score_gate_gte(qs):
    policy = Policy(
        on_failure="open",
        rules=[score_gate("risk", gte=2.5, min_confidence=0.5, then=ESCALATE)],
        default=ACT,
    )
    assert run(qs, policy, risk=(2.5, 0.5))[0].outcome is ESCALATE
    assert run(qs, policy, risk=(2.4, 0.9))[0].outcome is ACT


@pytest.mark.parametrize(("on_failure", "expected"), [("open", ABSTAIN), ("closed", ESCALATE)])
def test_on_failure_direction(qs, on_failure, expected):
    policy = Policy(on_failure=on_failure, rules=[], default=ACT)
    fake = FakeProvider.failing()
    verdict = decide(qs, {}, policy=policy, provider=fake)
    assert verdict.outcome is expected
    assert verdict.failed
    assert verdict.rule is None
    assert verdict.answers == {}


def test_request_errors_also_use_on_failure(qs):
    policy = Policy(on_failure="closed", rules=[], default=ACT)
    fake = FakeProvider.failing(ProviderRequestError("413"))
    assert decide(qs, {}, policy=policy, provider=fake).outcome is ESCALATE


def test_one_provider_call_per_decide(qs):
    verdict, fake = run(qs, GATE)
    assert len(fake.calls) == 1
    assert verdict.model == "fake"


def test_timeout_is_passed_through(qs):
    seen = []

    class Spy(FakeProvider):
        def answer(self, qs, state, *, timeout_s=None):
            seen.append(timeout_s)
            return super().answer(qs, state, timeout_s=timeout_s)

    decide(qs, {}, policy=GATE, provider=Spy({"destructive": 0, "risk": 0, "kind": "data"}))
    assert seen == [0.4]


@pytest.mark.parametrize(
    "rule",
    [
        noul_gate("missing", gte=0.5, then=ACT),
        noul_gate("kind", gte=0.5, then=ACT),
        choice_gate("destructive", equals="x", min_confidence=0.5, then=ACT),
        score_gate("kind", lte=1, min_confidence=0.5, then=ACT),
        choice_gate("kind", equals="typo", min_confidence=0.5, then=ACT),
    ],
)
def test_policy_mismatch_raises_before_any_call(qs, rule):
    policy = Policy(on_failure="open", rules=[rule], default=ABSTAIN)
    fake = FakeProvider()
    with pytest.raises(PolicyError):
        decide(qs, {}, policy=policy, provider=fake)
    assert fake.calls == []


def test_noul_gate_has_no_min_confidence():
    with pytest.raises(TypeError):
        noul_gate("destructive", gte=0.5, min_confidence=0.9, then=ACT)  # type: ignore[call-arg]


def test_choice_gate_requires_min_confidence():
    with pytest.raises(TypeError):
        choice_gate("kind", equals="data", then=ACT)  # type: ignore[call-arg]


def test_score_gate_requires_min_confidence():
    with pytest.raises(TypeError):
        score_gate("risk", lte=1, then=ACT)  # type: ignore[call-arg]


def test_policy_requires_on_failure():
    with pytest.raises(TypeError):
        Policy(rules=[], default=ABSTAIN)  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        Policy(on_failure="maybe", rules=[], default=ABSTAIN)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "build",
    [
        lambda: noul_gate("d", then=ACT),
        lambda: noul_gate("d", gte=0.1, lte=0.9, then=ACT),
        lambda: noul_gate("d", gte=1.1, then=ACT),
        lambda: choice_gate("k", min_confidence=0.5, then=ACT),
        lambda: choice_gate("k", equals="a", min_confidence=1.5, then=ACT),
        lambda: score_gate("r", gte=1, min_confidence=-0.1, then=ACT),
    ],
)
def test_gate_argument_validation(build):
    with pytest.raises(ValueError):
        build()


def test_then_must_be_outcome():
    with pytest.raises(TypeError):
        noul_gate("d", gte=0.5, then="ACT")  # type: ignore[arg-type]
