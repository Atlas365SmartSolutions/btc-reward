from __future__ import annotations

import json
import random
import urllib.request
from copy import deepcopy
from decimal import ROUND_HALF_UP, Decimal

from django.core.cache import cache
from django.utils import timezone

SATS_PER_BTC = Decimal("100000000")
MONEY = Decimal("0.01")
BTC = Decimal("0.00000001")
CUSTOMER_SHARE = Decimal("0.10")
MAX_VISIBLE_RECEIPTS = 8
DEFAULT_PRICE = Decimal("81012")

PURCHASE_ITEMS = {
    "small": {
        "label": "Small purchase",
        "button": "Small purchase",
        "range_display": "$0.50-$10",
        "min_cents": 50,
        "max_cents": 1000,
    },
    "regular": {
        "label": "Regular purchase",
        "button": "Regular purchase",
        "range_display": "$10-$50",
        "min_cents": 1000,
        "max_cents": 5000,
    },
    "larger": {
        "label": "Larger purchase",
        "button": "Larger purchase",
        "range_display": "$50-$150",
        "min_cents": 5000,
        "max_cents": 15000,
    },
    "big": {
        "label": "Big purchase",
        "button": "Big purchase",
        "range_display": "$150-$250",
        "min_cents": 15000,
        "max_cents": 25000,
    },
}


DEFAULT_DEMO_STATE = {
    "version": 8,
    "merchant": {"id": "m_demo", "name": "Satoshi Cafe"},
    "alice": {"name": "Alice", "customer_share_pct": "10"},
    "current_live_btc_price": str(DEFAULT_PRICE),
    "simulated_btc_price": str(DEFAULT_PRICE),
    "selected_receipt_id": "",
    "customer_share_pct": "10",
    "receipts": [],
    "payouts": [],
    "last_price_checked_at": "",
    "price_source_status": "using_last_price",
    "price_message": "Using last known BTC price.",
}


def get_demo_state(session) -> dict:
    """Load or initialize signed-cookie state for the browser-only demo."""
    if (
        "earn_forever_demo" not in session
        or session["earn_forever_demo"].get("version") != DEFAULT_DEMO_STATE["version"]
    ):
        session["earn_forever_demo"] = deepcopy(DEFAULT_DEMO_STATE)
        session.modified = True
    normalize_demo_state(session["earn_forever_demo"])
    session.modified = True
    return session["earn_forever_demo"]


def reset_demo_state(session) -> dict:
    session["earn_forever_demo"] = deepcopy(DEFAULT_DEMO_STATE)
    session.modified = True
    return session["earn_forever_demo"]


def save_demo_state(session, state: dict) -> None:
    normalize_demo_state(state)
    session["earn_forever_demo"] = state
    session.modified = True


def normalize_demo_state(state: dict) -> None:
    """Migrate older demo session shapes into the current schema in place."""
    state.setdefault("version", DEFAULT_DEMO_STATE["version"])
    state.setdefault("merchant", deepcopy(DEFAULT_DEMO_STATE["merchant"]))
    state.setdefault("alice", deepcopy(DEFAULT_DEMO_STATE["alice"]))
    if "receipts" not in state and "purchases" in state:
        state["receipts"] = state.pop("purchases")
    if "payouts" not in state and "payout_events" in state:
        state["payouts"] = state.pop("payout_events")
    if "current_live_btc_price" not in state:
        state["current_live_btc_price"] = state.get("current_btc_price", str(DEFAULT_PRICE))
    state.setdefault("simulated_btc_price", state.get("current_live_btc_price", str(DEFAULT_PRICE)))
    state.setdefault("selected_receipt_id", "")
    state.setdefault("customer_share_pct", "10")
    state.setdefault("receipts", [])
    state.setdefault("payouts", [])
    state.setdefault("last_price_checked_at", "")
    state.setdefault("price_source_status", "using_last_price")
    state.setdefault("price_message", "")

    for index, receipt in enumerate(state["receipts"], start=1):
        receipt.setdefault("id", f"alice_receipt_{index:03d}")
        receipt.setdefault("receipt_number", index)
        if receipt.get("purchase_type") not in PURCHASE_ITEMS:
            receipt["purchase_type"] = "regular"
        receipt.setdefault("label", PURCHASE_ITEMS[receipt["purchase_type"]]["label"])
        receipt.setdefault("item_name", receipt["label"])
        receipt.setdefault(
            "last_reward_checkpoint_price",
            receipt.get(
                "last_paid_btc_price",
                receipt.get("btc_price_at_purchase", state["current_live_btc_price"]),
            ),
        )
        receipt.setdefault("status", "No upside yet")
        receipt.setdefault("created_label", f"Receipt {index}")
        receipt.setdefault("payout_events", [])
        receipt.setdefault("paid_reward_usd_total", "0")


