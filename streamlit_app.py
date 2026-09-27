"""Frontend Streamlit: consulta la API FastAPI (JSON o SSE)."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import streamlit as st
from dotenv import load_dotenv

from app.context.examples import ESTIMATION_EXAMPLES

load_dotenv()
API_URL = os.getenv("ESTIMADOR_API_URL", "http://127.0.0.1:8000")


@dataclass
class CallMetrics:
    model: str
    provider: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_seconds: float | None = None


def _estimate_json(transcription: str) -> tuple[str, CallMetrics]:
    response = httpx.post(
        f"{API_URL}/api/v1/estimate",
        json={"transcription": transcription},
        timeout=120.0,
    )
    response.raise_for_status()
    payload = response.json()
    metrics = CallMetrics(model=payload["model"], provider=payload.get("provider"))
    return payload["estimation"], metrics


def _estimate_sse(messages: list[dict[str, str]]) -> Iterator[str]:
    """Yields text tokens; stores metrics from the `done` event in session_state."""
    with httpx.stream(
        "POST",
        f"{API_URL}/api/v1/estimate/stream",
        json={"messages": messages},
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

            data = line.removeprefix("data:").lstrip()
            if event_name == "token":
                yield data
            elif event_name == "error":
                detail = json.loads(data).get("detail", data)
                raise RuntimeError(detail)
            elif event_name == "done":
                done = json.loads(data)
                st.session_state.last_metrics = CallMetrics(
                    model=done.get("model", "—"),
                    provider=done.get("provider"),
                    input_tokens=done.get("input_tokens"),
                    output_tokens=done.get("output_tokens"),
                    latency_seconds=done.get("latency_seconds"),
                )
            event_name = "message"


def _render_sidebar() -> str:
    with st.sidebar:
        st.header("API")
        st.caption(f"Base URL: `{API_URL}`")
        mode = st.radio(
            "Endpoint",
            options=["stream", "json"],
            format_func=lambda value: {
                "stream": "SSE — /api/v1/estimate/stream",
                "json": "JSON — /api/v1/estimate",
            }[value],
            help=(
                "SSE envía el historial completo (multi-turno). "
                "JSON envía solo el último mensaje del usuario."
            ),
        )

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

    return mode


def _render_last_call_metrics(slot) -> None:
    with slot.container():
        st.subheader("Última llamada")
        metrics: CallMetrics | None = st.session_state.get("last_metrics")
        if metrics is None:
            st.caption("Aún no hay llamadas en esta sesión.")
            return

        st.metric("Modelo", metrics.model)
        if metrics.provider:
            st.metric("Provider", metrics.provider)
        st.metric(
            "Tokens entrada",
            metrics.input_tokens if metrics.input_tokens is not None else "—",
        )
        st.metric(
            "Tokens salida",
            metrics.output_tokens if metrics.output_tokens is not None else "—",
        )
        latency = (
            f"{metrics.latency_seconds:.2f} s"
            if metrics.latency_seconds is not None
            else "—"
        )
        st.metric("Tiempo de respuesta", latency)


st.set_page_config(page_title="Estimador CAG", page_icon="📋", layout="centered")
st.title("Estimador de software")
st.caption(
    "Frontend Streamlit sobre la API FastAPI. "
    "Pega una transcripción o continúa la conversación."
)

mode = _render_sidebar()
metrics_slot = st.sidebar.empty()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_metrics" not in st.session_state:
    st.session_state.last_metrics = None

_render_last_call_metrics(metrics_slot)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Transcripción o seguimiento (ej. reduce el alcance)…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            if mode == "stream":
                estimation = st.write_stream(
                    _estimate_sse(st.session_state.messages)
                )
            else:
                estimation, call_metrics = _estimate_json(prompt)
                st.session_state.last_metrics = call_metrics
                st.markdown(estimation)
            _render_last_call_metrics(metrics_slot)
        except httpx.ConnectError:
            estimation = (
                f"⚠️ No se pudo conectar a la API en `{API_URL}`. "
                "Levanta el servicio con: "
                "`uv run uvicorn app.main:app --reload`"
            )
            st.markdown(estimation)
        except Exception as exc:
            estimation = f"⚠️ Error al generar la estimación: {exc}"
            st.markdown(estimation)

    st.session_state.messages.append({"role": "assistant", "content": estimation})
