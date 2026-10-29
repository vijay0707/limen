<p align="center">
  <img src="https://raw.githubusercontent.com/OWNER/limen/main/docs/assets/brand/limen-logo.png" width="300" alt="limen">
</p>

<p align="center"><strong>Typed decisions with an explicit threshold — act, abstain, or escalate.</strong></p>

<p align="center">

[![PyPI](https://img.shields.io/pypi/v/limen.svg)](https://pypi.org/project/limen/)
[![Python](https://img.shields.io/pypi/pyversions/limen.svg)](https://pypi.org/project/limen/)
[![CI](https://github.com/OWNER/limen/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/limen/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

</p>

> **Status: alpha.** The API described below is settled in shape but not in detail, and will change before `1.0`. Pin exact versions.

---

A *limen* is the threshold at which a signal becomes detectable. Everything below it is subliminal — present, but not acted on.

That is the whole idea. [System One](https://docs.typesafe.ai) models like Jev return **calibrated probabilities**, not answers. A probability is only useful if something decides what to do with it, and that something is almost always a scatter of `if score > 0.8` scribbled across four repos with no record of why the number is `0.8`.

`limen` is that layer, done once: declared question sets, declared thresholds, an explicit abstain band, a decision log, and a calibration harness that fits the thresholds from your own outcomes instead of your gut.

```
state + questions  ──▶  provider  ──▶  probabilities  ──▶  policy  ──▶  ACT | ABSTAIN | ESCALATE
                                                            ▲
                                                   this is the part you own
```

## Install

```bash
pip install limen            # core: provider, policy, decision log
pip install limen[adk]       # + Google ADK plugin and callbacks
pip install limen[cli]       # + the calibrate / replay CLI
```

Python 3.10+. The core has no agent-framework dependency — it is just as useful inside a Kafka consumer or an Airflow task.

## Quickstart

```python
from limen import Choice, Noul, QuestionSet, Policy, decide, choice_gate, noul_gate, ACT, ESCALATE

TRIAGE = QuestionSet(
    name="support.triage", version=1,
    questions={
        "urgent": Noul("Does the ticket communicate real time pressure?"),
        "team": Choice("Which team should own this?", {
            "billing":   "Payments, invoices and refunds.",
            "technical": "Bugs, outages and integrations.",
            "other":     "Nothing above clearly fits.",
        }),
    },
)

ROUTE = Policy(
    on_failure="open",
    rules=[
        noul_gate("urgent", gte=0.90, then=ESCALATE),
        choice_gate("team", not_equals="other", min_confidence=0.85, then=ACT),
    ],
    default=ABSTAIN,        # unclear → hand it to the LLM, exactly as before
)

verdict = decide(TRIAGE, {"ticket": body, "tier": "business"}, policy=ROUTE)

match verdict.outcome:
    case ACT:      queues.route(verdict.answers["team"].choice)
    case ESCALATE: pager.page(body)
    case _:        llm_triage(body)
```

## Three outcomes, not two

A boolean throws away the most valuable thing a calibrated model gives you: the knowledge that it does not know. Every `limen` decision resolves to one of three outcomes, and the middle one is the point.

| Outcome | Meaning | Typical handling |
|---|---|---|
| `ACT` | Confident and inside policy | Take the cheap path, skip the LLM |
| `ABSTAIN` | Inside the deadband | Fall through to the slow, expensive, correct thing |
| `ESCALATE` | Confident that a human or supervisor is needed | Stop and hand off |

Without an abstain band you have bought a cheaper classifier. With one, you have bought a *router* — and the economics only work because the router knows when to recuse itself.

## Primitives are not interchangeable

| Primitive | Question | Returns |
|---|---|---|
| `Choice` | Which one of these? | selected option, probability per option, **confidence** |
| `Noul` | Does this condition hold? | probability of yes — **no confidence value** |
| `Score` | Where on an ordered scale? | probability-weighted position, probability per level, **confidence** |

Copying a `Choice` confidence threshold onto a `Noul` is the most common bug with these models, so `limen` makes it unrepresentable: `noul_gate` takes no `min_confidence`, and `choice_gate` requires one. The type checker catches it before review does.

## Question sets are versioned artifacts

Questions live in code as named, versioned objects — never inline strings at the call site:

```python
MIGRATION_REVIEW = QuestionSet(
    name="migration.review", version=3,
    questions={
        "destructive": Noul("Does this change drop, truncate or overwrite data irrecoverably?"),
        "risk": Score("How risky is this change against production?",
                      levels=["Trivial", "Routine", "Needs care", "Dangerous"]),
    },
)
```

Two consequences worth the ceremony: question wording becomes reviewable in a diff, and every logged decision carries the version it was made under — so a calibration run never mixes answers from two different wordings.

Each `decide()` call fans every question in the set out in **one request** against one shared state. That batching is the cost argument for System One models; leaving it as an optimization people remember to apply means they won't.

## Policies encode asymmetry

The cost of a false positive and a false negative are almost never equal, and the policy object is where that asymmetry is visible:

```python
MIGRATION_GATE = Policy(
    on_failure="closed",                                   # provider down → nothing auto-approves
    timeout_ms=400,
    rules=[
        noul_gate("destructive", gte=0.30, then=ESCALATE), # deliberately paranoid
        score_gate("risk", lte=1.5, min_confidence=0.80, then=ACT),
    ],
    default=ESCALATE,
)
```

`0.30` to flag a destructive change, `0.80` confidence to auto-approve one. Being wrong in those two directions costs wildly different amounts, and now that is a reviewable line rather than folklore.

### `on_failure` is required

There is no default, because there is no safe default. A router that cannot reach the provider should fall through to the LLM (`"open"`). A guardrail that cannot reach the provider must block (`"closed"`). Same library, opposite behaviour, so the caller states it.

## Google ADK

Two tiers, mirroring ADK's own structure.

**Plugin — global, every agent in the runner:**

```python
from google.adk.apps import App
from limen.adk import LoopGuard

app = App(
    name="research_assistant",
    root_agent=root_agent,
    plugins=[LoopGuard(TOOL_STEP, AGENT_LOOP, max_steps=12)],
)
```

**Callbacks — per agent:**

```python
from limen.adk import make_loop_callbacks

agent = LlmAgent(
    name="migration_reviewer",
    model="gemini-2.5-pro",
    tools=[...],
    after_tool_callback=make_loop_callbacks(TOOL_STEP, AGENT_LOOP),
)
```

`LoopGuard` replaces the two judgments that make ReAct agents spin — *did that step help* and *are we done* — with one typed call per tool result instead of another model turn. A hard step budget trips before any provider call, so a wedged loop terminates even if the provider is unreachable.

## Outside agents

The core has no ADK dependency. The same policy objects work anywhere a bounded judgment appears.

```python
# Stream processing — fan out a batch, no LLM in the path
for event, verdict in decide_many(TRIP_EVENT, [e.state for e in batch], policy=STREAM):
    if verdict.outcome is ACT:
        alerts.emit(event, verdict)
    sink.write(event, verdict.record)

# Reranking — only ambiguous queries reach the expensive judge
verdicts = decide_many(RELEVANCE, [{"query": q, "candidate": c} for c in shortlist[:15]])
confident = [v for v in verdicts if v.outcome is not ABSTAIN]
return rank(confident) if len(confident) >= 3 else llm_judge(q, shortlist)
```

## Decision log

Every call emits one structured record: question-set name and version, model version, state hash, the full probability distribution, confidence, the rule that fired, the outcome, latency and cost.

```python
Policy(..., sink=BigQuerySink("analytics.limen_decisions"))
```

Sinks ship for stdout, JSONL, BigQuery and AlloyDB; the interface is one method. This is your audit trail — *why did it escalate* has an answer with a row behind it — and it is the input to the next section.

## Calibration

Thresholds are guesses until they are fitted. Replay logged decisions against labelled outcomes:

```console
$ limen calibrate --question-set migration.review@3 --labels reviewed_migrations.parquet

  destructive   AUC 0.94   ECE 0.031
                escalate at >= 0.26 holds recall at 0.99  (current 0.30 → 0.97)
  risk          61% of changes clear risk<=1.5 at conf>=0.70;  3.1% at the current gate

  2 threshold changes suggested.  --write to apply to policies.py
```

Reliability diagrams, expected calibration error, and a suggested threshold per gate at your stated recall or precision floor. This is the feature that justifies a library rather than four copies of a helper function — nobody builds the replay harness four times.

## Providers

Configured by environment, so the same code runs against a hosted model in development and a self-hosted one where data cannot leave the network.

| Provider | Base URL | Notes |
|---|---|---|
| TypeSafe direct | `https://api.typesafe.ai/v1/systemone` | `TYPESAFE_API_KEY` |
| OpenRouter | `https://openrouter.ai/api/v1/systemone` | no separate account needed |
| Self-hosted | any compatible `/v1/systemone` | e.g. [Laya](https://github.com/NandhaKishorM/laya) |
| `FakeProvider` | — | deterministic, for tests |

```bash
export LIMEN_BASE_URL="https://openrouter.ai/api/v1/systemone"
export LIMEN_API_KEY="sk-or-v1-..."
export LIMEN_MODEL="typesafe/jev-1.13"
```

State is budgeted, truncated head-and-tail, and field-redacted before it leaves the process. The redaction list is configured once on the provider, because it is a compliance artifact rather than application logic.

## Testing

```python
from limen.testing import FakeProvider

def test_destructive_change_escalates():
    provider = FakeProvider({"destructive": 0.91, "risk": 3.2})
    verdict = decide(MIGRATION_REVIEW, {"sql": "DROP TABLE orders"},
                     policy=MIGRATION_GATE, provider=provider)
    assert verdict.outcome is ESCALATE
```

Policy logic is pure and deterministic, so the interesting behaviour — thresholds, rule precedence, failure direction, the deadband — is unit-testable with no API key, no network and no spend. Run it in CI on every commit.

## Design principles

1. **The model answers; your code decides.** Probabilities in, policy out. Nothing in this library generates prose or takes a side effect.
2. **No bare booleans.** Every decision can abstain.
3. **No magic numbers.** A threshold that cannot be traced to a calibration run is a bug.
4. **Fail direction is explicit.** Stated per policy, never inferred.
5. **Vendor-neutral.** Any compatible `/v1/systemone` endpoint, swapped by config.

## Roadmap

- [ ] Core: provider, primitives, `FakeProvider`
- [ ] Policy types and rule composition
- [ ] Decision log + sinks
- [ ] ADK plugin and callbacks
- [ ] `limen calibrate`
- [ ] Async client and batched `decide_many`
- [ ] Reliability diagrams in the CLI
- [ ] LangGraph adapter

## Contributing

Issues and PRs welcome. Run `uv sync --all-extras`, then `uv run pytest` and `uv run ruff check`. New gate types need a calibration story in the PR description, not just a test.

## License

MIT — see [LICENSE](LICENSE).

---

*Not affiliated with, endorsed by, or sponsored by TypeSafe AI. "Jev", "System One" and "TypeSafe" are trademarks of TypeSafe AI. `limen` talks to their public API under their published terms, and to any other compatible endpoint.*
