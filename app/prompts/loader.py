"""Carga y renderiza plantillas Jinja2 de estimación por versión."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

from app.exceptions import PromptTemplateError
from app.schemas.estimations import EstimationRequest

_PROMPTS_ROOT = Path(__file__).resolve().parent


@lru_cache
def _environment(version: str) -> Environment:
    version_dir = _PROMPTS_ROOT / "estimation" / version
    if not version_dir.is_dir():
        raise PromptTemplateError(f"Versión de prompt desconocida: {version!r}")

    return Environment(
        loader=FileSystemLoader(version_dir),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )


def _render(version: str, template: str, **context: str) -> str:
    try:
        return _environment(version).get_template(template).render(**context).strip()
    except TemplateNotFound as exc:
        raise PromptTemplateError(
            f"Falta la plantilla {exc.name!r} en estimation/{version}/"
        ) from exc


@lru_cache
def _system_prompt(version: str, language: str) -> str:
    # No request data: one prompt per (version, language). The language block goes last, so the
    # long instructions + examples prefix stays identical and cacheable across languages.
    return _render(version, "system.j2", language=language)


def render_estimation_examples(version: str) -> str:
    """Return the few-shot examples block exactly as it is injected into the system prompt."""
    return _render(version, "examples.j2")


def render_estimation_prompt(
    request: EstimationRequest,
    version: str,
    language: str = "es",
) -> tuple[str, str]:
    """Return ``(system, user)`` prompts ready for the LLM.

    Templates live under ``app/prompts/estimation/<version>/``; ``language`` is the response
    language the system prompt asks the model to answer in.
    """
    user = _render(
        version,
        "user.j2",
        description=request.description.strip(),
        project_type=request.project_type.value,
        detail_level=request.detail_level.value,
        output_format=request.output_format.value,
    )
    return _system_prompt(version, language), user
