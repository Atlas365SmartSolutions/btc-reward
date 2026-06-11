from __future__ import annotations

from django.db import models


class RewardStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCRUING = "ACCRUING", "Accruing"
    PAUSED = "PAUSED", "Paused"
    READY_FOR_PAYOUT = "READY_FOR_PAYOUT", "Ready for payout"
    PAID = "PAID", "Paid"


class RewardReceipt(models.Model):
    """Customer-facing reward position created from one BTC transaction."""

    id = models.CharField(max_length=64, primary_key=True)
    merchant = models.ForeignKey("merchants.Merchant", on_delete=models.PROTECT, related_name="reward_receipts")
    customer = models.ForeignKey("merchants.Customer", on_delete=models.PROTECT, related_name="reward_receipts")
    transaction = models.OneToOneField(
        "transactions.BtcTransaction",
        on_delete=models.PROTECT,
        related_name="reward_receipt",
    )
    status = models.CharField(max_length=32, choices=RewardStatus.choices, default=RewardStatus.PENDING)
    signed_reward_receipt_hash = models.CharField(max_length=255, blank=True, null=True)
    high_water_mark_value_usd = models.DecimalField(max_digits=18, decimal_places=8)
    merchant_coverage_ratio = models.DecimalField(max_digits=18, decimal_places=8)
    accrual_paused = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reward_receipt"
        indexes = [
            models.Index(fields=["merchant"], name="ix_reward_receipt_merchant_id"),
            models.Index(fields=["customer"], name="ix_reward_receipt_customer_id"),
            models.Index(
                fields=["merchant", "status", "-created_at", "-id"],
                name="ix_reward_receipt_ops",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(high_water_mark_value_usd__gte=0),
                name="ck_reward_receipt_high_water_mark_value_usd",
            ),
            models.CheckConstraint(
                condition=models.Q(merchant_coverage_ratio__gte=0),
                name="ck_reward_receipt_merchant_coverage_ratio",
            ),
        ]
        ordering = ["-created_at", "-id"]


class RewardCalculation(models.Model):
    """Point-in-time reward valuation for a receipt."""

    id = models.CharField(max_length=64, primary_key=True)
    reward_receipt = models.ForeignKey(RewardReceipt, on_delete=models.PROTECT, related_name="calculations")
    eligible_btc_notional_sats = models.BigIntegerField()
    basis_value_usd = models.DecimalField(max_digits=18, decimal_places=8)
    current_value_usd = models.DecimalField(max_digits=18, decimal_places=8)
    incremental_appreciation_usd = models.DecimalField(max_digits=18, decimal_places=8)
    customer_reward_usd = models.DecimalField(max_digits=18, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "reward_calculation"
        indexes = [
            models.Index(fields=["reward_receipt"], name="ix_reward_calc_receipt_id"),
            models.Index(
                fields=["reward_receipt", "-created_at", "-id"],
                name="ix_reward_calc_latest",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(eligible_btc_notional_sats__gte=0),
                name="ck_reward_calculation_eligible_btc_notional_sats",
            ),
            models.CheckConstraint(
                condition=models.Q(basis_value_usd__gte=0),
                name="ck_reward_calculation_basis_value_usd",
            ),
            models.CheckConstraint(
                condition=models.Q(current_value_usd__gte=0),
                name="ck_reward_calculation_current_value_usd",
            ),
            models.CheckConstraint(
                condition=models.Q(incremental_appreciation_usd__gte=0),
                name="ck_reward_calculation_incremental_appreciation_usd",
            ),
            models.CheckConstraint(
                condition=models.Q(customer_reward_usd__gte=0),
                name="ck_reward_calculation_customer_reward_usd",
            ),
        ]
        ordering = ["-created_at", "-id"]
