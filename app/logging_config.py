"""Structured logging (structlog): readable console in development, JSON in production."""

from __future__ import annotations

import logging

import structlog

from app.config import settings

# USD per 1M tokens: (input, output). Generic fallback when the model is not listed.
_MODEL_PRICES_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}
_DEFAULT_PRICE_PER_1M = (1.00, 3.00)


def estimate_cost_usd(
    model: str,
    tokens_in: int | None,
    tokens_out: int | None,
) -> float | None:
    if tokens_in is None or tokens_out is None:
        return None
    input_price, output_price = _MODEL_PRICES_PER_1M.get(model, _DEFAULT_PRICE_PER_1M)
    return round(
        (tokens_in / 1_000_000) * input_price + (tokens_out / 1_000_000) * output_price,
        6,
    )


def configure_logging() -> None:
    """Dual config: readable console in development, JSON in production."""
    log_level = settings.log_level.upper()
    level = getattr(logging, log_level, logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.EventRenamer("msg"),
    ]

    if settings.app_env == "production":
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        processors = shared_processors + [structlog.dev.ConsoleRenderer()]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