def decimal_value(value: object) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal) -> str:
    return f"${value.quantize(MONEY, rounding=ROUND_HALF_UP):,.2f}"


def btc(value: Decimal) -> str:
    return f"{value.quantize(BTC, rounding=ROUND_HALF_UP)} BTC"


def sats(value: Decimal | int) -> str:
    return f"{int(decimal_value(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP)):,} sats"


def price_per_btc(value: Decimal) -> str:
    return f"{money(value)}/BTC"


def pct(value: Decimal) -> str:
    return f"{value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)}%"


def checked_at_label() -> str:
    return timezone.localtime().strftime("%-I:%M:%S %p")


def random_purchase_amount(item_type: str) -> Decimal:
    item = PURCHASE_ITEMS.get(item_type, PURCHASE_ITEMS["regular"])
    return (Decimal(random.randint(item["min_cents"], item["max_cents"])) / Decimal("100")).quantize(
        MONEY, rounding=ROUND_HALF_UP
    )


def generate_random_purchase_amount() -> Decimal:
    return random_purchase_amount(random.choice(list(PURCHASE_ITEMS)))


def purchase_conversion(usd_spent: Decimal, btc_price: Decimal) -> dict:
    btc_spent = (usd_spent / btc_price).quantize(BTC, rounding=ROUND_HALF_UP)
    sats_spent = (btc_spent * SATS_PER_BTC).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return {"btc_spent": btc_spent, "sats_spent": sats_spent}


def reward_sats(reward_usd: Decimal, btc_price: Decimal) -> Decimal:
    if reward_usd <= 0 or btc_price <= 0:
        return Decimal("0")
    return (reward_usd / btc_price * SATS_PER_BTC).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def customer_share(state: dict) -> Decimal:
    return decimal_value(state.get("customer_share_pct", "10")) / Decimal("100")


def calculate_receipt_reward(state: dict, receipt: dict) -> dict:
    normalize_demo_state(state)
    simulated_price = decimal_value(state["simulated_btc_price"])
    btc_spent = decimal_value(receipt["btc_spent"])
    checkpoint_price = decimal_value(receipt["last_reward_checkpoint_price"])
    price_gain = max(Decimal("0"), simulated_price - checkpoint_price)
    upside_usd = btc_spent * price_gain
    reward_usd = upside_usd * customer_share(state)
    reward_sats_value = reward_sats(reward_usd, simulated_price)
    status = "Reward ready" if reward_usd > 0 else ("Paid" if receipt.get("payout_events") else "No upside")
    return {
        "receipt_price_gain": price_gain,
        "receipt_upside_usd": upside_usd,
        "receipt_reward_ready_usd": reward_usd,
        "receipt_reward_ready_sats": reward_sats_value,
        "receipt_status": status,
    }


def calculate_purchase_reward(receipt: dict, future_btc_price: Decimal) -> dict:
    state = deepcopy(DEFAULT_DEMO_STATE)
    state["simulated_btc_price"] = str(future_btc_price)
    normalized_receipt = deepcopy(receipt)
    normalized_receipt.setdefault(
        "last_reward_checkpoint_price",
        normalized_receipt.get(
            "last_paid_btc_price",
            normalized_receipt.get("btc_price_at_purchase", future_btc_price),
        ),
    )
    reward = calculate_receipt_reward(state, normalized_receipt)
    return {
        "price_gain": reward["receipt_price_gain"],
        "upside_usd": reward["receipt_upside_usd"],
        "reward_usd": reward["receipt_reward_ready_usd"],
        "reward_sats": reward["receipt_reward_ready_sats"],
    }


