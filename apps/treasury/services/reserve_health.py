from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import F, Sum, Window
from django.db.models.functions import Coalesce
from django.db.models.functions.window import RowNumber

from apps.receipts.models import RewardCalculation
from apps.rewards.models import RewardPolicy
from apps.treasury.domain.treasury import calculate_reserve_health
from apps.treasury.models import TreasurySnapshot


@dataclass(frozen=True)
class MerchantReserveHealthResult:
    """Aggregated reserve position for one merchant."""

    eligible_liabilities_usd: Decimal
    treasury_allocated_usd: Decimal
    min_coverage_ratio: Decimal
    coverage_ratio: Decimal
    is_healthy: bool
    pause_accrual: bool


def get_merchant_reserve_health(*, merchant_id: str) -> MerchantReserveHealthResult:
    """Return reserve health from the latest reward and treasury records.

    Liabilities come from the latest reward calculation for each receipt.
    Treasury value comes from the latest snapshot for each merchant wallet.
    """
    eligible_liabilities_usd = RewardCalculation.objects.filter(reward_receipt__merchant_id=merchant_id).annotate(
        latest_rank=Window(
            expression=RowNumber(),
            partition_by=[F("reward_receipt_id")],
            order_by=[F("created_at").desc(), F("id").desc()],
        )
    ).filter(latest_rank=1).aggregate(total=Coalesce(Sum("customer_reward_usd"), Decimal("0")))["total"] or Decimal("0")

    treasury_allocated_usd = TreasurySnapshot.objects.filter(treasury_wallet__merchant_id=merchant_id).annotate(
        latest_rank=Window(
            expression=RowNumber(),
            partition_by=[F("treasury_wallet_id")],
            order_by=[F("created_at").desc(), F("id").desc()],
        )
    ).filter(latest_rank=1).aggregate(total=Coalesce(Sum("allocated_usd_value"), Decimal("0")))["total"] or Decimal("0")

    min_coverage_ratio = RewardPolicy.objects.filter(merchant_id=merchant_id, status="ACTIVE").order_by(
        "-created_at", "-id"
    ).values_list("min_coverage_ratio", flat=True).first() or Decimal("1.1")

    reserve = calculate_reserve_health(
        eligible_liabilities_usd=eligible_liabilities_usd,
        treasury_allocated_usd=treasury_allocated_usd,
        min_coverage_ratio=min_coverage_ratio,
    )

    return MerchantReserveHealthResult(
        eligible_liabilities_usd=eligible_liabilities_usd,
        treasury_allocated_usd=treasury_allocated_usd,
        min_coverage_ratio=min_coverage_ratio,
        coverage_ratio=reserve.coverage_ratio,
        is_healthy=reserve.is_healthy,
        pause_accrual=reserve.pause_accrual,
    )
