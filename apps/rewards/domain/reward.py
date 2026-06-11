from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal

SATS_PER_BTC = Decimal("100000000")
BPS_DENOMINATOR = Decimal("10000")
USD_SCALE = Decimal("0.00000001")
BTC_SCALE = Decimal("0.00000001")


def q_usd(value: Decimal) -> Decimal:
    """Quantize money-like values to the project-wide Decimal scale."""
    return value.quantize(USD_SCALE, rounding=ROUND_HALF_EVEN)


def q_btc(value: Decimal) -> Decimal:
    """Quantize BTC values to satoshi precision."""
    return value.quantize(BTC_SCALE, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class RewardInput:
    """Inputs required to calculate rewardable appreciation for one BTC purchase."""

    btc_spent_sats: int
    merchant_retention_bps: int
    customer_share_bps: int
    current_btc_usd_price: Decimal
    btc_usd_price_at_purchase: Decimal
    high_water_mark_value_usd: Decimal


@dataclass(frozen=True)
class RewardResult:
    """Deterministic reward calculation output persisted on reward receipts."""

    eligible_btc_notional_sats: int
    eligible_btc_notional_btc: Decimal
    current_value_usd: Decimal
    basis_value_usd: Decimal
    incremental_appreciation_usd: Decimal
    customer_reward_usd: Decimal
    next_high_water_mark_value_usd: Decimal


def calculate_reward(input_data: RewardInput) -> RewardResult:
    """Calculate the customer's share of incremental BTC appreciation.

    The merchant retention rate chooses how much of the original BTC spend is
    eligible for upside sharing. Rewards accrue only above the receipt's current
    high-water mark, which prevents paying the same appreciation twice.
    """
    eligible_btc_notional_sats = int(
        (Decimal(input_data.btc_spent_sats) * Decimal(input_data.merchant_retention_bps) / BPS_DENOMINATOR).quantize(
            Decimal("1"), rounding=ROUND_DOWN
        )
    )
    eligible_btc_notional_btc = q_btc(Decimal(eligible_btc_notional_sats) / SATS_PER_BTC)

    current_value_usd = q_usd(eligible_btc_notional_btc * input_data.current_btc_usd_price)
    basis_value_usd = q_usd(eligible_btc_notional_btc * input_data.btc_usd_price_at_purchase)
    incremental_appreciation_usd = q_usd(max(Decimal("0"), current_value_usd - input_data.high_water_mark_value_usd))
    customer_reward_usd = q_usd(incremental_appreciation_usd * Decimal(input_data.customer_share_bps) / BPS_DENOMINATOR)
    next_high_water_mark_value_usd = q_usd(max(input_data.high_water_mark_value_usd, current_value_usd))

    return RewardResult(
        eligible_btc_notional_sats=eligible_btc_notional_sats,
        eligible_btc_notional_btc=eligible_btc_notional_btc,
        current_value_usd=current_value_usd,
        basis_value_usd=basis_value_usd,
        incremental_appreciation_usd=incremental_appreciation_usd,
        customer_reward_usd=customer_reward_usd,
        next_high_water_mark_value_usd=next_high_water_mark_value_usd,
    )
