# limen — working context

Decision-policy layer over System One models (TypeSafe Jev, OpenRouter, self-hosted
Laya). Turns calibrated probabilities into governed decisions.

**Status: pre-implementation.** The README describes the intended API, not what exists.
Build order: provider + fake → policy types → decision log → ADK plugin → calibrate CLI.

## Non-negotiable design constraints

These were decided deliberately. Changing one needs a reason, not a preference.

1. **Three outcomes, never two.** Every decision is `ACT | ABSTAIN | ESCALATE`. A bare
   boolean throws away the only thing a calibrated model gives you over a classifier.
2. **Noul has no confidence value.** Choice and Score return confidence; Noul returns
   only a probability. `noul_gate` must not accept `min_confidence` and `choice_gate`
   must require it — make the mistake unrepresentable rather than documented.
3. **`on_failure` has no default.** A router falls through to the LLM when the provider
   is down (`"open"`); a guardrail blocks (`"closed"`). The caller states which.
4. **Question sets are named and versioned.** Never inline strings at the call site.
   Every logged decision carries the version it was made under, so a calibration run
   never mixes answers from two wordings.
5. **One request per decide() call.** All questions in a set fan out against one shared
   state. This is the cost argument for System One models; it is not an optimization
   to apply selectively.
6. **The model answers, the code decides.** Nothing in this library generates prose or
   performs a side effect.
7. **Thresholds come from calibration, not intuition.** A magic number with no
   calibration run behind it is a bug.

## Structure

- Core (`limen`) has **no agent-framework dependency** — it must stay usable from a
  Kafka consumer or an Airflow task.
- ADK integration is an extra (`limen[adk]`), exposing both tiers: `LoopGuard`
  (a `BasePlugin`, global on the Runner) and `make_loop_callbacks` (per-agent).
- Provider is selected by env (`LIMEN_BASE_URL`, `LIMEN_API_KEY`, `LIMEN_MODEL`), so the
  same code runs against a hosted model in dev and a self-hosted one where data cannot
  leave the network.
- State truncation and field redaction live on the provider, not at call sites — the
  redaction list is a compliance artifact.

## Distribution

Public on PyPI. This is forced by Vertex AI Agent Engine: it installs from a
`requirements` list in a managed build with no credentials for a private index, so a
private package would have to be vendored per project — exactly the drift this exists
to remove. Domain-specific question sets stay in separate private packages that depend
on this one.

## Conventions

- `uv` + hatchling, src layout, `py.typed`, Python 3.10+
- `uv run pytest`, `uv run ruff check`
- Policy logic is pure and deterministic: test it with `FakeProvider`, no network in CI
- PyPI trusted publishing via GitHub Actions OIDC — no API token in secrets
- Assets live in `docs/assets/`, never inside `src/limen/`
- README images need absolute raw.githubusercontent URLs or they break on PyPI

## Avoid

- Putting `jev` or `typesafe` in package or module names — both are TypeSafe trademarks.
  Refer to the protocol as System One. Topics and keywords are fine.
- Naming internal/employer projects in public docs or examples. Use the schema-migration
  review example instead.
- Adding a `threshold: float` shared across primitive types (see constraint 2).
