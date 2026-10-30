"""Typed answers returned by a provider."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class NoulAnswer:
    """Probability that the condition holds. There is deliberately no confidence."""

    probability: float


@dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    confidence: float
    probabilities: Mapping[str, float]


@dataclass(frozen=True)
class ScoreAnswer:
    """``score`` is the probability-weighted level index, so it can be fractional."""

    score: float
    confidence: float
    probabilities: tuple[float, ...]


Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer


@dataclass(frozen=True)
class ProviderResult:
    model: str
    answers: Mapping[str, Answer]
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