def fetch_live_btc_usd_price(*, force_refresh: bool = False) -> Decimal:
    """Fetch a cached BTC/USD spot price for the interactive public demo."""
    if not force_refresh:
        cached = cache.get("demo_live_btc_usd_price")
        if cached is not None:
            return decimal_value(cached)

    request = urllib.request.Request(
        "https://api.exchange.coinbase.com/products/BTC-USD/ticker",
        headers={"User-Agent": "btc-loyalty-demo/1.0"},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        payload = json.loads(response.read().decode("utf-8"))
    price = decimal_value(payload["price"])
    cache.set("demo_live_btc_usd_price", str(price), timeout=60)
    return price


def sync_live_btc_price(state: dict, *, force_refresh: bool = False) -> bool:
    normalize_demo_state(state)
    try:
        live_price = fetch_live_btc_usd_price(force_refresh=force_refresh)
    except Exception:
        state["price_source_status"] = "using_last_price"
        state["price_message"] = "Using last known BTC price."
        if not state.get("last_price_checked_at"):
            state["last_price_checked_at"] = checked_at_label()
        return False

    state["current_live_btc_price"] = str(live_price.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if not state.get("selected_receipt_id"):
        state["simulated_btc_price"] = state["current_live_btc_price"]
    state["last_price_checked_at"] = checked_at_label()
    state["price_source_status"] = "live"
    state["price_message"] = ""
    return True


def create_weekly_purchase(
    state: dict,
    *,
    usd_spent: Decimal | None = None,
    item_name: str | None = None,
    item_type: str = "regular",
    force_price_refresh: bool = True,
) -> dict:
    """Append a simulated Alice purchase to the session-backed demo ledger."""
    normalize_demo_state(state)
    sync_live_btc_price(state, force_refresh=force_price_refresh)
    item = PURCHASE_ITEMS.get(item_type, PURCHASE_ITEMS["regular"])
    current_price = decimal_value(state["current_live_btc_price"])
    amount = (usd_spent if usd_spent is not None else random_purchase_amount(item_type)).quantize(
        MONEY, rounding=ROUND_HALF_UP
    )
    conversion = purchase_conversion(amount, current_price)
    receipt_number = len(state["receipts"]) + 1
    receipt = {
        "id": f"alice_receipt_{receipt_number:03d}",
        "receipt_number": receipt_number,
        "purchase_type": item_type if item_type in PURCHASE_ITEMS else "regular",
        "label": item_name or item["label"],
        "item_name": item_name or item["label"],
        "usd_spent": str(amount),
        "btc_spent": str(conversion["btc_spent"]),
        "sats_spent": str(conversion["sats_spent"]),
        "btc_price_at_purchase": str(current_price),
        "last_reward_checkpoint_price": str(current_price),
        "status": "No upside yet",
        "created_label": f"Receipt {receipt_number}",
        "payout_events": [],
        "paid_reward_usd_total": "0",
    }
    state["receipts"].append(receipt)
    state["selected_receipt_id"] = receipt["id"]
    state["simulated_btc_price"] = str(current_price)
    return receipt


def selected_receipt(state: dict) -> dict | None:
    normalize_demo_state(state)
    selected_id = state.get("selected_receipt_id")
    for receipt in state["receipts"]:
        if receipt["id"] == selected_id:
            return receipt
    return state["receipts"][-1] if state["receipts"] else None


def select_receipt(state: dict, receipt_id: str) -> None:
    normalize_demo_state(state)
    if any(receipt["id"] == receipt_id for receipt in state["receipts"]):
        state["selected_receipt_id"] = receipt_id


def set_demo_price(state: dict, price: str) -> None:
    normalize_demo_state(state)
    try:
        future_price = decimal_value(price)
    except Exception:
        return
    if future_price <= 0:
        return
    state["simulated_btc_price"] = str(future_price.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def set_simulated_price_from_live(state: dict) -> None:
    normalize_demo_state(state)
    state["simulated_btc_price"] = state["current_live_btc_price"]


def set_simulated_upside(state: dict, multiplier: str) -> None:
    normalize_demo_state(state)
    base_price = decimal_value(state["current_live_btc_price"])
    state["simulated_btc_price"] = str(
        (base_price * decimal_value(multiplier)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def enrich_receipt(receipt: dict, simulated_price: Decimal) -> dict:
    state = deepcopy(DEFAULT_DEMO_STATE)
    state["simulated_btc_price"] = str(simulated_price)
    reward = calculate_receipt_reward(state, receipt)
    usd_spent = decimal_value(receipt["usd_spent"])
    btc_spent = decimal_value(receipt["btc_spent"])
    sats_spent = decimal_value(receipt["sats_spent"])
    btc_price_at_purchase = decimal_value(receipt["btc_price_at_purchase"])
    checkpoint_price = decimal_value(receipt["last_reward_checkpoint_price"])
    return {
        **receipt,
        "status": reward["receipt_status"],
        "usd_spent_decimal": usd_spent,
        "btc_spent_decimal": btc_spent,
        "sats_spent_decimal": sats_spent,
        "btc_price_at_purchase_decimal": btc_price_at_purchase,
        "last_reward_checkpoint_price_decimal": checkpoint_price,
        "price_gain": reward["receipt_price_gain"],
        "upside_usd": reward["receipt_upside_usd"],
        "reward_usd": reward["receipt_reward_ready_usd"],
        "reward_sats": reward["receipt_reward_ready_sats"],
        "usd_spent_display": money(usd_spent),
        "btc_spent_display": btc(btc_spent),
        "sats_spent_display": sats(sats_spent),
        "btc_price_at_purchase_display": price_per_btc(btc_price_at_purchase),
        "last_reward_checkpoint_price_display": price_per_btc(checkpoint_price),
        "price_gain_display": money(reward["receipt_price_gain"]),
        "upside_usd_display": money(reward["receipt_upside_usd"]),
        "reward_usd_display": money(reward["receipt_reward_ready_usd"]),
        "reward_sats_display": sats(reward["receipt_reward_ready_sats"]),
    }


def calculate_alice_totals(state: dict) -> dict:
    normalize_demo_state(state)
    simulated_price = decimal_value(state["simulated_btc_price"])
    receipts = [enrich_receipt(receipt, simulated_price) for receipt in state["receipts"]]
    total_spent_usd = sum((receipt["usd_spent_decimal"] for receipt in receipts), Decimal("0"))
    total_btc_spent = sum((receipt["btc_spent_decimal"] for receipt in receipts), Decimal("0"))
    total_sats_spent = sum((receipt["sats_spent_decimal"] for receipt in receipts), Decimal("0"))
    total_reward_ready_usd = sum((receipt["reward_usd"] for receipt in receipts), Decimal("0"))
    total_reward_ready_sats = reward_sats(total_reward_ready_usd, simulated_price)
    total_rewards_paid_usd = sum((decimal_value(event["reward_usd"]) for event in state["payouts"]), Decimal("0"))
    total_rewards_paid_sats = sum(
        (decimal_value(event["reward_sats"]) for event in state["payouts"]),
        Decimal("0"),
    )
    aggregate_upside_usd = sum((receipt["upside_usd"] for receipt in receipts), Decimal("0"))
    return {
        "total_spent_usd": total_spent_usd,
        "total_btc_spent": total_btc_spent,
        "total_sats_spent": total_sats_spent,
        "total_reward_ready_usd": total_reward_ready_usd,
        "total_reward_ready_sats": total_reward_ready_sats,
        "total_rewards_paid_usd": total_rewards_paid_usd,
        "total_rewards_paid_sats": total_rewards_paid_sats,
        "receipt_count": len(receipts),
        "aggregate_upside_usd": aggregate_upside_usd,
    }


def calculate_aggregates(state: dict) -> dict:
    """Build aggregate demo totals and the currently selected receipt."""
    normalize_demo_state(state)
    simulated_price = decimal_value(state["simulated_btc_price"])
    receipts = [enrich_receipt(receipt, simulated_price) for receipt in state["receipts"]]
    selected = None
    for receipt in receipts:
        if receipt["id"] == state.get("selected_receipt_id"):
            selected = receipt
            break
    if selected is None and receipts:
        selected = receipts[-1]
        state["selected_receipt_id"] = selected["id"]

    totals = calculate_alice_totals(state)
    return {
        "simulated_price": simulated_price,
        "receipts": receipts,
        "selected_receipt": selected,
        "reward_ready_usd": totals["total_reward_ready_usd"],
        "reward_ready_sats": totals["total_reward_ready_sats"],
        "rewards_paid_usd": totals["total_rewards_paid_usd"],
        "rewards_paid_sats": totals["total_rewards_paid_sats"],
        **totals,
    }


def pay_alice_reward(state: dict, *, force_price_refresh: bool = False) -> dict | None:
    """Create an aggregate simulated payout and advance reward checkpoints."""
    normalize_demo_state(state)
    future_price = decimal_value(state["simulated_btc_price"])
    rewards_by_receipt = [(receipt, calculate_receipt_reward(state, receipt)) for receipt in state["receipts"]]
    total_reward_usd = sum(
        (reward["receipt_reward_ready_usd"] for _, reward in rewards_by_receipt),
        Decimal("0"),
    )
    total_reward_sats = reward_sats(total_reward_usd, future_price)
    if total_reward_usd <= 0:
        return None

    event = {
        "id": f"alice_payout_{len(state['payouts']) + 1:03d}",
        "receipt_ids": [
            receipt["id"] for receipt, reward in rewards_by_receipt if reward["receipt_reward_ready_usd"] > 0
        ],
        "reward_usd": str(total_reward_usd.quantize(MONEY, rounding=ROUND_HALF_UP)),
        "reward_sats": str(total_reward_sats),
        "to_btc_price": str(future_price),
        "created_label": f"Aggregate payout {len(state['payouts']) + 1}",
    }
    state["payouts"].append(event)
    for receipt, reward in rewards_by_receipt:
        if reward["receipt_reward_ready_usd"] <= 0:
            continue
        receipt["last_reward_checkpoint_price"] = str(future_price)
        receipt["status"] = "Paid"
        receipt["paid_reward_usd_total"] = str(
            (decimal_value(receipt.get("paid_reward_usd_total", "0")) + reward["receipt_reward_ready_usd"]).quantize(
                MONEY, rounding=ROUND_HALF_UP
            )
        )
        receipt.setdefault("payout_events", []).append(event)
    return event


def build_demo_context(state: dict) -> dict:
    """Format demo state into template-ready values."""
    normalize_demo_state(state)
    aggregates = calculate_aggregates(state)
    receipts = aggregates["receipts"]
    selected = aggregates["selected_receipt"]
    latest_payout = state["payouts"][-1] if state["payouts"] else None
    return {
        "merchant": state["merchant"],
        "alice": state["alice"],
        "purchase_items": PURCHASE_ITEMS,
        "upside_buttons": [
            ("+10%", "1.10"),
            ("+25%", "1.25"),
            ("+50%", "1.50"),
            ("+100%", "2.00"),
        ],
        "current_live_btc_price": decimal_value(state["current_live_btc_price"]),
        "current_btc_price_display": price_per_btc(decimal_value(state["current_live_btc_price"])),
        "simulated_btc_price": aggregates["simulated_price"],
        "simulated_btc_price_display": price_per_btc(aggregates["simulated_price"]),
        "last_price_checked_at": state.get("last_price_checked_at") or "Not checked yet",
        "price_status_display": "Live" if state.get("price_source_status") == "live" else "using last price",
        "price_message": state.get("price_message", ""),
        "receipt_count": len(receipts),
        "selected_receipt": selected,
        "visible_receipts": list(reversed(receipts))[:MAX_VISIBLE_RECEIPTS],
        "has_older_receipts": len(receipts) > MAX_VISIBLE_RECEIPTS,
        "latest_receipt": receipts[-1] if receipts else None,
        "total_spent_display": money(aggregates["total_spent_usd"]),
        "total_btc_spent_display": btc(aggregates["total_btc_spent"]),
        "total_sats_spent_display": sats(aggregates["total_sats_spent"]),
        "reward_ready_usd": aggregates["total_reward_ready_usd"],
        "reward_ready_usd_display": money(aggregates["total_reward_ready_usd"]),
        "reward_ready_sats_display": sats(aggregates["total_reward_ready_sats"]),
        "rewards_paid_usd_display": money(aggregates["total_rewards_paid_usd"]),
        "rewards_paid_sats_display": sats(aggregates["total_rewards_paid_sats"]),
        "aggregate_upside_display": money(aggregates["aggregate_upside_usd"]),
        "selected_reward_ready": selected["reward_usd"] if selected else Decimal("0"),
        "selected_has_reward_ready": bool(selected and selected["reward_usd"] > 0),
        "has_reward_ready": aggregates["total_reward_ready_usd"] > 0,
        "latest_payout": latest_payout,
        "latest_payout_reward_usd_display": money(decimal_value(latest_payout["reward_usd"])) if latest_payout else "",
        "latest_payout_reward_sats_display": sats(decimal_value(latest_payout["reward_sats"])) if latest_payout else "",
        "latest_payout_price_display": price_per_btc(decimal_value(latest_payout["to_btc_price"]))
        if latest_payout
        else "",
        "customer_share_display": pct(customer_share(state) * Decimal("100")),
    }


# Compatibility wrappers for older view/action names.
def simulate_payment(state: dict) -> None:
    create_weekly_purchase(state)


def authorize_payout(state: dict) -> None:
    pay_alice_reward(state)


def reset_alice_journey(state: dict) -> None:
    state.clear()
    state.update(deepcopy(DEFAULT_DEMO_STATE))
