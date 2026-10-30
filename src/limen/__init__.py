"""limen — typed decisions with an explicit threshold.

Build order (see CLAUDE.md):
    providers.py  → questions.py → policy.py → log.py → adk/ → cli.py

Implemented so far: primitives, providers, ``FakeProvider`` (``limen.testing``), policy
and ``decide``. The decision log, ADK integration and calibrate CLI are not built yet.
"""

from limen.answers import Answer, ChoiceAnswer, NoulAnswer, ProviderResult, ScoreAnswer
from limen.errors import (
    LimenError,
    PolicyError,
    ProviderError,
    ProviderRequestError,
    ProviderUnavailable,
    StateTooLarge,
)
from limen.policy import (
    ABSTAIN,
    ACT,
    ESCALATE,
    Outcome,
    Policy,
    Rule,
    Verdict,
    choice_gate,
    decide,
    noul_gate,
    score_gate,
)
from limen.providers import Provider, SystemOneProvider
from limen.questions import Choice, Noul, Question, QuestionSet, Score

__version__ = "0.0.0"
__all__ = [
    "ABSTAIN",
    "ACT",
    "ESCALATE",
    "Answer",
    "Choice",
    "ChoiceAnswer",
    "LimenError",
    "Noul",
    "NoulAnswer",
    "Outcome",
    "Policy",
    "PolicyError",
    "Provider",
    "ProviderError",
    "ProviderRequestError",
    "ProviderResult",
    "ProviderUnavailable",
    "Question",
    "QuestionSet",
    "Rule",
    "Score",
    "ScoreAnswer",
    "StateTooLarge",
    "SystemOneProvider",
    "Verdict",
    "choice_gate",
    "decide",
    "noul_gate",
    "score_gate",
]
