# AGENTS.md

Operating guide for AI agents and humans working on **estimador-cag**.
Read this before writing code. It defines *where* things go, *why*, and *what "done" means*.

---

## 1. What this app is

A FastAPI service that turns a **client meeting transcript** into a **software effort estimation**,
using **CAG (Cache-Augmented Generation)**: curated historical examples are injected into the system
prompt instead of being retrieved at query time.

Single flow today:

```
POST /api/v1/estimate  →  router  →  LLMService  →  OpenAI  →  Markdown estimation
```

Everything in this document exists to keep that flow easy to extend (more providers, more endpoints,
more context sources) **without rewriting it**.

---

## 2. Stack and commands

| Item | Value |
|---|---|
| Python | 3.13 (`.python-version`) |
| Package manager | `uv` (lockfile: `uv.lock`) |
| Web | FastAPI + Uvicorn |
| Config | pydantic-settings |
| LLM SDK | `openai` |

```bash
uv sync                                    # install deps
cp .env.example .env                       # then fill the keys
uv run uvicorn app.main:app --reload       # run (http://127.0.0.1:8000/docs)
uv add <pkg>                               # add a dependency (never edit pyproject by hand)
```

**Never** commit `.env`. Any new setting must be added to `.env.example` with an empty or safe default
in the same commit.

---

## 3. Architecture

### 3.1 Layer map

```
app/
├── main.py         # Composition root: app instance, router wiring, cross-cutting concerns
├── config.py       # Settings (pydantic-settings). The ONLY place that reads env vars.
├── routers/        # HTTP layer: parse, validate, delegate, map errors to status codes
├── schemas/        # Pydantic request/response models (see §5.1 — to be extracted)
├── services/       # Business logic. Knows nothing about HTTP.
└── context/        # Static knowledge injected into prompts (the "C" in CAG)
```

### 3.2 The dependency rule

Dependencies point **inward and downward only**:

```
main → routers → services → context / config
```

