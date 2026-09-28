"""Excepciones de dominio. Los routers / handlers de main.py las traducen a HTTP."""


class EstimationError(Exception):
    """Base de los errores del flujo de estimación. Su mensaje es seguro para el cliente."""


class PromptTemplateError(EstimationError):
    """La versión de prompt o una plantilla no existe: error de configuración del servidor."""


class LLMProviderError(EstimationError):
    """El proveedor LLM falló (red, timeout, rate limit, respuesta vacía…)."""
