# One-time setup

Delete this file once you've worked through it.

## 1. Replace the placeholder

`OWNER` appears in `README.md`, `pyproject.toml`, `mkdocs.yml` and `docs/index.md`.

```bash
grep -rl OWNER . | xargs sed -i '' 's/OWNER/your-github-handle/g'   # macOS
grep -rl OWNER . | xargs sed -i    's/OWNER/your-github-handle/g'   # Linux
```

Then set your real name in `LICENSE` and the `authors` field of `pyproject.toml`.

## 2. Reserve the name on PyPI

```bash
uv build && uv publish      # 0.0.0 placeholder, claims the name
```

Then configure trusted publishing at https://pypi.org/manage/account/publishing/
(owner, repo `limen`, workflow `publish.yml`, environment `pypi`) so no token is
ever stored in GitHub secrets.

## 3. Repo settings on GitHub

- **Description** — use the tagline verbatim.
- **Social preview** — Settings → General → upload `docs/assets/brand/social-preview.png`.
- **Topics** — `llm` `ai-agents` `google-adk` `agent-framework` `decision-making`
  `calibration` `guardrails` `llm-routing` `typed-decisions` `system-one` `jev`
  `typesafe-ai` `classification` `confidence` `python` `gemini` `cost-optimization`
  `mlops` `observability` `kafka`

## 4. Verify

```bash
uv sync --all-extras
uv run pytest -q
uv run ruff check
```

## Still missing

- Dark-background logo lockup — see "Known limitations" in `docs/brand.md`.
- `CONTRIBUTING.md`, issue templates.
- Everything in `src/limen/`. Build order is in `CLAUDE.md`.
