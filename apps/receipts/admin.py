from django.contrib import admin

from apps.receipts.models import RewardCalculation, RewardReceipt


class RewardCalculationInline(admin.TabularInline):
    model = RewardCalculation
    fields = (
        "id",
        "eligible_btc_notional_sats",
        "basis_value_usd",
        "current_value_usd",
        "incremental_appreciation_usd",
        "customer_reward_usd",
        "created_at",
    )
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RewardReceipt)
class RewardReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "merchant",
        "customer",
        "transaction",
        "status",
        "latest_customer_reward_usd",
        "accrual_paused",
        "created_at",
    )
    list_filter = ("status", "accrual_paused", "merchant")
    search_fields = ("id", "transaction__id", "customer__email")
    autocomplete_fields = ("merchant", "customer", "transaction")
    readonly_fields = ("created_at", "updated_at", "signed_reward_receipt_hash")
    date_hierarchy = "created_at"
    list_select_related = ("merchant", "customer", "transaction")
    inlines = (RewardCalculationInline,)

    @admin.display(description="Latest reward USD")
    def latest_customer_reward_usd(self, obj: RewardReceipt):
        latest = obj.calculations.order_by("-created_at", "-id").first()
        return latest.customer_reward_usd if latest else None


@admin.register(RewardCalculation)
class RewardCalculationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reward_receipt",
        "eligible_btc_notional_sats",
        "customer_reward_usd",
        "incremental_appreciation_usd",
        "created_at",
    )
    search_fields = ("id", "reward_receipt__id", "reward_receipt__transaction__id")
    autocomplete_fields = ("reward_receipt",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    list_select_related = ("reward_receipt",)
