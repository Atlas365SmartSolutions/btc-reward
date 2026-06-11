from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DemoMerchant:
    id: str
    name: str
    nostr_pubkey: str
    lightning_address: str


@dataclass(frozen=True)
class DemoReceipt:
    id: str
    customer_name: str
    customer_reward_usd: Decimal
    signed_reward_receipt_hash: str


demo_merchant = DemoMerchant(
    id="m_demo",
    name="Satoshi Cafe",
    nostr_pubkey="npub1merchant",
    lightning_address="ops@sats.cafe",
)

demo_receipt = DemoReceipt(
    id="rr_demo",
    customer_name="Alice",
    customer_reward_usd=Decimal("2.51"),
    signed_reward_receipt_hash="sig_hash_placeholder",
)
