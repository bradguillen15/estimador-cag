"""Tests del template de estimación (Parte 4): renderizan plantillas, nunca llaman a un modelo."""

import pytest

from app.prompts.loader import PROMPT_VERSION, render_estimation_prompt
from app.schemas.estimations import EstimationRequest
from tests.conftest import VALID_REQUEST

PER_PHASE_ASSUMPTIONS = "List the assumptions per phase"


def _render(**overrides: str) -> tuple[str, str]:
    return render_estimation_prompt(EstimationRequest.model_validate({**VALID_REQUEST, **overrides}))


def test_renders_the_active_prompt_version_by_default() -> None:
    assert _render() == render_estimation_prompt(EstimationRequest.model_validate(VALID_REQUEST), PROMPT_VERSION)


# 1. The description is included literally inside its block.


@pytest.mark.parametrize(
    "description",
    [
        "Portal interno para reservar salas con calendario y avisos por email.",
        "App con <etiquetas>, comillas \"dobles\", {{ llaves }} y\nsaltos de línea: se copia tal cual.",
    ],
)
def test_description_is_rendered_verbatim_inside_the_project_description_block(description: str) -> None:
    _, user = _render(description=description)
    assert f"<project_description>\n{description}\n</project_description>" in user


# 2. The system prompt names the selected output format, and only that one.


def test_phases_table_format_is_named_in_the_system_prompt() -> None:
    system, _ = _render(output_format="phases_table")
    assert "phases_table" in system
    assert "`Phase | Tasks | Hours`" in system


def test_narrative_format_does_not_mention_phases_table() -> None:
    system, _ = _render(output_format="narrative")
    assert "phases_table" not in system
    assert "`narrative`" in system


# 3. The detailed level adds the per-phase assumptions instruction; summary does not.


def test_detailed_level_asks_for_assumptions_per_phase() -> None:
    system, _ = _render(detail_level="detailed")
    assert PER_PHASE_ASSUMPTIONS in system


def test_summary_level_does_not_ask_for_assumptions_per_phase() -> None:
    system, _ = _render(detail_level="summary")
    assert PER_PHASE_ASSUMPTIONS not in system
    assert "Detail level `summary`" in system


def test_detailed_tables_carry_assumptions_in_their_own_column() -> None:
    detailed, _ = _render(detail_level="detailed", output_format="phases_table")
    medium, _ = _render(detail_level="medium", output_format="phases_table")
    assert "`Phase | Tasks | Assumptions | Hours`" in detailed
    assert "Assumptions |" not in medium
