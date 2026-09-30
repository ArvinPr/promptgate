class ProviderError(Exception):
    """Base exception for generation provider failures."""

    category = "provider"


class ProviderConfigurationError(ProviderError):
    """Raised when a provider is missing required configuration."""

    category = "configuration"


class ProviderRequestError(ProviderError):
    """Raised when a provider request fails."""

    def __init__(
        self,
        message,
        *,
        category="request",
        http_status_code=None,
        provider_error_code=None,
        provider_error_type=None,
    ):
        super().__init__(message)
        self.category = category
        self.http_status_code = http_status_code
        self.provider_error_code = provider_error_code
        self.provider_error_type = provider_error_type


class ProviderResponseError(ProviderError):
    """Raised when a provider returns an unusable response."""

    category = "response"
