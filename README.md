# estimador-cag

Estimador de costos con **CAG** (Cache-Augmented Generation).

## Estructura

```
estimador-cag/
├── app/
│   ├── main.py              # Entrypoint FastAPI
│   ├── config.py            # Settings (pydantic-settings)
│   ├── routers/             # Endpoints HTTP
│   ├── schemas/             # Contratos request/response (Pydantic)
│   ├── services/            # Lógica de negocio (LLM)
│   └── context/             # Datos estáticos para el prompt
├── streamlit_app.py         # Interfaz conversacional (Streamlit)
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

API (FastAPI):

```bash
uv run uvicorn app.main:app --reload
```

Chat (Streamlit):

```bash
uv run streamlit run streamlit_app.py
```
