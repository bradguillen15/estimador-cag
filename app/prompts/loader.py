"""Loads and renders the versioned Jinja2 estimation prompts."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

from app.exceptions import PromptTemplateError
from app.schemas.estimations import EstimationRequest

_PROMPTS_ROOT = Path(__file__).resolve().parent

# Active prompt version: the folder under estimation/ that requests are rendered with.
PROMPT_VERSION = "v3"


@lru_cache
def available_prompt_versions() -> tuple[str, ...]:
    """Versions discovered from the folders under ``estimation/`` (computed once)."""
    return tuple(sorted(p.name for p in (_PROMPTS_ROOT / "estimation").iterdir() if p.is_dir()))


@lru_cache
def _environment(version: str) -> Environment:
    version_dir = _PROMPTS_ROOT / "estimation" / version
    if not version_dir.is_dir():
        raise PromptTemplateError(f"Unknown prompt version: {version!r}")

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
            f"Missing template {exc.name!r} in estimation/{version}/"
        ) from exc


@lru_cache
def _system_prompt(version: str, detail_level: str, output_format: str, language: str) -> str:
    # Never includes the description, so there are only a few variants per version. Rules and
    # examples come first and are identical for every request (the provider caches that prefix);
    # only the short trailing blocks (request.j2, language.j2) depend on these arguments.
    return _render(
        version,
        "system.j2",
        detail_level=detail_level,
        output_format=output_format,
        language=language,
    )


def render_estimation_examples(version: str = PROMPT_VERSION) -> str:
    """Return the few-shot examples block exactly as it is injected into the system prompt."""
    return _render(version, "examples.j2")


def render_estimation_prompt(
    request: EstimationRequest,
    version: str = PROMPT_VERSION,
) -> tuple[str, str]:
    """Return ``(system, user)`` prompts ready for the LLM.

    Templates live under ``app/prompts/estimation/<version>/``. The system prompt ends with the
    instructions for the requested detail level and output format, and with an instruction to
    answer entirely in ``request.language``.
    """
    user = _render(
        version,
        "user.j2",
        description=request.description.strip(),
        project_type=request.project_type.value,
        detail_level=request.detail_level.value,
        output_format=request.output_format.value,
    )
    system = _system_prompt(
        version,
        request.detail_level.value,
        request.output_format.value,
        request.language.value,
    )
    return system, user
