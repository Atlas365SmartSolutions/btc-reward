from __future__ import annotations

from decimal import Decimal

import pytest

from apps.merchants.models import Merchant
from apps.receipts.models import RewardCalculation, RewardReceipt
from apps.rewards.models import RewardPolicy
from apps.transactions.models import BtcTransaction
from apps.transactions.services.demo_seed import seed_demo_data
from apps.treasury.models import TreasurySnapshot, TreasuryWallet

pytestmark = pytest.mark.django_db


def test_seed_demo_data_creates_usable_records() -> None:
    result = seed_demo_data()

    merchant = Merchant.objects.get(id=result["merchant_id"])
    policy = RewardPolicy.objects.get(id=result["reward_policy_id"])
    transaction = BtcTransaction.objects.get(id=result["transaction_id"])
    receipt = RewardReceipt.objects.get(id=result["receipt_id"])
    calculation = RewardCalculation.objects.get(id="rc_demo")
    wallet = TreasuryWallet.objects.get(id=result["wallet_id"])
    snapshot = TreasurySnapshot.objects.get(id=result["snapshot_id"])

    assert merchant.name == "Satoshi Cafe"
    assert policy.merchant_retention_bps == 3500
    assert transaction.sats_spent == 500_000
    assert receipt.signed_reward_receipt_hash == "signed_hash_placeholder"
    assert calculation.customer_reward_usd >= Decimal("0")
    assert wallet is not None
    assert snapshot.allocated_usd_value == Decimal("130.00000000")


def test_seed_demo_data_is_idempotent() -> None:
    first = seed_demo_data()
    second = seed_demo_data()

    assert first == second
    assert Merchant.objects.filter(id="m_demo").count() == 1
