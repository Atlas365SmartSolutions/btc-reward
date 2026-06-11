from django.contrib import admin

from apps.transactions.models import BtcTransaction, IngestionRequest


class IngestionRequestInline(admin.TabularInline):
    model = IngestionRequest
    fields = ("id", "idempotency_key", "status", "created_at", "updated_at")
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(BtcTransaction)
class BtcTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "merchant",
        "customer",
        "reward_policy",
        "sats_spent",
        "btc_usd_price_at_purchase",
        "payment_external_id",
        "created_at",
    )
    list_filter = ("merchant", "customer", "reward_policy")
    search_fields = ("id", "payment_external_id", "merchant__id", "customer__id")
    autocomplete_fields = ("merchant", "customer", "reward_policy")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    list_select_related = ("merchant", "customer", "reward_policy")
    inlines = (IngestionRequestInline,)


@admin.register(IngestionRequest)
class IngestionRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "idempotency_key",
        "transaction",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("id", "idempotency_key", "transaction__id")
    autocomplete_fields = ("transaction",)
    readonly_fields = ("created_at", "updated_at", "response_payload")
    date_hierarchy = "created_at"
    list_select_related = ("transaction",)
