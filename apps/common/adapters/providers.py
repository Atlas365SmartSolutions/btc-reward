from __future__ import annotations

from django.conf import settings

from apps.common.adapters.btc_price_oracle import BtcPriceOracle, MockBtcPriceOracle
from apps.common.adapters.payment_processor import (
    MockPaymentProcessor,
    PaymentProcessor,
)


def get_payment_processor() -> PaymentProcessor:
    """Build the configured payment processor adapter."""
    backend = settings.PAYMENT_PROCESSOR_BACKEND
    if backend == "mock":
        return MockPaymentProcessor()
    raise ValueError(f"Unsupported PAYMENT_PROCESSOR_BACKEND: {backend}")


def get_btc_price_oracle() -> BtcPriceOracle:
    """Build the configured BTC price oracle adapter."""
    backend = settings.BTC_PRICE_ORACLE_BACKEND
    if backend == "mock":
        return MockBtcPriceOracle()
    raise ValueError(f"Unsupported BTC_PRICE_ORACLE_BACKEND: {backend}")
