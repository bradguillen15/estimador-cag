# estimador-cag

Estimador de costos con **CAG** (Cache-Augmented Generation).

## Estructura

```
estimador-cag/
├── app/
│   ├── main.py              # Entrypoint FastAPI
│   ├── config.py            # Settings (pydantic-settings)
│   ├── routers/             # Endpoints HTTP
│   ├── services/            # Lógica de negocio (LLM)
│   └── context/             # Datos estáticos para el prompt
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

```bash
uv run uvicorn app.main:app --reload
```
