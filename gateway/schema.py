from drf_spectacular.extensions import OpenApiAuthenticationExtension


class APIKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "gateway.authentication.APIKeyAuthentication"
    name = "PromptGateApiKey"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Use `Api-Key <promptgate-client-api-key>`.",
        }