- A **router** may import services and schemas. It must never build a prompt or call an SDK.
- A **service** must never import `fastapi`, never raise `HTTPException`, never see a `Request`.
- **context/** is data only. No logic, no I/O, no imports from `services` or `routers`.
- **config.py** imports nothing from the app.

If you catch yourself importing "upward", the abstraction is in the wrong layer — move it, don't
patch around it.

### 3.3 Where each concern lives

| Concern | Home | Rule |
|---|---|---|
| HTTP status codes | `routers/` | Only place that knows about 400/502/… |
| Input shape validation | `schemas/` (Pydantic) | Declarative constraints, not `if` statements in the router |
| Domain rules / errors | `services/` | Raise domain exceptions, let the router translate them |
| Prompt text & assembly | `context/` + prompt builder | Never inline a prompt string in a router |
| Provider SDK calls | `services/llm/<provider>.py` | One file per provider, one class per provider |
| Env vars & secrets | `config.py` | `os.getenv` anywhere else is a bug |

---

## 4. Principles, applied to *this* codebase

Generic principle statements are useless. These are the concrete rules they translate to here.

### 4.1 SRP — one reason to change per unit

`LLMService` currently does three jobs: build the prompt, hold provider config, and call the OpenAI
SDK. Three reasons to change. Split as work lands:

- **Prompt assembly** → `app/context/prompt_builder.py` (changes when prompt wording changes)
- **Provider call** → `app/services/llm/openai.py` (changes when the SDK changes)
- **Use case orchestration** → `app/services/estimation_service.py` (changes when the business flow changes)

A router handler stays under ~15 lines. If it grows, the logic belongs in a service.

### 4.2 OCP — open for extension, closed for modification

Adding a second LLM provider must not require editing the estimation logic.

Target structure:

```
app/services/llm/
├── base.py       # LLMProvider Protocol  (the abstraction)
├── openai.py     # OpenAIProvider
├── anthropic.py  # AnthropicProvider
└── factory.py    # get_llm_provider(settings) -> LLMProvider
```

```python
# app/services/llm/base.py
from typing import Protocol

class LLMProvider(Protocol):
    name: str
    model: str
    def complete(self, system_prompt: str, user_prompt: str) -> str: ...
```

New provider = new file + one entry in the factory map. Zero edits to the service or the router.

### 4.3 LSP — substitutability

Every `LLMProvider` implementation must honour the same contract: same return type, same failure
mode (raise `LLMProviderError`, never return `None` or an empty string), same argument meaning.
A provider that silently truncates or returns a dict breaks every caller.

### 4.4 ISP — narrow interfaces

`complete(system_prompt, user_prompt) -> str` is deliberately minimal. Do not widen the Protocol with
streaming, embeddings or tool-calling until a real caller needs them — and when one does, add a
*separate* Protocol (`StreamingLLMProvider`) rather than forcing every provider to implement dead
methods.

### 4.5 DIP — depend on abstractions, inject them

Current code instantiates at import time:

```python
# app/routers/estimations.py  ❌
llm_service = LLMService()          # runs on import, unmockable, one global instance
```

Use FastAPI's dependency injection instead:

```python
# app/dependencies.py  ✅
from functools import lru_cache
from app.config import settings
from app.services.estimation_service import EstimationService
from app.services.llm.factory import get_llm_provider

@lru_cache
def get_estimation_service() -> EstimationService:
    return EstimationService(provider=get_llm_provider(settings))
```

```python
# app/routers/estimations.py  ✅
@router.post("/estimate", response_model=EstimateResponse)
def create_estimate(
    body: EstimateRequest,
    service: Annotated[EstimationService, Depends(get_estimation_service)],
) -> EstimateResponse: ...
```

This buys three things at once: no import-time side effects, `app.dependency_overrides` in tests,
and services that receive their collaborators instead of reaching for globals.

### 4.6 DRY — one source of truth

- Env var names: `config.py` only. Mirror every one in `.env.example`.
- Prompt fragments (`_ROLE_AND_RULES`, `_OUTPUT_FORMAT`, examples): defined once in `context/`,
  never duplicated per provider.
- Response shapes: one Pydantic model per payload, reused — do not hand-build dicts.
- Error→status mapping: one place (see §6.3), not repeated `try/except` blocks per endpoint.

DRY is about *knowledge*, not characters. Two snippets that look alike but change for different
reasons should stay separate.

### 4.7 KISS — the smallest thing that holds

- No repository/ORM layer until something is actually persisted.
- No async until there is real I/O concurrency to win; the current sync handlers are correct as-is
  (FastAPI runs `def` handlers in a threadpool).
- No caching layer, message queue, or plugin registry "for later".
- Prefer a plain function over a class with one method; prefer a dict lookup over a class hierarchy.

Apply the abstractions in §4.2 **when the second case appears**, not before. The Protocol above is
justified because `LLM_PROVIDER` and `ANTROPIC_API_KEY` already exist in config — the second case is
already on the roadmap.

---

## 5. Recipes

### 5.1 Add an endpoint

1. Define request/response models in `app/schemas/<domain>.py` (extract the existing ones out of
   `routers/estimations.py` the first time you touch them).
2. Put the logic in a service method under `app/services/`.
3. Add the handler to the relevant router: validate via the schema, `Depends` the service, map
   domain errors to HTTP.
4. Register the router in `main.py` if it is new. Keep the `/api/v1` prefix.
5. Give the handler an explicit return type and `response_model`.

### 5.2 Add an LLM provider

1. Create `app/services/llm/<provider>.py` with a class implementing `LLMProvider`.
2. Register it in `factory.py`'s provider map, keyed by the `LLM_PROVIDER` value.
3. Add its API key to `config.py` **and** `.env.example`.
4. Translate SDK exceptions into `LLMProviderError` at the boundary — SDK types must not leak out.
5. Do not touch the service, the router, or the schemas.

### 5.3 Add / change prompt context (CAG)

- Examples live in `app/context/examples.py` as data, matching the existing
  `{"meeting_summary": ..., "estimation": ...}` shape.
- Keep examples **consistent with the mandatory output format** in the prompt; if they diverge, fix
  the examples rather than adding compensating instructions.
- Context grows the token bill on *every* request. Before adding an example, ask whether it teaches
  something the existing ones do not (new domain, new granularity, new edge case).
- Prompt assembly is built once at startup, not per request. Keep it that way.

### 5.4 Add a setting

`config.py` → `.env.example` → use it via injected `settings`. Give it a sensible default unless it
is a secret; a missing optional var must not crash boot (see §7).

---

## 6. Conventions

### 6.1 Style

- Type-hint every function signature, including returns (`-> dict[str, str]`, not bare `dict`).
- Modern builtin generics (`list[dict[str, str]]`), no `typing.List`.
- Module-private helpers prefixed with `_`.
- Imports: stdlib / third-party / `app.*`, separated by blank lines.
- Naming: modules and functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE`.

### 6.2 Language

Identifiers, type names and this document are **English**. Domain content — prompts, examples,
user-facing messages and module docstrings — is **Spanish**, matching the product. Do not mix within
a single string.

### 6.3 Errors

- Services raise domain exceptions from `app/exceptions.py`
  (`EmptyTranscriptError`, `LLMProviderError`, …). Never `HTTPException`.
- Routers translate them. Current mapping: invalid input → **400**, upstream LLM failure → **502**.
- Prefer a single `@app.exception_handler` per domain exception in `main.py` over repeating
  `try/except` in every handler.
- Never swallow an exception silently and never leak provider stack traces or API keys in a response
  body.

### 6.4 Docs

Update `README.md` when setup, run commands, or the directory tree change. Update **this file** when
a layer, principle-driven rule, or recipe changes.

---

## 7. Known debt

Fix these opportunistically when you touch the surrounding code; do not replicate them.

| # | Issue | Location | Fix |
|---|---|---|---|
| 1 | Typos in setting names: `open_api_key`, `antropic_api_key` | `config.py`, `.env.example` | Rename to `openai_api_key` / `anthropic_api_key` (both files, same commit) |
| 2 | All settings required → app crashes on boot with a partial `.env` | `config.py` | Defaults for `llm_provider`, `llm_model`, `app_env`, `log_level`; provider keys optional |
| 3 | `provider` hardcoded to `"openai"`, ignoring `LLM_PROVIDER` | `services/llm_service.py` | Provider factory (§4.2) |
| 4 | Service instantiated at import time in the router | `routers/estimations.py` | FastAPI `Depends` (§4.5) |
| 5 | Schemas defined inside the router module | `routers/estimations.py` | Move to `app/schemas/estimations.py` |
| 6 | `estimation` returned as an opaque Markdown blob | `routers/estimations.py` | Consider a structured response (tasks, total hours, weeks) when a consumer needs it — not before |
| 7 | No tests, no linter, no logging | repo-wide | §8 |

---

## 8. Testing and quality

Not yet set up. When adding the first test, use `pytest` + `httpx`/`TestClient`:

```bash
uv add --dev pytest pytest-asyncio httpx ruff
uv run pytest
uv run ruff check . && uv run ruff format .
```

Rules once it exists:

- Test **services** directly with a fake `LLMProvider` — never hit a real API in a test.
- Test **routers** through `TestClient` with `app.dependency_overrides` swapping the service.
- Every bug fix gets a regression test.
- Never assert on exact LLM output; assert on contract (status code, schema, error mapping).

---

## 9. Definition of done

Before finishing any change:

- [ ] Layer boundaries respected — no HTTP in services, no business logic in routers, no env reads outside `config.py`
- [ ] New behaviour is an *addition* (new file/entry), not a modification of existing working code, where §4.2 applies
- [ ] Collaborators injected, not instantiated at import time
- [ ] Type hints on every new signature; no duplicated knowledge introduced
- [ ] New settings added to `config.py` **and** `.env.example`; no secret committed
- [ ] Errors mapped to the right status codes; nothing swallowed
- [ ] `uv run uvicorn app.main:app --reload` boots and `/health` returns `{"status": "ok"}`
- [ ] `README.md` / `AGENTS.md` updated if structure or workflow changed
