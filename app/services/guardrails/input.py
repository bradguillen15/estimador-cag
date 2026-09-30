"""Input guardrails: run on the description before anything else (cache, prompt, LLM).

1. Prompt-injection heuristics (English + Spanish): reject.
2. PII redaction (emails, phones, IBANs): replace with placeholders, never reject.
3. Moderation (optional, behind ``ModerationProvider``): reject flagged content; fails open.

The heuristics are deliberately conservative: a false positive blocks a legitimate client, and the
prompt already has its own defence. They are a cheap first line, not a compliance-grade filter.
"""

import re

import structlog

from app.exceptions import InputRejectedError
from app.services.llm.base import ModerationProvider

logger = structlog.get_logger()

_INJECTION_MESSAGE = (
    "La descripción contiene instrucciones dirigidas al asistente en lugar de describir el proyecto. "
    "Reescríbela explicando solo qué quieres construir."
)
_MODERATION_MESSAGE = (
    "La descripción contiene contenido que no podemos procesar. "
    "Revísala y vuelve a intentarlo describiendo solo el proyecto."
)

_FLAGS = re.IGNORECASE
_PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, _FLAGS)
    for pattern in (
        # English
        r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+|any\s+|every\s+)?(?:of\s+)?"
        r"(?:the\s+|your\s+|these\s+|those\s+)?(?:previous|prior|above|earlier|preceding|system|initial|original|all)\s+"
        r"(?:instructions?|prompts?|rules?|guidelines?|directions?|context)\b",
        r"\bforget\s+(?:everything|all\s+(?:of\s+)?that)\b",
        r"\byou\s+are\s+now\b",
        r"\bnew\s+instructions?\s*[:.\-]",
        r"\b(?:reveal|show|print|repeat|display)\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?(?:prompt|instructions)\b",
        r"\bjailbreak\b",
        # Spanish (tú and voseo)
        r"\b(?:ignor|olvid|descart|omit)[a-záéíóúü]*\s+(?:todas?\s+)?(?:(?:las|tus|sus|esas|estas|los)\s+)?"
        r"(?:instrucciones|reglas|indicaciones|pautas|directrices|[oó]rdenes)\b",
        r"\bignor[a-záéíóúü]*\s+(?:por\s+completo\s+)?todo\s+lo\s+anterior\b",
        r"\bolvid[a-záéíóúü]*\s+(?:todo|lo\s+anterior)\b",
        r"\b(?:ahora|a\s+partir\s+de\s+ahora)\s+(?:eres|sos|serás|actúa|actuá|responde|respondé)\b",
        r"\bnuev[ao]s?\s+(?:instrucci[oó]n(?:es)?|reglas?|[oó]rdenes)\s*[:.\-]",
        r"\b(?:revela|muestra|muéstrame|imprime|repite)\s+(?:tu|el|tus|las)\s+(?:system\s+)?(?:prompt|instrucciones)\b",
        # Structural tags that try to close the description block or open a new role.
        r"</?\s*(?:system|instructions?|prompt|assistant|project_description)\s*>",
    )
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Country code + check digits + 12-30 alphanumerics, optionally grouped in blocks of four.
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b")
# Digit runs with single space/dot/dash separators; validated in ``_is_phone``.
_PHONE_CANDIDATE_RE = re.compile(r"(?<![\w.,/])\+?\d(?:[ .\-]?\d){7,18}(?!\d)")
_CURRENCY_BEFORE_RE = re.compile(r"[€$£]\s*$")
_CURRENCY_AFTER_RE = re.compile(r"^\s*(?:[€$£]|eur\b|euros?\b|usd\b|d[oó]lares\b|mxn\b|cop\b|ars\b)", re.IGNORECASE)
_DOTTED_AMOUNT_RE = re.compile(r"^\d{1,3}(?:\.\d{3}){2,}$")
_ZERO_TAIL_RE = re.compile(r"(?:[ .\-]000)+$")


def _is_phone(candidate: str, before: str, after: str) -> bool:
    digits = re.sub(r"\D", "", candidate)
    has_plus = candidate.startswith("+")
    if not (8 if has_plus else 9) <= len(digits) <= 15:
        return False
    # Money is not a phone number: "1.500.000.000", "150 000 000 €", "$ 600 000 000".
    if _DOTTED_AMOUNT_RE.match(candidate) or _ZERO_TAIL_RE.search(candidate):
        return False
    return not (_CURRENCY_BEFORE_RE.search(before) or _CURRENCY_AFTER_RE.match(after))


def redact_pii(text: str) -> tuple[str, dict[str, int]]:
    """Replaces emails, IBANs and phone numbers with placeholders; returns the text and counts."""
    counts = {"email": 0, "iban": 0, "phone": 0}

    def _sub(kind: str, placeholder: str, pattern: re.Pattern[str], value: str) -> str:
        redacted, n = pattern.subn(placeholder, value)
        counts[kind] += n
        return redacted

    text = _sub("email", "[EMAIL]", _EMAIL_RE, text)
    text = _sub("iban", "[IBAN]", _IBAN_RE, text)

    def _phone(match: re.Match[str]) -> str:
        if _is_phone(match.group(0), text[max(0, match.start() - 4) : match.start()], text[match.end() : match.end() + 12]):
            counts["phone"] += 1
            return "[PHONE]"
        return match.group(0)

    return _PHONE_CANDIDATE_RE.sub(_phone, text), {kind: n for kind, n in counts.items() if n}


class InputGuardrails:
    """Validates and sanitizes a description. ``check`` returns the text the LLM may see."""

    def __init__(self, moderator: ModerationProvider | None = None) -> None:
        self._moderator = moderator

    def check(self, description: str) -> str:
        self._reject_prompt_injection(description)
        sanitized, redactions = redact_pii(description)
        if redactions:
            logger.info("pii_redacted", **redactions)
        self._moderate(sanitized)
        return sanitized

    @staticmethod
    def _reject_prompt_injection(description: str) -> None:
        for index, pattern in enumerate(_PROMPT_INJECTION_PATTERNS):
            if pattern.search(description):
                logger.warning("input_rejected", reason="prompt_injection", pattern_index=index)
                raise InputRejectedError(_INJECTION_MESSAGE, reason="prompt_injection")

    def _moderate(self, text: str) -> None:
        if self._moderator is None:
            return
        try:
            categories = self._moderator.flagged_categories(text)
        except Exception as exc:
            # Fail open: a moderation outage must not take the estimator down.
            logger.warning("moderation_failed_open", error_type=type(exc).__name__)
            return
        if categories:
            logger.warning("input_rejected", reason="moderation", categories=categories)
            raise InputRejectedError(_MODERATION_MESSAGE, reason="moderation")
