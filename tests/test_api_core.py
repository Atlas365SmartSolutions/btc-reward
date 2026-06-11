from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


def test_reward_calculate_endpoint(client) -> None:
    response = client.post(
        "/api/rewards/calculate",
        {
            "btc_spent_sats": 100000,
            "merchant_retention_bps": 5000,
            "customer_share_bps": 2000,
            "btc_usd_price_at_purchase": "60000",
            "high_water_mark_value_usd": "20",
        },
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["eligible_btc_notional_sats"] == 50000
    assert Decimal(payload["eligible_btc_notional_btc"]) == Decimal("0.00050000")
    assert Decimal(payload["customer_reward_usd"]) == Decimal("2.80000000")


def test_treasury_reserve_health_endpoint(client) -> None:
    response = client.post(
        "/api/treasury/reserve-health",
        {
            "eligible_liabilities_usd": "1000",
            "treasury_allocated_usd": "900",
            "min_coverage_ratio": "1.1",
        },
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert Decimal(payload["coverage_ratio"]) == Decimal("0.90000000")
    assert payload["is_healthy"] is False
    assert payload["pause_accrual"] is True
