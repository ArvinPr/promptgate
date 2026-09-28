from django.contrib.auth import password_validation
from rest_framework import serializers

from accounts.models import APIKey, User


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["id", "email", "password"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        email = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class APIKeySerializer(serializers.ModelSerializer):
    active = serializers.BooleanField(source="is_active", read_only=True)

    class Meta:
        model = APIKey
        fields = [
            "id",
            "name",
            "prefix",
            "created_at",
            "last_used_at",
            "revoked_at",
            "active",
        ]
        read_only_fields = [
            "id",
            "prefix",
            "created_at",
            "last_used_at",
            "revoked_at",
            "active",
        ]


class APIKeyCreatedSerializer(APIKeySerializer):
    key = serializers.CharField(read_only=True)

    class Meta(APIKeySerializer.Meta):
        fields = [*APIKeySerializer.Meta.fields, "key"]
