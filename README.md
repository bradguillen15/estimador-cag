# estimador-cag

Estimador de costos con **CAG** (Cache-Augmented Generation).

## Estructura

```
estimador-cag/
├── app/
│   ├── main.py              # Entrypoint FastAPI
│   ├── config.py            # Settings (pydantic-settings)
│   ├── routers/             # Endpoints HTTP / SSE
│   ├── schemas/             # Contratos request/response (Pydantic)
│   ├── services/            # Lógica de negocio (LLM)
│   └── context/             # Datos estáticos para el prompt
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

Terminal 2 — Chat (Streamlit como FE):

```bash
uv run streamlit run streamlit_app.py
```

Opcional: `ESTIMADOR_API_URL=http://127.0.0.1:8000` (default si no se define).

En el sidebar de Streamlit eliges el endpoint:

- **SSE** → `POST /api/v1/estimate/stream` (historial completo, tokens en vivo)
- **JSON** → `POST /api/v1/estimate` (solo el último mensaje, respuesta completa)

## Endpoints

| Método | Ruta | Respuesta |
|--------|------|-----------|
| `GET` | `/health` | `{"status": "ok"}` |
| `POST` | `/api/v1/estimate` | JSON con la estimación completa |
| `POST` | `/api/v1/estimate/stream` | SSE (`token` / `done` / `error`) |

```bash
curl -N -X POST http://127.0.0.1:8000/api/v1/estimate/stream \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Necesitamos un MVP web..."}]}'
```
