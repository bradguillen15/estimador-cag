"""Carga y renderiza plantillas Jinja2 de estimación por versión."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

from app.schemas.estimations import EstimationRequest

_PROMPTS_ROOT = Path(__file__).resolve().parent


@lru_cache
def _environment(version: str) -> Environment:
    version_dir = _PROMPTS_ROOT / "estimation" / version
    if not version_dir.is_dir():
        raise ValueError(f"Versión de prompt desconocida: {version!r}")

    return Environment(
        loader=FileSystemLoader(version_dir),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )


@lru_cache
def _system_prompt(version: str) -> str:
    # Static per version: identical prefix on every request, so the provider can cache it.
    return _environment(version).get_template("system.j2").render().strip()


def render_estimation_prompt(
    request: EstimationRequest,
    version: str,
) -> tuple[str, str]:
    """Return ``(system, user)`` prompts ready for the LLM.

    Templates live under ``app/prompts/estimation/<version>/``.
    """
    context = {
        "description": request.description.strip(),
        "project_type": request.project_type.value,
        "detail_level": request.detail_level.value,
        "output_format": request.output_format.value,
    }
    try:
        system = _system_prompt(version)
        user = _environment(version).get_template("user.j2").render(**context)
    except TemplateNotFound as exc:
        raise ValueError(
            f"Falta la plantilla {exc.name!r} en estimation/{version}/"
        ) from exc

    return system, user.strip()
