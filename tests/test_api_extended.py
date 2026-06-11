from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.receipts.models import RewardCalculation
from apps.treasury.models import TreasurySnapshot, TreasuryWallet

pytestmark = pytest.mark.django_db


def test_create_merchant_endpoint(client) -> None:
    response = client.post(
        "/api/merchants",
        {
            "name": "Satoshi Cafe",
            "nostr_pubkey": "npub_test",
            "lightning_address": "ops@sats.cafe",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["merchant"]["name"] == "Satoshi Cafe"


def test_create_reward_policy_endpoint(client, seeded_core_entities) -> None:
    response = client.post(
        "/api/reward-policies",
        {
            "merchant_id": seeded_core_entities["merchant_id"],
            "merchant_retention_bps": 4500,
            "customer_share_bps": 2000,
            "min_coverage_ratio": "1.2",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["policy"]["merchant_retention_bps"] == 4500
    assert Decimal(body["policy"]["min_coverage_ratio"]) == Decimal("1.2000")


def test_get_receipt_endpoint_returns_nested_entities(client, seeded_core_entities) -> None:
    tx_response = client.post(
        "/api/transactions",
        {
            "merchant_id": seeded_core_entities["merchant_id"],
            "customer_id": seeded_core_entities["customer_id"],
            "reward_policy_id": seeded_core_entities["reward_policy_id"],
            "sats_spent": 100000,
            "btc_usd_price_at_purchase": "60000",
        },
        format="json",
        headers={"Idempotency-Key": "receipt-get-1"},
    )
    assert tx_response.status_code == 200
    receipt_id = tx_response.json()["reward_receipt_id"]

    response = client.get(f"/api/receipts/{receipt_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == receipt_id
    assert body["transaction"]["id"] == tx_response.json()["transaction_id"]
    assert body["customer"]["id"] == seeded_core_entities["customer_id"]
    assert body["merchant"]["id"] == seeded_core_entities["merchant_id"]
    assert len(body["calculations"]) >= 1


def test_get_receipt_404(client) -> None:
    response = client.get("/api/receipts/does-not-exist")
    assert response.status_code == 404


def test_create_treasury_snapshot_endpoint(client, seeded_core_entities) -> None:
    wallet = TreasuryWallet.objects.create(
        id="w_1",
        merchant_id=seeded_core_entities["merchant_id"],
        label="Primary",
        btc_balance=Decimal("1.50000000"),
    )

    response = client.post(
        "/api/treasury/snapshots",
        {
            "treasury_wallet_id": wallet.id,
            "btc_usd_price": "68000",
            "allocated_usd_value": "1200",
            "coverage_ratio": "1.2",
            "snapshot_source": "manual",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["snapshot"]["treasury_wallet_id"] == wallet.id


def test_merchant_reserve_health_uses_persisted_records(client, seeded_core_entities) -> None:
    tx_response = client.post(
        "/api/transactions",
        {
            "merchant_id": seeded_core_entities["merchant_id"],
            "customer_id": seeded_core_entities["customer_id"],
            "reward_policy_id": seeded_core_entities["reward_policy_id"],
            "sats_spent": 100000,
            "btc_usd_price_at_purchase": "60000",
        },
        format="json",
        headers={"Idempotency-Key": "reserve-health-1"},
    )
    assert tx_response.status_code == 200
    receipt_id = tx_response.json()["reward_receipt_id"]

    late_created_at = timezone.now() + timedelta(seconds=30)
    latest_calc = RewardCalculation.objects.create(
        id="calc_late_1",
        reward_receipt_id=receipt_id,
        eligible_btc_notional_sats=50000,
        basis_value_usd=Decimal("30.00000000"),
        current_value_usd=Decimal("40.00000000"),
        incremental_appreciation_usd=Decimal("10.00000000"),
        customer_reward_usd=Decimal("1.25000000"),
    )
    RewardCalculation.objects.filter(id=latest_calc.id).update(created_at=late_created_at)

    wallet = TreasuryWallet.objects.create(
        id="wallet_health_1",
        merchant_id=seeded_core_entities["merchant_id"],
        label="Reserve Wallet",
        btc_balance=Decimal("9.00000000"),
    )
    old_snapshot = TreasurySnapshot.objects.create(
        id="snap_old_1",
        treasury_wallet=wallet,
        btc_usd_price=Decimal("68000.00000000"),
        allocated_usd_value=Decimal("300.00000000"),
        coverage_ratio=Decimal("0.8"),
        snapshot_source="oracle",
    )
    new_snapshot = TreasurySnapshot.objects.create(
        id="snap_new_1",
        treasury_wallet=wallet,
        btc_usd_price=Decimal("69000.00000000"),
        allocated_usd_value=Decimal("500.00000000"),
        coverage_ratio=Decimal("1.1"),
        snapshot_source="oracle",
    )
    TreasurySnapshot.objects.filter(id=old_snapshot.id).update(created_at=timezone.now())
    TreasurySnapshot.objects.filter(id=new_snapshot.id).update(created_at=late_created_at)

    response = client.get(f"/api/merchants/{seeded_core_entities['merchant_id']}/reserve-health")
    assert response.status_code == 200
    body = response.json()

    assert Decimal(body["eligible_liabilities_usd"]) == Decimal("1.25000000")
    assert Decimal(body["treasury_allocated_usd"]) == Decimal("500.00000000")
    assert Decimal(body["min_coverage_ratio"]) == Decimal("1.10000000")
    assert body["is_healthy"] is True
    assert body["pause_accrual"] is False


def test_merchant_reserve_health_ties_break_by_id(client, seeded_core_entities) -> None:
    tx_response = client.post(
        "/api/transactions",
        {
            "merchant_id": seeded_core_entities["merchant_id"],
            "customer_id": seeded_core_entities["customer_id"],
            "reward_policy_id": seeded_core_entities["reward_policy_id"],
            "sats_spent": 100000,
            "btc_usd_price_at_purchase": "60000",
        },
        format="json",
        headers={"Idempotency-Key": "reserve-health-tie-1"},
    )
    receipt_id = tx_response.json()["reward_receipt_id"]
    tied_created_at = timezone.now() + timedelta(minutes=5)

    low_calc = RewardCalculation.objects.create(
        id="calc_a",
        reward_receipt_id=receipt_id,
        eligible_btc_notional_sats=50000,
        basis_value_usd=Decimal("30.00000000"),
        current_value_usd=Decimal("40.00000000"),
        incremental_appreciation_usd=Decimal("10.00000000"),
        customer_reward_usd=Decimal("1.00000000"),
    )
    high_calc = RewardCalculation.objects.create(
        id="calc_z",
        reward_receipt_id=receipt_id,
        eligible_btc_notional_sats=50000,
        basis_value_usd=Decimal("30.00000000"),
        current_value_usd=Decimal("40.00000000"),
        incremental_appreciation_usd=Decimal("10.00000000"),
        customer_reward_usd=Decimal("2.00000000"),
    )
    RewardCalculation.objects.filter(id__in=[low_calc.id, high_calc.id]).update(created_at=tied_created_at)

    wallet = TreasuryWallet.objects.create(
        id="wallet_tie_1",
        merchant_id=seeded_core_entities["merchant_id"],
        label="Reserve Wallet",
        btc_balance=Decimal("1.00000000"),
    )
    low_snapshot = TreasurySnapshot.objects.create(
        id="snap_a",
        treasury_wallet=wallet,
        btc_usd_price=Decimal("68000.00000000"),
        allocated_usd_value=Decimal("100.00000000"),
        coverage_ratio=Decimal("1.0"),
        snapshot_source="oracle",
    )
    high_snapshot = TreasurySnapshot.objects.create(
        id="snap_z",
        treasury_wallet=wallet,
        btc_usd_price=Decimal("68000.00000000"),
        allocated_usd_value=Decimal("200.00000000"),
        coverage_ratio=Decimal("1.0"),
        snapshot_source="oracle",
    )
    TreasurySnapshot.objects.filter(id__in=[low_snapshot.id, high_snapshot.id]).update(created_at=tied_created_at)

    response = client.get(f"/api/merchants/{seeded_core_entities['merchant_id']}/reserve-health")

    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["eligible_liabilities_usd"]) == Decimal("2.00000000")
    assert Decimal(body["treasury_allocated_usd"]) == Decimal("200.00000000")
