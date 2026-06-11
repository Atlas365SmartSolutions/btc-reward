from django.contrib import admin
from django.db.models import Count

from apps.merchants.models import Customer, Merchant
from apps.rewards.models import RewardPolicy
from apps.treasury.models import TreasuryWallet


class CustomerInline(admin.TabularInline):
    model = Customer
    fields = ("id", "email", "lightning_address", "created_at")
    readonly_fields = ("id", "created_at")
    extra = 0
    show_change_link = True


class RewardPolicyInline(admin.TabularInline):
    model = RewardPolicy
    fields = (
        "id",
        "status",
        "merchant_retention_bps",
        "customer_share_bps",
        "min_coverage_ratio",
        "created_at",
    )
    readonly_fields = ("id", "created_at")
    extra = 0
    show_change_link = True


class TreasuryWalletInline(admin.TabularInline):
    model = TreasuryWallet
    fields = ("id", "label", "status", "btc_balance", "created_at")
    readonly_fields = ("id", "created_at")
    extra = 0
    show_change_link = True


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "lightning_address",
        "has_nwc_uri",
        "customer_count",
        "policy_count",
        "transaction_count",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("id", "name", "lightning_address", "nostr_pubkey")
    readonly_fields = ("created_at", "updated_at", "has_nwc_uri")
    exclude = ("encrypted_nwc_uri",)
    inlines = (CustomerInline, RewardPolicyInline, TreasuryWalletInline)
    date_hierarchy = "created_at"

    fieldsets = (
        ("Merchant", {"fields": ("id", "name", "lightning_address", "nostr_pubkey")}),
        ("Security", {"fields": ("has_nwc_uri",)}),
        ("Audit", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _customer_count=Count("customers", distinct=True),
                _policy_count=Count("reward_policies", distinct=True),
                _transaction_count=Count("btc_transactions", distinct=True),
            )
        )

    @admin.display(boolean=True, description="NWC stored")
    def has_nwc_uri(self, obj: Merchant) -> bool:
        return bool(obj.encrypted_nwc_uri)

    @admin.display(ordering="_customer_count", description="Customers")
    def customer_count(self, obj: Merchant) -> int:
        return obj._customer_count

    @admin.display(ordering="_policy_count", description="Policies")
    def policy_count(self, obj: Merchant) -> int:
        return obj._policy_count

    @admin.display(ordering="_transaction_count", description="Transactions")
    def transaction_count(self, obj: Merchant) -> int:
        return obj._transaction_count


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant", "email", "lightning_address", "created_at")
    list_filter = ("merchant",)
    search_fields = ("id", "email", "lightning_address", "nostr_pubkey")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("merchant",)
    date_hierarchy = "created_at"
