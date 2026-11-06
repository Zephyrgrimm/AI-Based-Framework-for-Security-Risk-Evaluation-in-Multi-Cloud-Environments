"""Domain-specific exceptions for UDGE."""

class UDGEError(Exception):
    """Base exception for all UDGE errors."""
    pass

class IngestionError(UDGEError):
    """Raised when an input document fails extraction or parsing."""
    pass

class TemplateError(UDGEError):
    """Raised when a template is malformed or missing required specifications."""
    pass

class LibreOfficeError(UDGEError):
    """Raised when LibreOffice conversion, formatting, or rendering fails."""
    pass

class ValidationError(UDGEError):
    """Raised when QA checks or structural verification fails."""
    pass

class LLMProviderError(UDGEError):
    """Raised when LLM API call fails or times out."""
    pass
