from django.contrib import admin

from apps.rewards.models import RewardPolicy


@admin.register(RewardPolicy)
class RewardPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "merchant",
        "status",
        "merchant_retention_bps",
        "customer_share_bps",
        "min_coverage_ratio",
        "created_at",
    )
    list_filter = ("status", "merchant")
    search_fields = ("id", "merchant__id", "merchant__name")
    autocomplete_fields = ("merchant",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    list_select_related = ("merchant",)
