class ProviderError(Exception):
    """Base exception for generation provider failures."""


class ProviderConfigurationError(ProviderError):
    """Raised when a provider is missing required configuration."""


class ProviderRequestError(ProviderError):
    """Raised when a provider request fails."""


class ProviderResponseError(ProviderError):
    """Raised when a provider returns an unusable response."""
