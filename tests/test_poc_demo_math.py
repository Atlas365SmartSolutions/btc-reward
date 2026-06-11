from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from apps.ui.services.poc_demo import (
    DEFAULT_DEMO_STATE,
    PURCHASE_ITEMS,
    calculate_aggregates,
    calculate_alice_totals,
    calculate_purchase_reward,
    calculate_receipt_reward,
    create_weekly_purchase,
    generate_random_purchase_amount,
    pay_alice_reward,
    purchase_conversion,
    random_purchase_amount,
    reward_sats,
)


def test_purchase_conversion() -> None:
    result = purchase_conversion(Decimal("10"), Decimal("100000"))

    assert result["btc_spent"] == Decimal("0.00010000")
    assert result["sats_spent"] == Decimal("10000")


def test_random_purchase_bounds() -> None:
    for _ in range(200):
        amount = generate_random_purchase_amount()
        assert Decimal("0.50") <= amount <= Decimal("250.00")


def test_purchase_ranges() -> None:
    for item_type, item in PURCHASE_ITEMS.items():
        minimum = Decimal(item["min_cents"]) / Decimal("100")
        maximum = Decimal(item["max_cents"]) / Decimal("100")
        for _ in range(100):
            amount = random_purchase_amount(item_type)
            assert minimum <= amount <= maximum


def test_new_purchase_uses_current_price_for_basis_and_checkpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("81234"),
    )
    state = deepcopy(DEFAULT_DEMO_STATE)

    purchase = create_weekly_purchase(state, usd_spent=Decimal("12.50"), item_type="regular")

    assert purchase["btc_price_at_purchase"] == "81234"
    assert purchase["last_reward_checkpoint_price"] == "81234"
    assert purchase["id"] == "alice_receipt_001"
    assert purchase["label"] == "Regular purchase"
    assert state["selected_receipt_id"] == "alice_receipt_001"


def test_reward_zero_at_purchase(monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("80000"),
    )
    state = deepcopy(DEFAULT_DEMO_STATE)
    purchase = create_weekly_purchase(state, usd_spent=Decimal("100"), item_type="larger")

    reward = calculate_purchase_reward(purchase, Decimal("80000"))

    assert reward["reward_usd"] == Decimal("0E-13")


def test_reward_after_btc_rise() -> None:
    purchase = {
        "btc_spent": "0.00100000",
        "last_paid_btc_price": "100000",
    }

    reward = calculate_purchase_reward(purchase, Decimal("150000"))

    assert reward["price_gain"] == Decimal("50000")
    assert reward["reward_usd"] == Decimal("5.000000000")


def test_aggregate_reward_across_two_receipts() -> None:
    state = deepcopy(DEFAULT_DEMO_STATE)
    state["simulated_btc_price"] = "150000"
    state["receipts"] = [
        {
            "id": "alice_receipt_001",
            "receipt_number": 1,
            "purchase_type": "regular",
            "label": "Regular purchase",
            "usd_spent": "100.00",
            "btc_spent": "0.00100000",
            "sats_spent": "100000",
            "btc_price_at_purchase": "100000",
            "last_reward_checkpoint_price": "100000",
            "created_label": "Receipt 1",
            "payout_events": [],
        },
        {
            "id": "alice_receipt_002",
            "receipt_number": 2,
            "purchase_type": "regular",
            "label": "Regular purchase",
            "usd_spent": "50.00",
            "btc_spent": "0.00100000",
            "sats_spent": "100000",
            "btc_price_at_purchase": "50000",
            "last_reward_checkpoint_price": "50000",
            "created_label": "Receipt 2",
            "payout_events": [],
        },
    ]

    reward_a = calculate_receipt_reward(state, state["receipts"][0])
    reward_b = calculate_receipt_reward(state, state["receipts"][1])
    totals = calculate_alice_totals(state)

    assert reward_a["receipt_reward_ready_usd"] == Decimal("5.000000000")
    assert reward_b["receipt_reward_ready_usd"] == Decimal("10.000000000")
    assert totals["total_reward_ready_usd"] == Decimal("15.000000000")


