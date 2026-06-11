from __future__ import annotations

from django.db import models
from django.db.models.functions import Lower


class TimestampedModel(models.Model):
    """Abstract base for records that need creation and update timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Merchant(TimestampedModel):
    """Merchant account that owns customers, policies, rewards, and treasury."""

    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=255)
    nostr_pubkey = models.CharField(max_length=255, blank=True, null=True)
    lightning_address = models.CharField(max_length=255, blank=True, null=True)
    encrypted_nwc_uri = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "merchant"
        indexes = [
            models.Index(fields=["name"], name="ix_merchant_name"),
            models.Index(fields=["lightning_address"], name="ix_merchant_lightning_addr"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["lightning_address"],
                condition=models.Q(lightning_address__isnull=False) & ~models.Q(lightning_address=""),
                name="uq_merchant_lightning_address",
            ),
            models.UniqueConstraint(
                fields=["nostr_pubkey"],
                condition=models.Q(nostr_pubkey__isnull=False) & ~models.Q(nostr_pubkey=""),
                name="uq_merchant_nostr_pubkey",
            ),
        ]
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return self.name


class Customer(TimestampedModel):
    """Merchant-scoped customer identity for BTC reward receipts."""

    id = models.CharField(max_length=64, primary_key=True)
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name="customers")
    email = models.EmailField()
    nostr_pubkey = models.CharField(max_length=255, blank=True, null=True)
    lightning_address = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "customer"
        indexes = [
            models.Index(fields=["merchant"], name="ix_customer_merchant_id"),
            models.Index(fields=["email"], name="ix_customer_email"),
        ]
        constraints = [
            models.UniqueConstraint("merchant", Lower("email"), name="uq_customer_merchant_email_ci"),
            models.UniqueConstraint(
                fields=["merchant", "lightning_address"],
                condition=models.Q(lightning_address__isnull=False) & ~models.Q(lightning_address=""),
                name="uq_customer_merchant_lightning",
            ),
            models.UniqueConstraint(
                fields=["merchant", "nostr_pubkey"],
                condition=models.Q(nostr_pubkey__isnull=False) & ~models.Q(nostr_pubkey=""),
                name="uq_customer_merchant_nostr",
            ),
        ]
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return self.email
