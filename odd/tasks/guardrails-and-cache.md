# Feature: guardrails-and-cache

## Objective
Port the relevant pieces of the course reference (`../ai-engineering`, `origin/session_4_live`,
`estimator/app/`) into this API: input guardrails, an output check, an exact response cache, a
semantic response cache and prompt improvements — adapted to our Markdown + SSE flow and layering.

## Problem / why
- No protection before the LLM: prompt-injection only defended inside the prompt; PII from meeting
  notes goes straight to the provider; no moderation.
- Every identical request pays a full LLM call (Anthropic prompt caching only discounts tokens).
- Prompt v2 lacks a confidence signal, an explicit "items first, then sum" rule, discovery /
  deployment phases, and a "do not invent deadlines/stakeholders" rule.
- `description` max 2000 chars is too short for meeting notes / transcriptions.

## Scope (authorized, single PR `feat/litellm-provider`, one commit per task)
See tasks. User decision 2026-09-30: everything in this PR, separate commits.

## Out of scope
Structured JSON output (Instructor) — our contract stays Markdown over SSE. No Redis in CI (fakes).

## Constraints
- AGENTS.md layering: services never import FastAPI; routers map domain errors to status codes;
  env only in `config.py` + `.env.example`; UI strings/errors reaching UI in Spanish, code in English.
- LiteLLM stays the only LLM SDK: moderation and embeddings go through `litellm` inside
  `app/services/llm/` (rule relaxed from "only litellm.py" to "only `app/services/llm/`"; update AGENTS.md).
- Guardrails run BEFORE any cache lookup (a rejected input is never served from cache).
- Streaming: input rejection must happen before the SSE response starts (→ HTTP 400, not an SSE event).
- Only outputs that pass the output check are cached; a stream that errors is never cached.
- Cache keys include prompt version, model list, detail, format and **language**.
- Redis unavailable → log a warning and degrade to no cache; never fail the request.
- Tests never hit Redis, LiteLLM or OpenAI: in-memory fakes / patched functions.
- Pre-commit hook needs Node 24 in PATH (see Engram discovery).

## Decisions (defaults chosen by the orchestrator, reported to the user)
- Prompt-injection heuristics: English + Spanish patterns → reject (HTTP 400, Spanish message).
- PII (email, phone, IBAN): **redact** with placeholders before the LLM, do not reject.
- Moderation: `litellm.moderation` (OpenAI), toggle `MODERATION_ENABLED`, fail-open with a warning log.
- Exact cache: Redis, SHA-256 key, TTL setting; `CACHE_ENABLED` / `REDIS_URL`.
- Semantic cache: redisvl + Redis Stack, embeddings via `litellm.embedding`; disabled by default,
  `SEMANTIC_CACHE_LOG_ONLY=true` by default, threshold 0.92; embed once per request.
- Output check: closing block (total label) or insufficient-information heading present; failures
  are logged and not cached (the stream is already sent, it is not rewritten).
- Prompt v3 + `PROMPT_VERSION` bump; examples updated consistently.
- `description` max length → 20000 (API schema + `web/src/api/types.ts`).
- TDD: off (source: project default, see litellm-provider.md). Runner: `uv run pytest` / `pnpm test`.
- RDD: off (global) → ordinary checks only.

## Tasks
- [x] T1 — Prompt v3 (confidence line, items-then-sum algorithm, discovery/deploy phases, no invented
      deadlines/stakeholders) + examples + PROMPT_VERSION + tests. Commit `feat(prompts): ...`
- [ ] T2 — Input guardrails (injection es/en reject → 400, PII redaction, moderation via LiteLLM) wired
      into service for `/estimate` and `/estimate/stream` + tests. Commit `feat(guardrails): ...`
- [ ] T3 — Output check (log + mark not cacheable) + tests. Commit `feat(guardrails): ...`
- [ ] T4 — Exact Redis response cache (hit replays over SSE, store after successful stream) + settings
      + tests. Commit `feat(cache): ...`
- [ ] T5 — Semantic cache (redisvl, log_only default, LiteLLM embeddings) + settings + tests.
      Commit `feat(cache): ...`
- [ ] T6 — Description limit 20000 (schema + web mirror + tests). Commit `feat(api): ...`
- [ ] T7 — Docs: README, AGENTS.md (layer map, litellm rule, recipes), `.env.example`, architecture
      diagram. Commit `docs: ...`

Route: one delegated writer for T1–T6 (trigger: 2+ non-trivial files per task, 4+ files to map);
T7 diagram by the parent with the archify skill.

## Acceptance criteria
- Injection text → 400 on both endpoints with a Spanish message; PII never reaches the provider.
- Identical second request is served from cache (no provider call) on both endpoints.
- Redis down → requests still succeed.
- `pnpm test` passes after every commit; app boots and `/health` ok.

## Checks
`uv run pytest -q`; `pnpm test:web`; `pnpm lint`; `pnpm build` when web changes; boot + `/health`.

## Progress
- 2026-09-30: comparison done, scope accepted by the user; document created.
- 2026-09-30: T1 done (prompt v3, PROMPT_VERSION bump, examples + tests); commit hash recorded in the next task's update.
