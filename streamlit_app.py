"""Frontend Streamlit: formulario que POST /estimate (JSON o SSE)."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import httpx
import streamlit as st
from dotenv import load_dotenv

from app.context.examples import ESTIMATION_EXAMPLES
from app.schemas.estimations import (
    DetailLevel,
    EstimationRequest,
    EstimationResponse,
    OutputFormat,
    ProjectType,
)
from app.services.llm_service import PROMPT_VERSION

load_dotenv()
API_URL = os.getenv("ESTIMADOR_API_URL", "http://127.0.0.1:8000")

_PROJECT_TYPE_LABELS = {
    ProjectType.MOBILE_APP: "App móvil",
    ProjectType.WEB_SAAS: "Web / SaaS",
    ProjectType.INTERNAL_TOOL: "Herramienta interna",
    ProjectType.DATA_PIPELINE: "Pipeline de datos",
}

_DETAIL_LEVEL_LABELS = {
    DetailLevel.SUMMARY: "Resumen",
    DetailLevel.MEDIUM: "Medio",
    DetailLevel.DETAILED: "Detallado",
}

_OUTPUT_FORMAT_LABELS = {
    OutputFormat.PHASES_TABLE: "Tabla por fases",
    OutputFormat.LINE_ITEMS: "Partidas / line items",
    OutputFormat.NARRATIVE: "Narrativo",
}


def _user_content(payload: EstimationRequest) -> str:
    return (
        f"Tipo de proyecto: {payload.project_type.value}\n"
        f"Nivel de detalle: {payload.detail_level.value}\n"
        f"Formato de salida: {payload.output_format.value}\n\n"
        f"Descripción del proyecto:\n{payload.description.strip()}"
    )


def _post_estimate(payload: EstimationRequest) -> EstimationResponse:
    response = httpx.post(
        f"{API_URL}/api/v1/estimate",
        json=payload.model_dump(mode="json"),
        timeout=120.0,
    )
    response.raise_for_status()
    return EstimationResponse.model_validate(response.json())


def _stream_estimate(payload: EstimationRequest) -> Iterator[str]:
    """Yields tokens from POST /api/v1/estimate/stream."""
    with httpx.stream(
        "POST",
        f"{API_URL}/api/v1/estimate/stream",
        json={"messages": [{"role": "user", "content": _user_content(payload)}]},
        timeout=None,
    ) as response:
        response.raise_for_status()
        event_name = "message"
        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
                continue
            if not line.startswith("data:"):
                continue

            # SSE: after "data:" there is at most one protocol space.
            data = line.removeprefix("data:")
            if data.startswith(" "):
                data = data[1:]
            if event_name == "token":
                # Server sends JSON-encoded strings so "\n" and leading spaces survive
                yield json.loads(data)
            elif event_name == "error":
                detail = json.loads(data).get("detail", data)
                raise RuntimeError(detail)
            event_name = "message"


def _render_sidebar() -> bool:
    with st.sidebar:
        st.header("API")
        st.caption(f"Base URL: `{API_URL}`")
        use_stream = st.toggle(
            "Streaming (SSE)",
            value=False,
            help="Off → POST /estimate (JSON). On → POST /estimate/stream (SSE).",
        )
        mode_label = "SSE" if use_stream else "JSON"
        st.caption(f"{mode_label} — mismo formulario, distinto endpoint.")

        st.header("Contexto CAG")
        st.caption("Ejemplos inyectados en el system prompt del servidor.")
        with st.expander("Ejemplos estáticos", expanded=False):
            for index, example in enumerate(ESTIMATION_EXAMPLES, start=1):
                st.markdown(f"**Ejemplo {index}**")
                st.markdown("*Resumen de la reunión*")
                st.markdown(example["meeting_summary"].strip())
                st.markdown("*Estimación generada*")
                st.markdown(example["estimation"].strip())
                if index < len(ESTIMATION_EXAMPLES):
                    st.divider()

    return use_stream


st.set_page_config(page_title="Estimador CAG", page_icon="📋", layout="centered")
st.title("Estimador de software")
st.caption(
    "Describe el proyecto y elige tipo, detalle y formato. "
    "El formulario construye un `EstimationRequest` y lo envía al servicio."
)

use_stream = _render_sidebar()

with st.form("estimation_form"):
    description = st.text_area(
        "Descripción del proyecto",
        height=160,
        placeholder=(
            "Ej.: Necesitamos un MVP web de e-commerce con catálogo, carrito, "
            "pagos y panel de administración…"
        ),
        help="Entre 20 y 2000 caracteres.",
    )
    project_type = st.selectbox(
        "Tipo de proyecto",
        options=list(ProjectType),
        format_func=lambda value: _PROJECT_TYPE_LABELS[value],
    )
    detail_level = st.selectbox(
        "Nivel de detalle",
        options=list(DetailLevel),
        format_func=lambda value: _DETAIL_LEVEL_LABELS[value],
        index=1,
    )
    output_format = st.selectbox(
        "Formato de salida",
        options=list(OutputFormat),
        format_func=lambda value: _OUTPUT_FORMAT_LABELS[value],
    )
    submitted = st.form_submit_button("Generar estimación", type="primary")

if submitted:
    try:
        request = EstimationRequest(
            description=description.strip(),
            project_type=project_type,
            detail_level=detail_level,
            output_format=output_format,
        )
    except Exception as exc:
        st.error(f"Datos inválidos: {exc}")
    else:
        try:
            if use_stream:
                st.subheader("Estimación")
                text = st.write_stream(_stream_estimate(request))
                st.session_state["last_estimation"] = EstimationResponse(
                    text=text or "",
                    prompt_version=PROMPT_VERSION,
                )
            else:
                with st.spinner("Generando estimación…"):
                    st.session_state["last_estimation"] = _post_estimate(request)
        except httpx.ConnectError:
            st.error(
                f"No se pudo conectar a la API en `{API_URL}`. "
                "Levanta el servicio con: "
                "`uv run uvicorn app.main:app --reload`"
            )
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            try:
                detail = exc.response.json().get("detail", detail)
            except Exception:
                pass
            st.error(f"Error HTTP {exc.response.status_code}: {detail}")
        except Exception as exc:
            st.error(f"Error al generar la estimación: {exc}")

result: EstimationResponse | None = st.session_state.get("last_estimation")
if result is not None and not (submitted and use_stream):
    st.subheader("Estimación")
    st.caption(f"prompt_version: `{result.prompt_version}`")
    st.markdown(result.text)
