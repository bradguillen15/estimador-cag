"""Domain exceptions. The exception handlers in main.py translate them to HTTP responses."""


class EstimationError(Exception):
    """Base class for estimation errors. The message is safe to show to the end user."""


class PromptTemplateError(EstimationError):
    """A prompt version or template is missing: a server configuration error."""


class LLMProviderError(EstimationError):
    """The LLM provider failed (network, timeout, rate limit, empty answer…)."""
