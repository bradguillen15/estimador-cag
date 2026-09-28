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
│   ├── services/            # Lógica de negocio (LLM)
│   └── context/             # Datos estáticos legacy (sidebar)
├── streamlit_app.py         # Frontend Streamlit (consume la API)
├── .env                     # Secretos locales (no commitear)
├── .env.example
├── pyproject.toml
└── README.md
```

## Setup

```bash
# Desde estimador-cag/
uv sync
cp .env.example .env   # y completa OPENAI_API_KEY
```

## Run

Necesitas **los dos procesos**: la API y el frontend.

Terminal 1 — API (FastAPI):

```bash
uv run uvicorn app.main:app --reload
```

Terminal 2 — Formulario (Streamlit como FE):

```bash
uv run streamlit run streamlit_app.py
```

Opcional: `ESTIMADOR_API_URL=http://127.0.0.1:8000` (default si no se define).

Streamlit envía un `EstimationRequest` (descripción + tipo + detalle + formato)
vía `POST /api/v1/estimate`.

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

```bash
curl -X POST http://127.0.0.1:8000/api/v1/estimate \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "MVP web de e-commerce con catálogo, carrito y pagos Stripe",
    "project_type": "web_saas",
    "detail_level": "medium",
    "output_format": "phases_table"
  }'
```
