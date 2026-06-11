from decimal import Decimal

from apps.rewards.domain.reward import RewardInput, calculate_reward


def test_calculate_reward_high_water_mark() -> None:
    result = calculate_reward(
        RewardInput(
            btc_spent_sats=100_000,
            merchant_retention_bps=5_000,
            customer_share_bps=2_000,
            current_btc_usd_price=Decimal("80000"),
            btc_usd_price_at_purchase=Decimal("60000"),
            high_water_mark_value_usd=Decimal("20"),
        )
    )

    assert result.eligible_btc_notional_sats == 50_000
    assert result.eligible_btc_notional_btc == Decimal("0.00050000")
    assert result.current_value_usd == Decimal("40.00000000")
    assert result.basis_value_usd == Decimal("30.00000000")
    assert result.incremental_appreciation_usd == Decimal("20.00000000")
    assert result.customer_reward_usd == Decimal("4.00000000")
    assert result.next_high_water_mark_value_usd == Decimal("40.00000000")


def test_calculate_reward_below_high_water_mark() -> None:
    result = calculate_reward(
        RewardInput(
            btc_spent_sats=100_000,
            merchant_retention_bps=5_000,
            customer_share_bps=2_000,
            current_btc_usd_price=Decimal("60000"),
            btc_usd_price_at_purchase=Decimal("60000"),
            high_water_mark_value_usd=Decimal("40"),
        )
    )

    assert result.incremental_appreciation_usd == Decimal("0.00000000")
    assert result.customer_reward_usd == Decimal("0.00000000")
    assert result.next_high_water_mark_value_usd == Decimal("40.00000000")
