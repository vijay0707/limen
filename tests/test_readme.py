"""The README examples, run against FakeProvider. If these break, the README is wrong."""

from limen import (
    ABSTAIN,
    ACT,
    ESCALATE,
    Choice,
    Noul,
    Outcome,
    Policy,
    QuestionSet,
    Score,
    choice_gate,
    decide,
    noul_gate,
    score_gate,
)
from limen.testing import FakeProvider

TRIAGE = QuestionSet(
    name="support.triage",
    version=1,
    questions={
        "urgent": Noul("Does the ticket communicate real time pressure?"),
        "team": Choice(
            "Which team should own this?",
            {
                "billing": "Payments, invoices and refunds.",
                "technical": "Bugs, outages and integrations.",
                "other": "Nothing above clearly fits.",
            },
        ),
    },
)

ROUTE = Policy(
    on_failure="open",
    rules=[
        noul_gate("urgent", gte=0.90, then=ESCALATE),
        choice_gate("team", not_equals="other", min_confidence=0.85, then=ACT),
    ],
    default=ABSTAIN,
)

MIGRATION_REVIEW = QuestionSet(
    name="migration.review",
    version=3,
    questions={
        "destructive": Noul("Does this change drop, truncate or overwrite data irrecoverably?"),
        "risk": Score(
            "How risky is this change against production?",
            levels=["Trivial", "Routine", "Needs care", "Dangerous"],
        ),
    },
)

MIGRATION_GATE = Policy(
    on_failure="closed",
    timeout_ms=400,
    rules=[
        noul_gate("destructive", gte=0.30, then=ESCALATE),
        score_gate("risk", lte=1.5, min_confidence=0.80, then=ACT),
    ],
    default=ESCALATE,
)


def route(verdict):
    match verdict.outcome:
        case Outcome.ACT:
            return f"queue:{verdict.answers['team'].choice}"
        case Outcome.ESCALATE:
            return "page"
        case _:
            return "llm"


def test_quickstart_routes():
    body = {"ticket": "Refund please", "tier": "business"}

    def go(urgent, team):
        provider = FakeProvider({"urgent": urgent, "team": team})
        return route(decide(TRIAGE, body, policy=ROUTE, provider=provider))

    assert go(0.2, ("billing", 0.9)) == "queue:billing"
    assert go(0.95, ("billing", 0.9)) == "page"
    assert go(0.2, ("billing", 0.6)) == "llm"
    assert go(0.2, ("other", 0.99)) == "llm"
    assert route(decide(TRIAGE, body, policy=ROUTE, provider=FakeProvider.failing())) == "llm"


def test_destructive_change_escalates():
    provider = FakeProvider({"destructive": 0.91, "risk": 2.8})
    verdict = decide(
        MIGRATION_REVIEW, {"sql": "DROP TABLE orders"}, policy=MIGRATION_GATE, provider=provider
    )
    assert verdict.outcome is ESCALATE


def test_routine_change_acts():
    provider = FakeProvider({"destructive": 0.02, "risk": (1.0, 0.9)})
    verdict = decide(
        MIGRATION_REVIEW, {"sql": "ADD COLUMN"}, policy=MIGRATION_GATE, provider=provider
    )
    assert verdict.outcome is ACT
