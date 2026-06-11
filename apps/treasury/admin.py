from django.contrib import admin

from apps.treasury.models import PayoutBatch, TreasurySnapshot, TreasuryWallet


class TreasurySnapshotInline(admin.TabularInline):
    model = TreasurySnapshot
    fields = (
        "id",
        "btc_usd_price",
        "allocated_usd_value",
        "coverage_ratio",
        "snapshot_source",
        "created_at",
    )
    readonly_fields = ("id", "created_at")
    extra = 0
    show_change_link = True


@admin.register(TreasuryWallet)
class TreasuryWalletAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant", "label", "status", "btc_balance", "created_at")
    list_filter = ("status", "merchant")
    search_fields = ("id", "label", "merchant__id", "merchant__name")
    autocomplete_fields = ("merchant",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    list_select_related = ("merchant",)
    inlines = (TreasurySnapshotInline,)


@admin.register(TreasurySnapshot)
class TreasurySnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "treasury_wallet",
        "btc_usd_price",
        "allocated_usd_value",
        "coverage_ratio",
        "created_at",
    )
    list_filter = ("snapshot_source",)
    search_fields = (
        "id",
        "treasury_wallet__id",
        "treasury_wallet__merchant__id",
        "treasury_wallet__merchant__name",
    )
    autocomplete_fields = ("treasury_wallet",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    list_select_related = ("treasury_wallet", "treasury_wallet__merchant")


@admin.register(PayoutBatch)
class PayoutBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant", "status", "total_usd", "created_at")
    list_filter = ("status", "merchant")
    search_fields = ("id", "merchant__id", "merchant__name")
    autocomplete_fields = ("merchant",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    list_select_related = ("merchant",)
