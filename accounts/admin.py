from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import APIKey, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = ["email", "is_staff", "is_active", "date_joined"]
    search_fields = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "user",
        "prefix",
        "created_at",
        "last_used_at",
        "revoked_at",
    ]
    list_filter = ["created_at", "revoked_at"]
    search_fields = ["name", "prefix", "user__email"]
    readonly_fields = [
        "id",
        "user",
        "name",
        "prefix",
        "created_at",
        "last_used_at",
        "revoked_at",
    ]
    exclude = ["key_hash"]

    def has_add_permission(self, request):
        return False
