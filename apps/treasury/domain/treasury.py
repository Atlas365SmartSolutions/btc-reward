from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

RATIO_SCALE = Decimal("0.00000001")


def q_ratio(value: Decimal) -> Decimal:
    """Quantize reserve coverage ratios for stable API and UI output."""
    return value.quantize(RATIO_SCALE, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class ReserveHealthResult:
    """Coverage decision for a merchant treasury reserve check."""

    coverage_ratio: Decimal
    is_healthy: bool
    pause_accrual: bool


def calculate_reserve_health(
    eligible_liabilities_usd: Decimal,
    treasury_allocated_usd: Decimal,
    min_coverage_ratio: Decimal = Decimal("1.1"),
) -> ReserveHealthResult:
    """Compare allocated treasury value against outstanding customer rewards.

    A merchant is healthy when allocated reserves meet or exceed the configured
    minimum coverage ratio. Zero liabilities are treated as infinitely covered.
    """
    if eligible_liabilities_usd == Decimal("0"):
        coverage_ratio = Decimal("Infinity")
    else:
        coverage_ratio = q_ratio(treasury_allocated_usd / eligible_liabilities_usd)

    is_healthy = coverage_ratio >= min_coverage_ratio
    return ReserveHealthResult(
        coverage_ratio=coverage_ratio,
        is_healthy=is_healthy,
        pause_accrual=not is_healthy,
    )
