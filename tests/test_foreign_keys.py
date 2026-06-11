from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.receipts.models import RewardCalculation
from apps.transactions.models import BtcTransaction
from apps.treasury.models import TreasurySnapshot


@pytest.mark.django_db(transaction=True)
def test_transaction_rejects_missing_customer_fk(seeded_core_entities) -> None:
    with pytest.raises(IntegrityError):
        BtcTransaction.objects.create(
            id="tx_missing_customer",
            merchant_id=seeded_core_entities["merchant_id"],
            customer_id="missing_customer",
            reward_policy_id=seeded_core_entities["reward_policy_id"],
            sats_spent=100,
            btc_usd_price_at_purchase=Decimal("60000.00000000"),
            payment_external_id="mockpay_fk_1",
        )


@pytest.mark.django_db(transaction=True)
def test_reward_calculation_rejects_missing_receipt_fk() -> None:
    with pytest.raises(IntegrityError):
        RewardCalculation.objects.create(
            id="calc_missing_receipt",
            reward_receipt_id="missing_receipt",
            eligible_btc_notional_sats=100,
            basis_value_usd=Decimal("1.00000000"),
            current_value_usd=Decimal("1.20000000"),
            incremental_appreciation_usd=Decimal("0.20000000"),
            customer_reward_usd=Decimal("0.04000000"),
        )


@pytest.mark.django_db(transaction=True)
def test_treasury_snapshot_rejects_missing_wallet_fk() -> None:
    with pytest.raises(IntegrityError):
        TreasurySnapshot.objects.create(
            id="snap_missing_wallet",
            treasury_wallet_id="missing_wallet",
            btc_usd_price=Decimal("68000.00000000"),
            allocated_usd_value=Decimal("100.00000000"),
            coverage_ratio=Decimal("1.10000000"),
            snapshot_source="manual",
        )
