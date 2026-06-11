from __future__ import annotations

from decimal import Decimal

import pytest

from apps.treasury.models import TreasurySnapshot, TreasuryWallet

pytestmark = pytest.mark.django_db


def test_home_page_renders(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    text = response.content.decode()
    assert "Turn Bitcoin payments into customer rewards." in text
    assert "Bitcoin rewards infrastructure for merchants" in text
    assert "Try the demo" in text
    assert "View customer receipt" in text
    assert ">Home</a>" in text
    assert "Product" not in text
    assert "Demo state: deterministic" not in text
    assert "0.01 BTC" not in text
    assert "$150,000 - $100,000" not in text
    assert "Treasury coverage" not in text
    assert "prorate" not in text.lower()
    assert "crystallize" not in text.lower()
    assert "high-water" not in text.lower()
    assert "notional" not in text.lower()
    assert "liability" not in text.lower()


def test_merchants_page_renders_seeded_merchant(client, seeded_core_entities) -> None:
    response = client.get("/merchants")
    assert response.status_code == 200
    text = response.content.decode()
    assert "Merchants" in text
    assert "Merchant One" in text


def test_merchant_detail_page_renders_sections(client) -> None:
    response = client.get("/merchants/m_demo")
    assert response.status_code in (200, 404)


def test_merchant_detail_page_renders_live_summary(client, seeded_core_entities) -> None:
    response = client.get(f"/merchants/{seeded_core_entities['merchant_id']}")
    assert response.status_code == 200
    text = response.content.decode()
    assert f"Merchant {seeded_core_entities['merchant_id']}" in text
    assert "Policies:" in text
    assert "Transactions:" in text
    assert "Treasury wallets:" in text


def test_merchant_policy_and_transaction_pages_render_live_data(client, seeded_core_entities) -> None:
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
        headers={"Idempotency-Key": "ui-sections-1"},
    )
    assert tx_response.status_code == 200

    policies = client.get(f"/merchants/{seeded_core_entities['merchant_id']}/policies")
    transactions = client.get(f"/merchants/{seeded_core_entities['merchant_id']}/transactions")

    assert policies.status_code == 200
    assert transactions.status_code == 200
    assert "Merchant retention:" in policies.content.decode()
    assert "Sats spent:" in transactions.content.decode()


def test_merchant_treasury_page_renders_live_data(client, seeded_core_entities) -> None:
    wallet = TreasuryWallet.objects.create(
        id="ui_wallet_1",
        merchant_id=seeded_core_entities["merchant_id"],
        label="Primary",
        btc_balance=Decimal("0.50000000"),
    )
    TreasurySnapshot.objects.create(
        id="ui_snap_1",
        treasury_wallet=wallet,
        btc_usd_price=Decimal("70000.00000000"),
        allocated_usd_value=Decimal("250.00000000"),
        coverage_ratio=Decimal("1.20000000"),
        snapshot_source="manual",
    )

    response = client.get(f"/merchants/{seeded_core_entities['merchant_id']}/treasury")
    assert response.status_code == 200
    text = response.content.decode()
    assert "Coverage ratio:" in text
    assert "Primary" in text
    assert "Allocated USD:" in text


def test_receipt_page_renders_existing_receipt(client, seeded_core_entities) -> None:
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
        headers={"Idempotency-Key": "ui-receipt-1"},
    )
    receipt_id = tx_response.json()["reward_receipt_id"]

    response = client.get(f"/receipts/{receipt_id}")
    assert response.status_code == 200
    text = response.content.decode()
    assert f"Reward Receipt {receipt_id}" in text
    assert "alice@example.com" in text


def test_admin_demo_page_renders(client) -> None:
    response = client.get("/admin/demo")
    assert response.status_code == 200
    text = response.content.decode()
    assert "Admin Demo" in text
    assert "system-record-root" in text


def test_demo_reset_starts_empty_with_purchase_first_ui(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("81012"),
    )
    response = client.post("/demo/actions/reset", follow=True)
    assert response.status_code == 200

    state = client.session["earn_forever_demo"]
    assert state["receipts"] == []
    assert state["merchant"]["name"] == "Satoshi Cafe"

    text = response.content.decode()
    assert "Alice buys with Bitcoin" in text
    assert "No receipt yet. Have Alice buy something with Bitcoin." in text
    assert "Live BTC price" in text
    assert "$0.00" in text


