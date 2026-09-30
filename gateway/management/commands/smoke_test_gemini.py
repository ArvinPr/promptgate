from django.conf import settings
from django.core.management.base import BaseCommand

from gateway.providers.exceptions import ProviderError
from gateway.providers.gemini import GeminiProvider


class Command(BaseCommand):
    help = "Run one Gemini request and print only sanitized diagnostics."

    def add_arguments(self, parser):
        parser.add_argument("prompt")

    def handle(self, *args, **options):
        model = settings.GEMINI_MODEL

        try:
            result = GeminiProvider().generate(options["prompt"])
        except ProviderError as exc:
            self.stdout.write("success: false")
            self.stdout.write(f"model: {model}")
            self.stdout.write(f"sanitized_category: {exc.category}")
            if getattr(exc, "http_status_code", None) is not None:
                self.stdout.write(f"http_status_code: {exc.http_status_code}")
            if getattr(exc, "provider_error_code", None) is not None:
                self.stdout.write(
                    f"provider_error_code: {exc.provider_error_code}"
                )
            if getattr(exc, "provider_error_type", None) is not None:
                self.stdout.write(
                    f"provider_error_type: {exc.provider_error_type}"
                )
            return

        self.stdout.write("success: true")
        self.stdout.write(f"model: {result.model}")
        self.stdout.write(f"returned_text: {result.output}")
