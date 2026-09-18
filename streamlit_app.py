"""Interfaz conversacional Streamlit para el estimador CAG."""

import streamlit as st

from app.context.examples import ESTIMATION_EXAMPLES
from app.services.llm_service import GenerationMetrics, LLMService


@st.cache_resource
def get_llm_service() -> LLMService:
    """Reutiliza el mismo LLMService (system prompt CAG + API key desde .env)."""
    return LLMService()


def _render_cag_context(service: LLMService) -> None:
    with st.sidebar:
        st.header("Contexto CAG")

        with st.expander("System prompt activo", expanded=False):
            st.text_area(
                "system_prompt",
                value=service.system_prompt,
                height=320,
                disabled=True,
                label_visibility="collapsed",
            )

        with st.expander("Contexto estático (ejemplos)", expanded=False):
            st.caption(
                "Estimaciones de ejemplo inyectadas en el system prompt (CAG)."
            )
            for index, example in enumerate(ESTIMATION_EXAMPLES, start=1):
                st.markdown(f"**Ejemplo {index}**")
                st.markdown("*Resumen de la reunión*")
                st.markdown(example["meeting_summary"].strip())
                st.markdown("*Estimación generada*")
                st.markdown(example["estimation"].strip())
                if index < len(ESTIMATION_EXAMPLES):
                    st.divider()


def _render_last_call_metrics(slot) -> None:
    with slot.container():
        st.subheader("Última llamada")
        metrics: GenerationMetrics | None = st.session_state.get("last_metrics")
        if metrics is None:
            st.caption("Aún no hay llamadas en esta sesión.")
            return

        st.metric("Modelo", metrics.model)
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
    "Pega la transcripción de una reunión o continúa la conversación para ajustar la estimación."
)

llm_service = get_llm_service()
_render_cag_context(llm_service)
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
            call_metrics = GenerationMetrics(model=llm_service.model)
            estimation = st.write_stream(
                llm_service.generate_stream(
                    st.session_state.messages,
                    metrics=call_metrics,
                )
            )
            st.session_state.last_metrics = call_metrics
            _render_last_call_metrics(metrics_slot)
        except ValueError as exc:
            estimation = f"⚠️ {exc}"
            st.markdown(estimation)
        except Exception as exc:
            estimation = f"⚠️ Error al generar la estimación: {exc}"
            st.markdown(estimation)

    st.session_state.messages.append({"role": "assistant", "content": estimation})
