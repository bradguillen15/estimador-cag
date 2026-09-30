"""Output check: structure of the generated Markdown and its use by the service."""

import pytest
from structlog.testing import capture_logs

from app.prompts.loader import render_estimation_prompt
from app.schemas.estimations import EstimationRequest, ResponseLanguage
from app.services.estimation_service import EstimationService
from app.services.guardrails.output import check_estimation_output
from tests.conftest import VALID_REQUEST, FakeProvider

ES, EN = ResponseLanguage.ES, ResponseLanguage.EN


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("## Estimación: X\n\n**Total estimado: 40 horas**\n**Confianza: alta — claro**", ES),
        ("## Estimate: X\n\n**Total estimate: 120 hours**", EN),
        ("## Estimación: X\nTotal estimado: 40 horas", ES),
        ("## Información insuficiente\n\n- ¿Qué plataformas?", ES),
        ("## Insufficient information\n\n- Which platforms?", EN),
    ],
)
def test_valid_answers_pass(text: str, language: ResponseLanguage) -> None:
    assert check_estimation_output(text, language).passed


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("## Estimación: X\n\n### Desglose\n1. Backend: 40 horas", ES),  # truncated before the closing block
        ("I cannot help with that.", EN),
        ("**Total estimate: 40 hours**", ES),  # wrong language labels
        ("**Total estimado: muchas horas**", ES),  # no number
        ("", ES),
    ],
)
def test_malformed_answers_fail(text: str, language: ResponseLanguage) -> None:
    check = check_estimation_output(text, language)
    assert not check.passed and check.reason


def test_labels_stay_in_sync_with_the_prompt_language_block() -> None:
    for language, label in ((ES, "**Total estimado: <N>"), (EN, "**Total estimate: <N>")):
        request = EstimationRequest.model_validate({**VALID_REQUEST, "language": language.value})
        assert label in render_estimation_prompt(request)[0]
    for language, heading in ((ES, "## Información insuficiente"), (EN, "## Insufficient information")):
        request = EstimationRequest.model_validate({**VALID_REQUEST, "language": language.value})
        assert heading in render_estimation_prompt(request)[0]


def test_service_logs_a_warning_for_a_malformed_blocking_answer() -> None:
    service = EstimationService(FakeProvider(text="respuesta sin formato"))
    request = EstimationRequest.model_validate(VALID_REQUEST)

    with capture_logs() as logs:
        assert service.generate(request) == "respuesta sin formato"  # never rewritten

    assert [log["event"] for log in logs if log["log_level"] == "warning"] == ["output_check_failed"]


def test_service_is_silent_for_a_well_formed_answer() -> None:
    service = EstimationService(FakeProvider())
    with capture_logs() as logs:
        service.generate(EstimationRequest.model_validate(VALID_REQUEST))
    assert logs == []


def test_stream_is_checked_after_completion_and_not_rewritten() -> None:
    service = EstimationService(FakeProvider(tokens=["## Estimación", ": X", "\n\ntruncated"]))
    request = EstimationRequest.model_validate(VALID_REQUEST)

    with capture_logs() as logs:
        assert "".join(service.generate_stream(request)) == "## Estimación: X\n\ntruncated"

    assert [log["event"] for log in logs] == ["output_check_failed"]


def test_stream_that_errors_is_not_output_checked() -> None:
    from app.exceptions import LLMProviderError

    service = EstimationService(FakeProvider(error=LLMProviderError("caído"), fail_after=1))
    request = EstimationRequest.model_validate(VALID_REQUEST)

    with capture_logs() as logs, pytest.raises(LLMProviderError):
        list(service.generate_stream(request))

    assert logs == []
