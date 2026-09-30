from rest_framework import serializers


class StrictCharField(serializers.CharField):
    default_error_messages = {"invalid": "Not a valid string."}

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class GenerateRequestSerializer(serializers.Serializer):
    prompt = StrictCharField(max_length=10_000, trim_whitespace=True)


class TokenUsageSerializer(serializers.Serializer):
    input_tokens = serializers.IntegerField(allow_null=True, min_value=0)
    output_tokens = serializers.IntegerField(allow_null=True, min_value=0)
    total_tokens = serializers.IntegerField(allow_null=True, min_value=0)


class GenerateResponseSerializer(serializers.Serializer):
    output = serializers.CharField()
    provider = serializers.CharField()
    model = serializers.CharField()
    request_id = serializers.CharField()
    usage = TokenUsageSerializer()
    latency_ms = serializers.IntegerField(min_value=0)
