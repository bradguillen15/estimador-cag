"""Output check: did the model follow the mandatory structure?

A valid answer either ends with the closing block (its total line) or is the
insufficient-information reply. Anything else (truncated, refused, off-format) is logged and
never cached. The text itself is never rewritten: in streaming it has already been sent.

The labels mirror ``language.j2`` in the active prompt version; a test keeps them in sync.
"""

import re
from dataclasses import dataclass

from app.schemas.estimations import ResponseLanguage

_TOTAL_LABELS: dict[ResponseLanguage, str] = {
    ResponseLanguage.ES: "Total estimado",
    ResponseLanguage.EN: "Total estimate",
}
_INSUFFICIENT_HEADINGS: dict[ResponseLanguage, str] = {
    ResponseLanguage.ES: "Información insuficiente",
    ResponseLanguage.EN: "Insufficient information",
}


@dataclass(frozen=True)
class OutputCheck:
    passed: bool
    reason: str | None = None


def check_estimation_output(text: str, language: ResponseLanguage) -> OutputCheck:
    """Verifies the Markdown contains the localized total line or the insufficient-information heading."""
    total = re.compile(rf"^[ \t]*\**{re.escape(_TOTAL_LABELS[language])}\s*:\s*\**\s*\d", re.IGNORECASE | re.MULTILINE)
    insufficient = re.compile(
        rf"^[ \t]*#{{1,6}}[ \t]*{re.escape(_INSUFFICIENT_HEADINGS[language])}", re.IGNORECASE | re.MULTILINE
    )
    if total.search(text) or insufficient.search(text):
        return OutputCheck(passed=True)
    return OutputCheck(passed=False, reason="missing_total_and_insufficient_heading")
