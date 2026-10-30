import pytest

from limen import Choice, Noul, QuestionSet, Score

MIGRATION_REVIEW = QuestionSet(
    name="migration.review",
    version=3,
    questions={
        "destructive": Noul("Does this change drop, truncate or overwrite data irrecoverably?"),
        "risk": Score(
            "How risky is this change against production?",
            levels=["Trivial", "Routine", "Needs care", "Dangerous"],
        ),
        "kind": Choice(
            "What kind of change is this?",
            {"schema": "DDL changes.", "data": "DML backfills.", "other": None},
        ),
    },
)


@pytest.fixture
def qs() -> QuestionSet:
    return MIGRATION_REVIEW
