import pytest

from limen import Choice, Noul, QuestionSet, Score


def test_ref_carries_name_and_version(qs):
    assert qs.ref == "migration.review@3"


def test_question_set_is_immutable(qs):
    with pytest.raises(TypeError):
        qs.questions["new"] = Noul("x?")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "", "version": 1, "questions": {"a": Noul("x?")}},
        {"name": "s", "version": 0, "questions": {"a": Noul("x?")}},
        {"name": "s", "version": True, "questions": {"a": Noul("x?")}},
        {"name": "s", "version": 1, "questions": {}},
        {"name": "s", "version": 1, "questions": {"": Noul("x?")}},
    ],
)
def test_question_set_validation(kwargs):
    with pytest.raises(ValueError):
        QuestionSet(**kwargs)


def test_question_set_rejects_non_primitive():
    with pytest.raises(TypeError):
        QuestionSet(name="s", version=1, questions={"a": "Is it?"})


def test_choice_option_limits():
    with pytest.raises(ValueError):
        Choice("Which?", {})
    with pytest.raises(ValueError):
        Choice("Which?", {f"o{i}": None for i in range(256)})
    assert len(Choice("Which?", {f"o{i}": None for i in range(255)}).options) == 255


def test_score_level_limits():
    with pytest.raises(ValueError):
        Score("How?", levels=[])
    with pytest.raises(ValueError):
        Score("How?", levels=[str(i) for i in range(11)])
    with pytest.raises(TypeError):
        Score("How?", levels="abc")
    assert Score("How?", levels=["a", "b", "c"]).max_score == 2


def test_empty_instructions_rejected():
    with pytest.raises(ValueError):
        Noul("   ")
