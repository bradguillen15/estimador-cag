# Feature: prompt-version-and-ui-defaults

## Objective
1. Course requirement "Versionado real": the estimate endpoints accept `?prompt_version=<vN>` to run
   a specific prompt version side by side (`v1/`, `v2/`, `v3/` already exist on disk).
2. UI defaults: English and dark mode by default, and the default option shown first (left) in each
   sidebar toggle.

## Scope (authorized 2026-09-30, same branch/PR `feat/litellm-provider`, one commit per task)
- T1 `?prompt_version=` optional query param on `POST /api/v1/estimate` and `/estimate/stream`
  (and `GET /api/v1/context` so the UI/examples can match). Default = `PROMPT_VERSION`.
- T2 UI defaults: `DEFAULT_RESPONSE_LANGUAGE='en'`, pre-paint script default `en`, toggles ordered
  English | Español and Dark | Light. Dark is already the default theme.

## Out of scope
- UI selector for the prompt version (not requested).
- API default response language stays `es` (the UI always sends `language`; other clients unchanged).
- Sidebar brand icon: options proposed in chat, pending user choice.

## Constraints / decisions
- Unknown or malformed version → HTTP 422 before any LLM/cache work and before SSE starts
  (validated in the dependency layer, like `get_safe_request`). Allowed versions discovered from
  `app/prompts/estimation/*/` at startup (no hardcoded list).
- The effective version flows into rendering, the exact and semantic cache keys/buckets, the
  response `prompt_version` and the SSE `done` event.
- v1 is the original Spanish prompt (no `language.j2`/`request.j2`): it must render; the language
  param does not apply to it (document). The output check may fail for older versions → not cached,
  never an error.
- TDD: off (project default). Runner: `uv run pytest`, `pnpm test:web`, `pnpm lint`, `pnpm build`.
- RDD: off (global).

## Tasks
- [x] T1 — prompt_version query param + validation + cache/response wiring + tests + README/AGENTS.
      Commit `feat(api): ...` (route: delegated writer; trigger: 2+ non-trivial files)
- [ ] T2 — UI defaults English/dark + option order + tests. Commit `feat(web): ...` (same writer)

## Acceptance criteria
- `POST /api/v1/estimate?prompt_version=v2` renders v2 and returns `prompt_version: "v2"`; no param → v3.
- `?prompt_version=v9` or `?prompt_version=../x` → 422 on both endpoints, no provider call.
- Fresh browser (no localStorage) shows English UI, dark theme, English/Dark on the left.

## Checks
`uv run pytest -q`; `pnpm test:web`; `pnpm lint`; `pnpm build`.

## Progress
- 2026-09-30: document created.
