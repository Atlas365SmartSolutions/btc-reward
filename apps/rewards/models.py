from __future__ import annotations

from django.db import models


class PolicyStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    ARCHIVED = "ARCHIVED", "Archived"


class RewardPolicy(models.Model):
    """Merchant rules for retention, customer upside share, and coverage."""

    id = models.CharField(max_length=64, primary_key=True)
    merchant = models.ForeignKey("merchants.Merchant", on_delete=models.PROTECT, related_name="reward_policies")
    merchant_retention_bps = models.PositiveIntegerField()
    customer_share_bps = models.PositiveIntegerField()
    min_coverage_ratio = models.DecimalField(max_digits=8, decimal_places=4)
    status = models.CharField(max_length=32, choices=PolicyStatus.choices, default=PolicyStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reward_policy"
        indexes = [
            models.Index(fields=["merchant"], name="ix_reward_policy_merchant_id"),
            models.Index(
                fields=["merchant", "status", "-created_at", "-id"],
                name="ix_reward_policy_current",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(merchant_retention_bps__gte=0) & models.Q(merchant_retention_bps__lte=10000),
                name="ck_reward_policy_merchant_retention_bps",
            ),
            models.CheckConstraint(
                condition=models.Q(customer_share_bps__gte=0) & models.Q(customer_share_bps__lte=10000),
                name="ck_reward_policy_customer_share_bps",
            ),
            models.CheckConstraint(
                condition=models.Q(min_coverage_ratio__gt=0),
                name="ck_reward_policy_min_coverage_ratio",
            ),
            models.UniqueConstraint(
                fields=["merchant"],
                condition=models.Q(status=PolicyStatus.ACTIVE),
                name="uq_reward_policy_one_active_per_merchant",
            ),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.merchant_id} policy {self.id}"
