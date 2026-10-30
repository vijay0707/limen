# Changelog

All notable changes to this project are documented here.
This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Question primitives (`Noul`, `Choice`, `Score`) and named, versioned `QuestionSet`.
- `SystemOneProvider` for any `/v1/systemone` endpoint, configured from `LIMEN_*` env vars,
  with field redaction and head-and-tail truncation before anything is sent.
- `limen.testing.FakeProvider` for offline, deterministic policy tests.
- `Policy`, `noul_gate` / `choice_gate` / `score_gate`, `decide()` and `Verdict` with
  three outcomes (`ACT`, `ABSTAIN`, `ESCALATE`) and an explicit `on_failure` direction.
- Repository scaffold, brand assets, and design documentation.
