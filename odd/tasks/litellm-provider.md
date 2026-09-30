# Feature: litellm-provider

## Objective
Add LiteLLM as an `LLMProvider` so the model/provider is chosen by configuration, with Anthropic
first and OpenAI as automatic fallback.

## Problem / why
- Switching provider today means writing a new provider class per SDK.
- No timeout/retry config: the OpenAI client uses SDK defaults (600 s timeout).
- User wants Anthropic as primary and OpenAI as fallback.

## Scope (authorized)
- New `app/services/llm/litellm.py` (`LiteLLMProvider`: `complete` + `stream`), registered in `factory.py`.
- Settings: ordered `LLM_MODELS` list, `LLM_TIMEOUT`, `LLM_RETRIES`, `LLM_MAX_TOKENS`; fix key typos
  (`openai_api_key`, `anthropic_api_key`), provider keys optional. Mirror in `.env.example`.
- Anthropic prompt caching on the system message (`cache_control_injection_points`).
- Tests with a faked `litellm.completion`; conftest guard against real LiteLLM calls.
- Docs: README, AGENTS.md (layer map, debt table #1), architecture diagram candidate if nodes change.

## Out of scope
Service, router, schemas and `web/` stay untouched. No Redis cache. No LiteLLM Router/proxy.

## Constraints
- AGENTS.md §4.2/§4.3: new provider = new file + factory entry; raise `LLMProviderError`, never
  return empty text; SDK exceptions must not leak.
- Streaming fallback only helps before the first chunk; mid-stream failures stay SSE `error`.
- Anthropic Sonnet 5.5 via LiteLLM: do not send `temperature`/`top_p` (non-default → 400).
  Minimum cacheable prefix 512 tokens (claude-api skill, prompt-caching.md).

## Decisions
- Default models: `anthropic/claude-sonnet-5-5` primary, `openai/<current LLM_MODEL>` fallback
  (proposed to and accepted by the user 2026-09-30).
- Cache breakpoint on the whole system message (small number of detail×format×language variants).
- TDD: off (no project/session config); source: default. Runner: `uv run pytest` (`pnpm test:api`).

## Tasks
- [x] T1 — LiteLLM provider + settings + factory + tests + docs (route: delegated writer; trigger:
      2+ non-trivial files)

## Acceptance criteria
- `LLM_PROVIDER=litellm` serves `/estimate` and `/estimate/stream` through LiteLLM with fallbacks.
- `done` event keeps token usage (incl. cached tokens) and cost.
- Errors map to `LLMProviderError` with safe Spanish messages → 502 / SSE `error`.
- `pnpm test:api` passes; app boots and `/health` returns ok.

## Checks
`uv run pytest`; boot `uv run uvicorn app.main:app` + `/health`.

## Progress
- 2026-09-30: branch `feat/litellm-provider` from `origin/main` (76de25e). Docs verified via Context7.
- T1 implemented (delegated writer). `uv run pytest -q`: 120 passed (re-run by parent). Boot ok.
  Risk: high (unassessable, untracked files) → independent verifier: PASS-with-notes, no blocking defects.
  Pending: `.env.example` (writes denied by permission settings; user decision), diagram update, commit.
  Notes (non-blocking): `error_msg=str(error)` logged raw (same as OpenAIProvider); cached tokens/cost
  reach logs and GenerationMetrics but not the SSE `done` payload (router/web change, separate decision).

- `.env.example` applied by the user.
- 2026-09-30 accepted change: user found OpenAIProvider redundant with LiteLLM → remove direct
  OpenAI path (openai.py, its tests, LLM_PROVIDER, LLM_MODEL, direct `openai` dep). Folded into T1
  before its first commit (T1 reopened, not yet committed).

- OpenAIProvider removed (delegated writer); `uv run pytest -q` all passed (re-run by parent).
- Commits: a1e78d2 feat(llm) (pre-commit api.sh + web.sh passed); 8fc802a docs(architecture),
  archify finalize: validate/deliver/check/browser-check pass. RDD: off (global) → not run.

## Next step
User decides push / PR. Optional follow-up: expose cached tokens + cost in the SSE `done` event.
