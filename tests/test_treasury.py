from decimal import Decimal

from apps.treasury.domain.treasury import calculate_reserve_health


def test_reserve_health_zero_liabilities() -> None:
    result = calculate_reserve_health(
        eligible_liabilities_usd=Decimal("0"),
        treasury_allocated_usd=Decimal("1000"),
        min_coverage_ratio=Decimal("1.1"),
    )

    assert result.coverage_ratio == Decimal("Infinity")
    assert result.is_healthy is True
    assert result.pause_accrual is False


def test_reserve_health_exact_threshold() -> None:
    result = calculate_reserve_health(
        eligible_liabilities_usd=Decimal("1000"),
        treasury_allocated_usd=Decimal("1100"),
        min_coverage_ratio=Decimal("1.1"),
    )

    assert result.coverage_ratio == Decimal("1.10000000")
    assert result.is_healthy is True
    assert result.pause_accrual is False


def test_reserve_health_below_threshold() -> None:
    result = calculate_reserve_health(
        eligible_liabilities_usd=Decimal("1000"),
        treasury_allocated_usd=Decimal("900"),
        min_coverage_ratio=Decimal("1.1"),
    )

    assert result.coverage_ratio == Decimal("0.90000000")
    assert result.is_healthy is False
    assert result.pause_accrual is True
