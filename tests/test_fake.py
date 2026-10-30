import pytest

from limen import ChoiceAnswer, NoulAnswer, ProviderRequestError, ProviderUnavailable, ScoreAnswer
from limen.testing import FakeProvider


def test_shorthand_values(qs):
    result = FakeProvider({"destructive": 0.3, "risk": 1.25, "kind": "data"}).answer(qs, {})
    assert result.answers["destructive"] == NoulAnswer(0.3)
    risk = result.answers["risk"]
    assert isinstance(risk, ScoreAnswer)
    assert risk.confidence == 1.0
    assert risk.probabilities == (0.0, 0.75, 0.25, 0.0)
    assert sum(i * p for i, p in enumerate(risk.probabilities)) == pytest.approx(1.25)
    kind = result.answers["kind"]
    assert isinstance(kind, ChoiceAnswer)
    assert (kind.choice, kind.confidence) == ("data", 1.0)


def test_tuple_values_carry_confidence(qs):
    result = FakeProvider({"destructive": 0.3, "risk": (3, 0.6), "kind": ("schema", 0.7)}).answer(
        qs, {}
    )
    assert result.answers["risk"].confidence == 0.6
    assert result.answers["risk"].probabilities[3] == 1.0
    assert result.answers["kind"].confidence == 0.7


def test_answer_objects_pass_through(qs):
    kind = ChoiceAnswer("other", 0.4, {"schema": 0.3, "data": 0.3, "other": 0.4})
    result = FakeProvider({"destructive": 0.1, "risk": 0, "kind": kind}).answer(qs, {})
    assert result.answers["kind"] is kind


@pytest.mark.parametrize(
    "values",
    [
        {"destructive": 1.5, "risk": 0, "kind": "data"},
        {"destructive": 0.1, "risk": 3.2, "kind": "data"},
        {"destructive": 0.1, "risk": (1, 1.2), "kind": "data"},
        {"destructive": 0.1, "risk": 1, "kind": "nope"},
    ],
)
def test_out_of_range_values_rejected(qs, values):
    with pytest.raises(ValueError):
        FakeProvider(values).answer(qs, {})


def test_noul_tuple_rejected(qs):
    with pytest.raises(TypeError, match="no confidence"):
        FakeProvider({"destructive": (0.9, 0.9), "risk": 0, "kind": "data"}).answer(qs, {})


def test_missing_key_names_the_key(qs):
    with pytest.raises(KeyError, match="kind"):
        FakeProvider({"destructive": 0.1, "risk": 0}).answer(qs, {})


def test_failing_records_call_and_raises(qs):
    fake = FakeProvider.failing()
    with pytest.raises(ProviderUnavailable):
        fake.answer(qs, {"a": 1})
    assert fake.calls == [(qs, {"a": 1})]
    with pytest.raises(ProviderRequestError):
        FakeProvider.failing(ProviderRequestError("bad")).answer(qs, {})
