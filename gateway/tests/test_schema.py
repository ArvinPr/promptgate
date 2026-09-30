from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_openapi_schema_endpoint_documents_public_api():
    response = APIClient().get(
        reverse("schema"),
        HTTP_ACCEPT="application/json",
    )

    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert "/api/auth/register/" in schema["paths"]
    assert "/api/auth/token/" in schema["paths"]
    assert "/api/auth/token/refresh/" in schema["paths"]
    assert "/api/api-keys/" in schema["paths"]
    assert "/api/v1/generate/" in schema["paths"]

    generate_operation = schema["paths"]["/api/v1/generate/"]["post"]
    assert {"PromptGateApiKey": []} in generate_operation["security"]
    response_schema = generate_operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    component_name = response_schema["$ref"].rsplit("/", 1)[-1]
    response_properties = schema["components"]["schemas"][component_name][
        "properties"
    ]
    assert {
        "request_id",
        "output",
        "provider",
        "model",
        "usage",
        "latency_ms",
        "cached",
    } <= response_properties.keys()


def test_swagger_ui_endpoint_works():
    response = APIClient().get(reverse("swagger-ui"))

    assert response.status_code == status.HTTP_200_OK
    assert b"swagger-ui" in response.content.lower()
