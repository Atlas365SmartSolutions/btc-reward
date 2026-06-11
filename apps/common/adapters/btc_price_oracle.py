from __future__ import annotations

from decimal import Decimal


class BtcPriceOracle:
    """Interface for BTC/USD spot price providers."""

    def get_current_price_usd(self) -> Decimal:
        raise NotImplementedError


class MockBtcPriceOracle(BtcPriceOracle):
    """Stable local price oracle for tests and development."""

    def get_current_price_usd(self) -> Decimal:
        return Decimal("68000")