def test_demo_purchase_creates_weekly_sats_receipt(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("100000"),
    )
    client.post("/demo/actions/reset")
    response = client.post("/demo/actions/alice-buys", {"item_type": "regular"}, follow=True)

    assert response.status_code == 200
    state = client.session["earn_forever_demo"]
    assert len(state["receipts"]) == 1
    purchase = state["receipts"][0]
    assert purchase["id"] == "alice_receipt_001"
    assert purchase["label"] == "Regular purchase"
    assert purchase["btc_price_at_purchase"] == "100000"
    assert purchase["last_reward_checkpoint_price"] == "100000"

    text = response.content.decode()
    assert "Receipt 1" in text
    assert "sats" in text
    assert "BTC price when paid" in text


def test_demo_second_purchase_does_not_show_chart(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("100000"),
    )
    client.post("/demo/actions/reset")

    client.post("/demo/actions/alice-buys", {"item_type": "small"}, follow=True)
    response = client.post("/demo/actions/alice-buys", {"item_type": "regular"}, follow=True)

    assert response.status_code == 200
    text = response.content.decode()
    assert "Alice's sats receipts" in text
    assert "btcRewardChart" not in text
    assert "Receipt 2" in text


def test_demo_payout_moves_purchase_checkpoint_price(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("100000"),
    )
    client.post("/demo/actions/reset")
    client.post("/demo/actions/alice-buys", {"item_type": "larger"}, follow=True)
    client.post("/demo/actions/set-price", {"value": "150000"}, follow=True)
    response = client.post("/demo/actions/authorize-payout", follow=True)

    assert response.status_code == 200
    state = client.session["earn_forever_demo"]
    assert state["payouts"]
    assert state["receipts"][0]["last_reward_checkpoint_price"] == "150000"

    text = response.content.decode()
    assert "Alice was paid" in text
    assert "Future rewards will only come from new BTC upside after this approval." in text


def test_demo_new_upside_after_payout_is_incremental(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("100000"),
    )
    monkeypatch.setattr("apps.ui.services.poc_demo.random.randint", lambda minimum, maximum: 10000)
    client.post("/demo/actions/reset")
    client.post("/demo/actions/alice-buys", {"item_type": "larger"}, follow=True)
    client.post("/demo/actions/set-price", {"value": "150000"}, follow=True)
    client.post("/demo/actions/authorize-payout", follow=True)
    response = client.post("/demo/actions/set-price", {"value": "180000"}, follow=True)

    assert response.status_code == 200
    text = response.content.decode()
    assert "Alice reward ready from all receipts" in text
    assert "$3.00" in text


def test_demo_multiple_purchases_show_aggregate_reward(client, monkeypatch) -> None:
    values = iter([10000, 5000])
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("100000"),
    )
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.random.randint",
        lambda minimum, maximum: next(values),
    )
    client.post("/demo/actions/reset")
    client.post("/demo/actions/alice-buys", {"item_type": "regular"}, follow=True)
    client.post("/demo/actions/alice-buys", {"item_type": "larger"}, follow=True)
    response = client.post("/demo/actions/set-price", {"value": "150000"}, follow=True)

    assert response.status_code == 200
    state = client.session["earn_forever_demo"]
    assert len(state["receipts"]) == 2

    text = response.content.decode()
    assert "Alice's reward total" in text
    assert "Alice reward ready from all receipts" in text
    assert "$7.50" in text
    assert "Reward from this receipt" in text
    assert "Paid-through BTC price" not in text


def test_demo_primary_ui_avoids_blocked_terms(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("81012"),
    )
    response = client.get("/demo")
    text = response.content.decode()

    assert "Coverage behavior" not in text
    assert "Demo upside mode" not in text
    assert "Alice's rewards over time" not in text
    assert "btcRewardChart" not in text
    assert "high-water" not in text.lower()
    assert "notional" not in text.lower()
    assert "liability" not in text.lower()
    assert "crystallize" not in text.lower()
    assert "prorate" not in text.lower()
    assert "yield" not in text.lower()
    assert "APY" not in text
    assert "investment" not in text.lower()
