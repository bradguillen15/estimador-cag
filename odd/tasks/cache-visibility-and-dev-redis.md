# Feature: cache-visibility-and-dev-redis

## Objective
1. `pnpm dev` starts a local Redis (Docker) automatically when a cache is enabled in the config, so
   the exact/semantic cache can be exercised without manual setup.
2. The UI shows when an estimate was served from the cache, also for the blocking `/estimate` path
   (the stream path already reports `cache_hit` in its `done` event).

## Scope (authorized 2026-09-30, same branch/PR `feat/litellm-provider`, one commit per task)
- T1 `docker-compose.yml` (Redis Stack only) + `scripts/dev.mjs` starts it only when
  `CACHE_ENABLED` or `SEMANTIC_CACHE_ENABLED` is truthy (process env first, else `.env`); docs.
- T2 `cache_hit` on `EstimationResponse` (`/estimate`), mirrored in `web/src/api/types.ts`; a
  "cached" chip in `EstimationResult` (i18n en/es); tests.

## Out of scope
- Persisting Redis data policy, production deployment, auth on Redis.
- Changing `.env.example` (any needed lines are reported, not edited, by this writer).

## Constraints / decisions
- Cache detection in `dev.mjs` mirrors the app: env var wins over `.env`; booleans are truthy for
  `1, true, yes, on` (case-insensitive); values from `.env` are never printed.
- Docker missing or failing degrades to "no cache" (the app already tolerates an unreachable
  Redis); api/web still start. `docker compose stop redis` on shutdown only if the script started it.
- `cache_hit` defaults to `false` in the schema, so existing clients are unaffected.
- TDD: off (project default). Runner: `uv run pytest`, `pnpm test:web`, `pnpm lint`, `pnpm build`.
- RDD: off (global).

## Tasks
- [x] T1 — docker-compose + dev.mjs + README/AGENTS. Commit `feat(dev): ...`
      (route: delegated writer; trigger: 2+ non-trivial files)
- [x] T2 — cache_hit in `/estimate` + UI chip + tests + README. Commit `feat: ...` (same writer)

## Acceptance criteria
- With both flags false (env or `.env`), `pnpm dev` does not touch Docker.
- With a flag true, Redis is up (healthy) before api/web start; Ctrl+C stops it if we started it.
- `POST /api/v1/estimate` returns `cache_hit: true` on a repeated request, `false` otherwise.
- The result header shows a "cached"/"desde caché" chip for cache hits in streaming and JSON modes.

## Checks
`uv run pytest -q`; `pnpm test:web`; `pnpm lint`; `pnpm build`.

## Progress
- 2026-09-30: document created.
- 2026-09-30: T1 done in 061d408; T2 in 258a9ed (pytest, test:web, lint, build green). Note: two
  pytest tests (`test_cache` factory no-op, `test_semantic_cache` defaults) read the local `.env`
  and fail when it enables a cache; run with `CACHE_ENABLED=false SEMANTIC_CACHE_ENABLED=false`.
