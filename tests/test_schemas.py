"""Validación del contrato de entrada (EstimationRequest)."""

import pytest
from pydantic import ValidationError

from app.schemas.estimations import EstimationRequest
from tests.conftest import VALID_REQUEST


def test_accepts_a_valid_request() -> None:
    request = EstimationRequest.model_validate(VALID_REQUEST)
    assert request.project_type.value == "web_saas"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", "x" * 19),
        ("description", "x" * 2001),
        ("project_type", "blockchain"),
        ("detail_level", "extreme"),
        ("output_format", "pdf"),
    ],
)
def test_rejects_out_of_contract_values(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        EstimationRequest.model_validate({**VALID_REQUEST, field: value})


def test_language_defaults_to_spanish() -> None:
    assert EstimationRequest.model_validate(VALID_REQUEST).language.value == "es"


@pytest.mark.parametrize(("sent", "expected"), [("es", "es"), ("en", "en"), ("EN", "en"), (" en ", "en")])
def test_accepts_supported_languages(sent: str, expected: str) -> None:
    request = EstimationRequest.model_validate({**VALID_REQUEST, "language": sent})
    assert request.language.value == expected


@pytest.mark.parametrize("sent", ["fr", "english", "", None, 1])
def test_unsupported_languages_fall_back_to_spanish(sent: object) -> None:
    request = EstimationRequest.model_validate({**VALID_REQUEST, "language": sent})
    assert request.language.value == "es"


def test_description_length_bounds_are_inclusive() -> None:
    EstimationRequest.model_validate({**VALID_REQUEST, "description": "x" * 20})
    EstimationRequest.model_validate({**VALID_REQUEST, "description": "x" * 2000})


@pytest.mark.parametrize("missing", ["description", "project_type", "detail_level", "output_format"])
def test_every_field_is_required(missing: str) -> None:
    payload = {key: value for key, value in VALID_REQUEST.items() if key != missing}
    with pytest.raises(ValidationError):
        EstimationRequest.model_validate(payload)
