from __future__ import annotations

import pytest

from apps.transactions.models import IngestionRequest

pytestmark = pytest.mark.django_db


def test_sensitive_api_requires_staff_authentication(anonymous_client, seeded_core_entities) -> None:
    response = anonymous_client.get(f"/api/merchants/{seeded_core_entities['merchant_id']}/reserve-health")

    assert response.status_code in (401, 403)


def test_sensitive_ui_redirects_to_admin_login(anonymous_client, seeded_core_entities) -> None:
    response = anonymous_client.get(f"/merchants/{seeded_core_entities['merchant_id']}")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


def test_receipt_api_redacts_contact_and_secret_fields(client, seeded_core_entities) -> None:
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
        headers={"Idempotency-Key": "security-redaction-1"},
    )
    receipt_id = tx_response.json()["reward_receipt_id"]

    response = client.get(f"/api/receipts/{receipt_id}")

    assert response.status_code == 200
    body = response.json()
    assert "signed_reward_receipt_hash" not in body
    assert "email" not in body["customer"]
    assert "nostr_pubkey" not in body["customer"]
    assert "lightning_address" not in body["customer"]
    assert "encrypted_nwc_uri" not in body["merchant"]
    assert "lightning_address" not in body["merchant"]


def test_transaction_rejects_zero_purchase_price_before_database_error(client, seeded_core_entities) -> None:
    response = client.post(
        "/api/transactions",
        {
            "merchant_id": seeded_core_entities["merchant_id"],
            "customer_id": seeded_core_entities["customer_id"],
            "reward_policy_id": seeded_core_entities["reward_policy_id"],
            "sats_spent": 100,
            "btc_usd_price_at_purchase": "0",
        },
        format="json",
        headers={"Idempotency-Key": "zero-price-1"},
    )

    assert response.status_code == 400
    assert IngestionRequest.objects.filter(idempotency_key="zero-price-1").count() == 0


def test_idempotency_key_rejects_different_payload(client, seeded_core_entities) -> None:
    key = "same-key-different-body"
    first = client.post(
        "/api/transactions",
        {
            "merchant_id": seeded_core_entities["merchant_id"],
            "customer_id": seeded_core_entities["customer_id"],
            "reward_policy_id": seeded_core_entities["reward_policy_id"],
            "sats_spent": 100,
            "btc_usd_price_at_purchase": "60000",
        },
        format="json",
        headers={"Idempotency-Key": key},
    )
    second = client.post(
        "/api/transactions",
        {
            "merchant_id": seeded_core_entities["merchant_id"],
            "customer_id": seeded_core_entities["customer_id"],
            "reward_policy_id": seeded_core_entities["reward_policy_id"],
            "sats_spent": 200,
            "btc_usd_price_at_purchase": "60000",
        },
        format="json",
        headers={"Idempotency-Key": key},
    )

    assert first.status_code == 200
    assert second.status_code == 409
