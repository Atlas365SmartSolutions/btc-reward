from __future__ import annotations

from django.db import models


class IngestionRequestStatus(models.TextChoices):
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class BtcTransaction(models.Model):
    """Persisted BTC purchase recorded through the ingestion workflow."""

    id = models.CharField(max_length=64, primary_key=True)
    merchant = models.ForeignKey("merchants.Merchant", on_delete=models.PROTECT, related_name="btc_transactions")
    customer = models.ForeignKey("merchants.Customer", on_delete=models.PROTECT, related_name="btc_transactions")
    reward_policy = models.ForeignKey(
        "rewards.RewardPolicy",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="btc_transactions",
    )
    sats_spent = models.BigIntegerField()
    btc_usd_price_at_purchase = models.DecimalField(max_digits=18, decimal_places=8)
    payment_external_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "btc_transaction"
        indexes = [
            models.Index(fields=["merchant"], name="ix_btc_transaction_merchant_id"),
            models.Index(fields=["customer"], name="ix_btc_transaction_customer_id"),
            models.Index(fields=["reward_policy"], name="ix_btc_tx_reward_policy_id"),
            models.Index(
                fields=["merchant", "-created_at", "-id"],
                name="ix_btc_tx_merchant_recent",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(sats_spent__gt=0),
                name="ck_btc_transaction_sats_spent",
            ),
            models.CheckConstraint(
                condition=models.Q(btc_usd_price_at_purchase__gt=0),
                name="ck_btc_transaction_btc_usd_price_at_purchase",
            ),
            models.UniqueConstraint(
                fields=["payment_external_id"],
                condition=models.Q(payment_external_id__isnull=False) & ~models.Q(payment_external_id=""),
                name="uq_btc_transaction_payment_external_id",
            ),
        ]
        ordering = ["-created_at", "-id"]


class IngestionRequest(models.Model):
    """Idempotency record for transaction creation requests."""

    id = models.CharField(max_length=64, primary_key=True)
    idempotency_key = models.CharField(max_length=255, unique=True)
    request_hash = models.CharField(max_length=128, blank=True)
    response_payload = models.JSONField(blank=True, null=True)
    transaction = models.ForeignKey(
        BtcTransaction,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="ingestion_requests",
    )
    status = models.CharField(
        max_length=32,
        choices=IngestionRequestStatus.choices,
        default=IngestionRequestStatus.COMPLETED,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ingestion_request"
        indexes = [
            models.Index(fields=["transaction"], name="ix_ingestion_req_tx_id"),
            models.Index(fields=["status", "-created_at", "-id"], name="ix_ingestion_req_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(status=IngestionRequestStatus.COMPLETED) | models.Q(transaction__isnull=False),
                name="ck_ingestion_completed_has_tx",
            ),
        ]
        ordering = ["-created_at", "-id"]