def test_approve_aggregate_reward(monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("100000"),
    )
    state = deepcopy(DEFAULT_DEMO_STATE)
    create_weekly_purchase(state, usd_spent=Decimal("100"), item_type="regular")
    state["current_live_btc_price"] = "50000"
    create_weekly_purchase(state, usd_spent=Decimal("50"), item_type="regular", force_price_refresh=False)
    state["receipts"][1]["btc_spent"] = "0.00100000"
    state["receipts"][1]["sats_spent"] = "100000"
    state["receipts"][1]["btc_price_at_purchase"] = "50000"
    state["receipts"][1]["last_reward_checkpoint_price"] = "50000"
    state["simulated_btc_price"] = "150000"

    event = pay_alice_reward(state)
    aggregates = calculate_aggregates(state)

    assert event is not None
    assert event["reward_usd"] == "15.00"
    assert state["receipts"][0]["last_reward_checkpoint_price"] == "150000"
    assert state["receipts"][1]["last_reward_checkpoint_price"] == "150000"
    assert aggregates["total_rewards_paid_usd"] == Decimal("15.00")
    assert aggregates["reward_ready_usd"] == Decimal("0E-13")


def test_new_reward_after_later_btc_rise(monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("100000"),
    )
    state = deepcopy(DEFAULT_DEMO_STATE)
    purchase = create_weekly_purchase(state, usd_spent=Decimal("100"), item_type="regular")
    purchase["last_reward_checkpoint_price"] = "150000"

    reward = calculate_purchase_reward(purchase, Decimal("180000"))

    assert reward["price_gain"] == Decimal("30000")
    assert reward["reward_usd"] == Decimal("3.000000000")


def test_sats_reward() -> None:
    assert reward_sats(Decimal("5"), Decimal("150000")) == Decimal("3333")


def test_requested_sats_conversion() -> None:
    assert reward_sats(Decimal("12.38"), Decimal("110334")) == Decimal("11220")


def test_approve_then_new_upside_uses_checkpoint_price(monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.ui.services.poc_demo.fetch_live_btc_usd_price",
        lambda force_refresh=False: Decimal("100000"),
    )
    state = deepcopy(DEFAULT_DEMO_STATE)
    create_weekly_purchase(state, usd_spent=Decimal("100"), item_type="regular")
    state["current_live_btc_price"] = "50000"
    create_weekly_purchase(state, usd_spent=Decimal("50"), item_type="regular", force_price_refresh=False)
    state["receipts"][1]["btc_spent"] = "0.00100000"
    state["receipts"][1]["sats_spent"] = "100000"
    state["receipts"][1]["btc_price_at_purchase"] = "50000"
    state["receipts"][1]["last_reward_checkpoint_price"] = "50000"
    state["simulated_btc_price"] = "150000"

    pay_alice_reward(state)
    state["simulated_btc_price"] = "180000"
    totals = calculate_alice_totals(state)

    assert state["receipts"][0]["last_reward_checkpoint_price"] == "150000"
    assert state["receipts"][1]["last_reward_checkpoint_price"] == "150000"
    assert totals["total_reward_ready_usd"] == Decimal("6.000000000")


def test_multiple_receipts_use_their_own_checkpoint_price() -> None:
    receipt_one = {"btc_spent": "0.00100000", "last_reward_checkpoint_price": "150000"}
    receipt_two = {"btc_spent": "0.00100000", "last_reward_checkpoint_price": "100000"}

    reward_one = calculate_purchase_reward(receipt_one, Decimal("180000"))
    reward_two = calculate_purchase_reward(receipt_two, Decimal("180000"))

    assert reward_one["reward_usd"] == Decimal("3.000000000")
    assert reward_two["reward_usd"] == Decimal("8.000000000")
