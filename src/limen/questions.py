"""Question primitives and named, versioned question sets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

MAX_CHOICE_OPTIONS = 255
MAX_SCORE_LEVELS = 10


def _require_instructions(kind: str, instructions: str) -> None:
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError(f"{kind} instructions must be a non-empty string")


@dataclass(frozen=True)
class Noul:
    """Does this condition hold? Answers with a probability of yes and nothing else."""

    instructions: str

    def __post_init__(self) -> None:
        _require_instructions("Noul", self.instructions)


@dataclass(frozen=True)
class Choice:
    """Which one of these? Options map a name to an optional description."""

    instructions: str
    options: Mapping[str, str | None]

    def __post_init__(self) -> None:
        _require_instructions("Choice", self.instructions)
        if not 1 <= len(self.options) <= MAX_CHOICE_OPTIONS:
            raise ValueError(f"Choice needs 1 to {MAX_CHOICE_OPTIONS} options")
        if any(not isinstance(k, str) or not k for k in self.options):
            raise ValueError("Choice option names must be non-empty strings")
        object.__setattr__(self, "options", MappingProxyType(dict(self.options)))


@dataclass(frozen=True)
class Score:
    """Where on an ordered scale? Levels run lowest to highest; the score is 0 to n-1."""

    instructions: str
    levels: Sequence[str]

    def __post_init__(self) -> None:
        _require_instructions("Score", self.instructions)
        if isinstance(self.levels, str):
            raise TypeError("Score levels must be a sequence of strings, not a string")
        levels = tuple(self.levels)
        if not 1 <= len(levels) <= MAX_SCORE_LEVELS:
            raise ValueError(f"Score needs 1 to {MAX_SCORE_LEVELS} levels")
        object.__setattr__(self, "levels", levels)

    @property
    def max_score(self) -> int:
        return len(self.levels) - 1


Question = Noul | Choice | Score


@dataclass(frozen=True)
class QuestionSet:
    """A named, versioned group of questions answered together in one request.

    Bump ``version`` whenever wording changes, so calibration never mixes the two.
    """

    name: str
    version: int
    questions: Mapping[str, Question] = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("QuestionSet name must be a non-empty string")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("QuestionSet version must be an integer >= 1")
        if not self.questions:
            raise ValueError("QuestionSet needs at least one question")
        for key, question in self.questions.items():
            if not isinstance(key, str) or not key:
                raise ValueError("question keys must be non-empty strings")
            if not isinstance(question, (Noul, Choice, Score)):
                raise TypeError(f"question {key!r} must be a Noul, Choice or Score")
        object.__setattr__(self, "questions", MappingProxyType(dict(self.questions)))

    @property
    def ref(self) -> str:
        return f"{self.name}@{self.version}"
