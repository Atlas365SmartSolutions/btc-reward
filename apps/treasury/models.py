from __future__ import annotations

from django.db import models


class WalletStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class PayoutStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    QUEUED = "QUEUED", "Queued"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class TreasuryWallet(models.Model):
    """Merchant treasury wallet tracked for reward reserve coverage."""

    id = models.CharField(max_length=64, primary_key=True)
    merchant = models.ForeignKey("merchants.Merchant", on_delete=models.PROTECT, related_name="treasury_wallets")
    label = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=WalletStatus.choices, default=WalletStatus.ACTIVE)
    btc_balance = models.DecimalField(max_digits=28, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "treasury_wallet"
        indexes = [
            models.Index(fields=["merchant"], name="ix_treasury_wallet_merchant_id"),
            models.Index(
                fields=["merchant", "status", "-created_at", "-id"],
                name="ix_treasury_wallet_ops",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(btc_balance__gte=0),
                name="ck_treasury_wallet_btc_balance",
            ),
            models.UniqueConstraint(fields=["merchant", "label"], name="uq_treasury_wallet_merchant_label"),
        ]
        ordering = ["-created_at", "-id"]


class TreasurySnapshot(models.Model):
    """Point-in-time wallet valuation used for reserve health checks."""

    id = models.CharField(max_length=64, primary_key=True)
    treasury_wallet = models.ForeignKey(TreasuryWallet, on_delete=models.PROTECT, related_name="snapshots")
    btc_usd_price = models.DecimalField(max_digits=18, decimal_places=8)
    allocated_usd_value = models.DecimalField(max_digits=18, decimal_places=8)
    coverage_ratio = models.DecimalField(max_digits=18, decimal_places=8)
    snapshot_source = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "treasury_snapshot"
        indexes = [
            models.Index(fields=["treasury_wallet"], name="ix_treasury_snap_wallet_id"),
            models.Index(
                fields=["treasury_wallet", "-created_at", "-id"],
                name="ix_treasury_snap_latest",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(btc_usd_price__gt=0),
                name="ck_treasury_snapshot_btc_usd_price",
            ),
            models.CheckConstraint(
                condition=models.Q(allocated_usd_value__gte=0),
                name="ck_treasury_snapshot_allocated_usd_value",
            ),
            models.CheckConstraint(
                condition=models.Q(coverage_ratio__gte=0),
                name="ck_treasury_snapshot_coverage_ratio",
            ),
        ]
        ordering = ["-created_at", "-id"]


class PayoutBatch(models.Model):
    """Merchant payout batch for reward settlement operations."""

    id = models.CharField(max_length=64, primary_key=True)
    merchant = models.ForeignKey("merchants.Merchant", on_delete=models.PROTECT, related_name="payout_batches")
    status = models.CharField(max_length=32, choices=PayoutStatus.choices, default=PayoutStatus.DRAFT)
    total_usd = models.DecimalField(max_digits=18, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payout_batch"
        indexes = [
            models.Index(fields=["merchant"], name="ix_payout_batch_merchant_id"),
            models.Index(
                fields=["merchant", "status", "-created_at", "-id"],
                name="ix_payout_batch_ops",
            ),
        ]
        constraints = [models.CheckConstraint(condition=models.Q(total_usd__gte=0), name="ck_payout_batch_total_usd")]
        ordering = ["-created_at", "-id"]
