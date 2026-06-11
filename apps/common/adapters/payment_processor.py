from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class PaymentRecord:
    """Normalized payment processor response used by ingestion."""

    external_id: str


class PaymentProcessor:
    """Interface for recording BTC payments with an external processor."""

    def record_btc_payment(self, *, amount_sats: int, merchant_id: str, customer_id: str) -> PaymentRecord:
        raise NotImplementedError


class MockPaymentProcessor(PaymentProcessor):
    """Local processor used until a real payment integration is configured."""

    def record_btc_payment(self, *, amount_sats: int, merchant_id: str, customer_id: str) -> PaymentRecord:
        stamp = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S%f")
        return PaymentRecord(external_id=f"mockpay_{stamp}")
