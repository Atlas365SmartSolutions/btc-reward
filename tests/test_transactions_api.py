from decimal import Decimal

import pytest

from apps.receipts.models import RewardCalculation, RewardReceipt
from apps.transactions.models import BtcTransaction, IngestionRequest


@pytest.mark.django_db
def test_create_transaction_persists_related_records(client, seeded_core_entities) -> None:
    response = client.post(
        "/api/transactions",
        {
            "merchant_id": seeded_core_entities["merchant_id"],
            "customer_id": seeded_core_entities["customer_id"],
            "reward_policy_id": seeded_core_entities["reward_policy_id"],
            "sats_spent": 100000,
            "btc_usd_price_at_purchase": "60000",
        },
        format="json",
        headers={"Idempotency-Key": "txn-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["idempotent_replay"] is False
    assert Decimal(body["reward_calculation"]["customer_reward_usd"]) == Decimal("6.80000000")

    assert BtcTransaction.objects.count() == 1
    assert RewardReceipt.objects.count() == 1
    assert RewardCalculation.objects.count() == 1
    assert IngestionRequest.objects.count() == 1


@pytest.mark.django_db
def test_create_transaction_idempotent_replay_returns_same_transaction(client, seeded_core_entities) -> None:
    payload = {
        "merchant_id": seeded_core_entities["merchant_id"],
        "customer_id": seeded_core_entities["customer_id"],
        "reward_policy_id": seeded_core_entities["reward_policy_id"],
        "sats_spent": 100000,
        "btc_usd_price_at_purchase": "60000",
    }

    first = client.post(
        "/api/transactions",
        payload,
        format="json",
        headers={"Idempotency-Key": "txn-2"},
    )
    second = client.post(
        "/api/transactions",
        payload,
        format="json",
        headers={"Idempotency-Key": "txn-2"},
    )

    assert first.status_code == 200
    assert second.status_code == 200

    first_body = first.json()
    second_body = second.json()

    assert first_body["transaction_id"] == second_body["transaction_id"]
    assert first_body["reward_receipt_id"] == second_body["reward_receipt_id"]
    assert second_body["idempotent_replay"] is True

    assert BtcTransaction.objects.count() == 1
    assert RewardReceipt.objects.count() == 1
    assert RewardCalculation.objects.count() == 1
    assert IngestionRequest.objects.count() == 1
