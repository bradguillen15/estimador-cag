# estimador-cag

Estimador de costos con **CAG** (Cache-Augmented Generation).

## Estructura

```
estimador-cag/
├── app/
│   ├── main.py              # Entrypoint FastAPI + middleware request_id
│   ├── config.py            # Settings (pydantic-settings)
│   ├── logging_config.py    # Structlog (consola / JSON)
│   ├── prompts/             # Plantillas Jinja2 (estimation/v1/…)
│   ├── routers/             # Endpoints HTTP / SSE
│   ├── schemas/             # Contratos request/response (Pydantic)
│   ├── services/            # Caso de uso + proveedores LLM (services/llm/)
│   ├── dependencies.py      # Inyección de dependencias (Depends)
│   └── exceptions.py        # Errores de dominio → HTTP
├── tests/                   # Tests de la API (pytest, LLM siempre simulado)
├── web/                     # Frontend React + TypeScript + Tailwind (Vite)
│   └── src/
│       ├── api/             # Cliente HTTP/SSE + tipos (espejo de app/schemas)
│       ├── components/      # Sidebar, formulario, resultado, tema
│       ├── hooks/           # useEstimation (JSON/SSE), useTheme (claro/oscuro)
│       └── test/            # setup de Vitest y fixtures
├── package.json             # Scripts raíz (tests de API + UI)
├── .env                     # Secretos locales (no commitear)
├── .env.example
├── pyproject.toml
└── README.md
```

## Setup

```bash
# Desde estimador-cag/
uv sync
cp .env.example .env   # y completa OPEN_API_KEY
pnpm install
```

Requiere Python 3.13 (`uv`), Node 20+ y **pnpm 10** (el repo es un workspace de pnpm; `npm install`
está bloqueado para no tener dos lockfiles).

## Run

### Desarrollo

```bash
pnpm dev
```

Levanta la API (FastAPI con `--reload`, :8000) y la UI (Vite, http://localhost:5173)
en una sola terminal, con logs prefijados `[api]` / `[web]`. `Ctrl+C` detiene ambos, y si
uno de los dos falla (p. ej. el puerto 8000 ocupado) el otro se detiene también.

Por separado: `pnpm dev:api` y `pnpm dev:web`.

Vite hace proxy de `/api` y `/health` a `http://127.0.0.1:8000`, así que la UI usa
URLs relativas y no hace falta CORS. El formulario envía un `EstimationRequest`
a `POST /api/v1/estimate` (JSON) o `POST /api/v1/estimate/stream` (SSE) según el
interruptor de la barra lateral.

### Un solo proceso (build)

```bash
pnpm build
uv run uvicorn app.main:app
```

Si existe `web/dist`, FastAPI sirve la UI en `/` (la API, `/health` y `/docs` tienen prioridad).

## Tests

```bash
pnpm test               # API (pytest) + UI (Vitest), desde la raíz
pnpm test:watch         # UI en modo watch
pnpm test:coverage      # cobertura de ambos
```

Los tests nunca llaman al LLM real: la API usa un proveedor falso y la UI simula `web/src/api/client.ts`.

### Pre-commit

`pnpm install` instala un hook de git (Husky + lint-staged) que revisa **solo lo que vas a
commitear** y bloquea el commit si algo falla:

| Si cambias… | Se ejecuta |
|---|---|
| `app/`, `tests/`, `pyproject.toml`, `uv.lock` | toda la suite de la API (`pytest`, ~1.5 s) |
| `web/src/**/*.ts(x)` | ESLint de esos archivos + los tests de Vitest que los importan |
| config de la UI (`web/package.json`, `vite.config.ts`, `index.css`, `pnpm-lock.yaml`…) | toda la suite web |
| solo docs u otros archivos | nada |

La suite completa tarda ~11 s, así que el hook corre solo el área tocada; CI corre todo en cada PR.
Necesita `uv` y `pnpm` en el `PATH` (clientes git gráficos incluidos). Para saltarlo en una
emergencia: `git commit --no-verify` (CI igual bloqueará el merge si algo falla).

## Flujo de trabajo (PRs)

`main` está protegida: no se puede hacer push directo (tampoco los admins) y todo cambio entra por
pull request. Para mergear, el PR debe pasar los checks de CI (`.github/workflows/ci.yml`) y estar
al día con `main`:

- `api-tests` — `uv sync --locked` + `pytest`
- `web-tests` — `pnpm install --frozen-lockfile` + lint + Vitest + build (incluye type-check)

[CodeRabbit](https://coderabbit.ai) revisa cada PR con las reglas de `.coderabbit.yaml`.

## Logging

Structured logs con **structlog** en cada llamada al LLM (`llm_call_started` /
`llm_call_completed` / `llm_call_failed`), con `request_id` por request HTTP.

- `APP_ENV=development` → consola legible
- `APP_ENV=production` → JSON (una línea por evento)
- `LOG_LEVEL=INFO` (requerido en `.env`, sin default en código)

## Endpoints

| Método | Ruta | Respuesta |
|--------|------|-----------|
| `GET` | `/health` | `{"status": "ok"}` |
| `POST` | `/api/v1/estimate` | `EstimationResponse` (`text`, `prompt_version`) |
| `POST` | `/api/v1/estimate/stream` | SSE (`token` / `done` / `error`) |
| `GET` | `/api/v1/context` | `PromptContextResponse` (`prompt_version`, `examples_markdown`) |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/estimate \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "MVP web de e-commerce con catálogo, carrito y pagos Stripe",
    "project_type": "web_saas",
    "detail_level": "medium",
    "output_format": "phases_table",
    "language": "en"
  }'

# language: "es" (por defecto) | "en" — idioma de la respuesta del modelo.
# Los prompts están siempre en inglés; un valor no soportado vuelve a "es".
```
