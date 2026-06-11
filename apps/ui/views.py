from __future__ import annotations

from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.db import DatabaseError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.merchants.models import Customer, Merchant
from apps.receipts.models import RewardCalculation, RewardReceipt
from apps.rewards.models import PolicyStatus, RewardPolicy
from apps.transactions.models import (
    BtcTransaction,
    IngestionRequest,
    IngestionRequestStatus,
)
from apps.treasury.models import (
    PayoutBatch,
    PayoutStatus,
    TreasurySnapshot,
    TreasuryWallet,
)
from apps.treasury.services.reserve_health import (
    MerchantReserveHealthResult,
    get_merchant_reserve_health,
)
from apps.ui.services.demo_data import demo_merchant, demo_receipt
from apps.ui.services.poc_demo import (
    authorize_payout,
    build_demo_context,
    create_weekly_purchase,
    get_demo_state,
    reset_alice_journey,
    reset_demo_state,
    save_demo_state,
    select_receipt,
    set_demo_price,
    set_simulated_price_from_live,
    set_simulated_upside,
    simulate_payment,
    sync_live_btc_price,
)


def _empty_reserve_health() -> MerchantReserveHealthResult:
    return MerchantReserveHealthResult(
        eligible_liabilities_usd=Decimal("0"),
        treasury_allocated_usd=Decimal("0"),
        min_coverage_ratio=Decimal("1"),
        coverage_ratio=Decimal("1"),
        is_healthy=True,
        pause_accrual=False,
    )


def _home_snapshot() -> dict[str, object]:
    try:
        latest_transaction = (
            BtcTransaction.objects.select_related("merchant", "customer").order_by("-created_at", "-id").first()
        )
        latest_receipt = (
            RewardReceipt.objects.select_related("merchant", "customer", "transaction")
            .order_by("-created_at", "-id")
            .first()
        )
        latest_ingestion = IngestionRequest.objects.select_related("transaction").order_by("-created_at", "-id").first()
        merchants = list(Merchant.objects.order_by("created_at", "id")[:4])
        featured_merchant = merchants[0] if merchants else demo_merchant
        featured_health = get_merchant_reserve_health(merchant_id=featured_merchant.id)
        featured_policy = (
            RewardPolicy.objects.filter(merchant_id=featured_merchant.id).order_by("-created_at", "-id").first()
        )

        counts = {
            "merchants": Merchant.objects.count(),
            "customers": Customer.objects.count(),
            "active_policies": RewardPolicy.objects.filter(status=PolicyStatus.ACTIVE).count(),
            "transactions": BtcTransaction.objects.count(),
            "receipts": RewardReceipt.objects.count(),
            "active_wallets": TreasuryWallet.objects.filter(status="ACTIVE").count(),
            "pending_ingestions": IngestionRequest.objects.filter(status=IngestionRequestStatus.PROCESSING).count(),
            "queued_payouts": PayoutBatch.objects.filter(status=PayoutStatus.QUEUED).count(),
        }
    except DatabaseError:
        latest_transaction = None
        latest_receipt = None
        latest_ingestion = None
        featured_merchant = demo_merchant
        featured_health = _empty_reserve_health()
        featured_policy = None
        counts = {
            "merchants": 0,
            "customers": 0,
            "active_policies": 0,
            "transactions": 0,
            "receipts": 0,
            "active_wallets": 0,
            "pending_ingestions": 0,
            "queued_payouts": 0,
        }

    return {
        "counts": counts,
        "latest_transaction": latest_transaction,
        "latest_receipt": latest_receipt,
        "latest_ingestion": latest_ingestion,
        "featured_merchant": featured_merchant,
        "featured_health": featured_health,
        "featured_policy": featured_policy,
        "featured_coverage_ratio": str(featured_health.coverage_ratio),
    }


def _merchant_rows() -> list[dict[str, object]]:
    merchants = list(Merchant.objects.order_by("created_at", "id"))
    if not merchants:
        merchants = [demo_merchant]

    rows: list[dict[str, object]] = []
    for merchant in merchants:
        reserve_health = get_merchant_reserve_health(merchant_id=merchant.id)
        rows.append(
            {
                "merchant": merchant,
                "policy_count": RewardPolicy.objects.filter(merchant_id=merchant.id).count(),
                "transaction_count": BtcTransaction.objects.filter(merchant_id=merchant.id).count(),
                "wallet_count": TreasuryWallet.objects.filter(merchant_id=merchant.id).count(),
                "coverage_ratio": str(reserve_health.coverage_ratio),
                "is_healthy": reserve_health.is_healthy,
            }
        )

    return rows


def home(request):
    state = get_demo_state(request.session)
    context = {
        "page_title": "Earn Forever",
        **_home_snapshot(),
        **build_demo_context(state),
    }
    return render(request, "home.html", context)


def home_summary(request):
    return render(
        request,
        "home_summary.html",
        {"page_title": "Earn Forever MVP", **_home_snapshot()},
    )


@staff_member_required
def merchants_page(request):
    return render(
        request,
        "merchants.html",
        {"page_title": "Merchants", "merchant_rows": _merchant_rows()},
    )


@staff_member_required
def merchant_detail(request, merchant_id: str):
    merchant = Merchant.objects.filter(id=merchant_id).first()
    if merchant is None and merchant_id == demo_merchant.id:
        merchant = demo_merchant
    if merchant is None:
        raise Http404("Merchant not found")

    reserve_health = get_merchant_reserve_health(merchant_id=merchant_id)
    return render(
        request,
        "merchant_detail.html",
        {
            "page_title": f"Merchant {merchant_id}",
            "merchant": merchant,
            "merchant_id": merchant_id,
            "policy_count": RewardPolicy.objects.filter(merchant_id=merchant_id).count(),
            "transaction_count": BtcTransaction.objects.filter(merchant_id=merchant_id).count(),
            "wallet_count": TreasuryWallet.objects.filter(merchant_id=merchant_id).count(),
            "coverage_ratio": str(reserve_health.coverage_ratio),
            "is_healthy": reserve_health.is_healthy,
            "customer_liabilities_usd": reserve_health.eligible_liabilities_usd,
            "active_policy": RewardPolicy.objects.filter(merchant_id=merchant_id, status=PolicyStatus.ACTIVE)
            .order_by("-created_at", "-id")
            .first(),
            "latest_transaction": BtcTransaction.objects.filter(merchant_id=merchant_id)
            .select_related("customer", "reward_policy")
            .order_by("-created_at", "-id")
            .first(),
            "latest_wallet": TreasuryWallet.objects.filter(merchant_id=merchant_id)
            .order_by("-created_at", "-id")
            .first(),
        },
    )


@staff_member_required
def merchant_policies(request, merchant_id: str):
    policies = RewardPolicy.objects.filter(merchant_id=merchant_id).order_by("-created_at", "-id")
    return render(
        request,
        "merchant_policies.html",
        {"page_title": "Policies", "policies": policies, "merchant_id": merchant_id},
    )


@staff_member_required
def merchant_transactions(request, merchant_id: str):
    transactions = BtcTransaction.objects.filter(merchant_id=merchant_id).order_by("-created_at", "-id")
    return render(
        request,
        "merchant_transactions.html",
        {
            "page_title": "Transactions",
            "transactions": transactions,
            "merchant_id": merchant_id,
        },
    )


@staff_member_required
def merchant_treasury(request, merchant_id: str):
    wallets = list(TreasuryWallet.objects.filter(merchant_id=merchant_id).order_by("-created_at", "-id"))
    snapshots = TreasurySnapshot.objects.filter(treasury_wallet_id__in=[wallet.id for wallet in wallets]).order_by(
        "-created_at", "-id"
    )
    reserve_health = get_merchant_reserve_health(merchant_id=merchant_id)
    return render(
        request,
        "merchant_treasury.html",
        {
            "page_title": "Treasury",
            "merchant_id": merchant_id,
            "wallets": wallets,
            "snapshots": snapshots,
            "reserve_health": reserve_health,
            "coverage_ratio": str(reserve_health.coverage_ratio),
        },
    )


@staff_member_required
def receipt_page(request, receipt_id: str):
    receipt = RewardReceipt.objects.filter(id=receipt_id).first()
    reward_customer_name = demo_receipt.customer_name
    reward_amount = demo_receipt.customer_reward_usd

    if receipt is not None:
        customer = Customer.objects.filter(id=receipt.customer_id).first()
        calculation = RewardCalculation.objects.filter(reward_receipt=receipt).order_by("-created_at", "-id").first()
        reward_customer_name = customer.email if customer is not None else demo_receipt.customer_name
        reward_amount = calculation.customer_reward_usd if calculation is not None else demo_receipt.customer_reward_usd

    return render(
        request,
        "receipt.html",
        {
            "page_title": f"Reward Receipt {receipt_id}",
            "receipt_id": receipt_id,
            "customer_name": reward_customer_name,
            "customer_reward_usd": reward_amount,
        },
    )


def demo_dashboard(request):
    state = get_demo_state(request.session)
    sync_live_btc_price(state)
    save_demo_state(request.session, state)
    return render(
        request,
        "demo/dashboard.html",
        {"page_title": "Earn Forever Demo", **build_demo_context(state)},
    )


def demo_receipt_page(request, receipt_id: str):
    state = get_demo_state(request.session)
    sync_live_btc_price(state)
    save_demo_state(request.session, state)
    context = build_demo_context(state)
    if receipt_id not in {"rr_demo", "rr_demo_alice_001", "alice"}:
        raise Http404("Reward receipt not found")
    return render(
        request,
        "demo/receipt.html",
        {"page_title": "Alice Reward Receipt", **context},
    )


@require_POST
def demo_action(request, action: str | None = None):
    action = action or request.POST.get("action", "")
    state = reset_demo_state(request.session) if action == "reset" else get_demo_state(request.session)

    if action == "alice_purchase":
        create_weekly_purchase(state, item_type=request.POST.get("item_type", "coffee"))
    elif action == "simulate_payment":
        simulate_payment(state)
    elif action in {"price", "quick_price", "set_price", "demo_upside"}:
        set_demo_price(
            state,
            request.POST.get("value", request.POST.get("current_btc_price", "150000")),
        )
    elif action == "advance_price":
        set_simulated_upside(state, request.POST.get("multiplier", "1.10"))
    elif action == "current_live_price":
        set_simulated_price_from_live(state)
    elif action == "sync_live_price":
        sync_live_btc_price(state, force_refresh=request.POST.get("force") == "1")
    elif action == "reset_alice":
        reset_alice_journey(state)
    elif action == "authorize_payout":
        authorize_payout(state)
    elif action == "select_receipt":
        select_receipt(state, request.POST.get("receipt_id", ""))

    if action != "reset":
        save_demo_state(request.session, state)

    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "demo/_dashboard_state.html",
            {
                "page_title": "Earn Forever Demo",
                "is_hx": True,
                **build_demo_context(state),
            },
        )

    next_url = request.POST.get("next") or "/demo"
    return redirect(next_url)


@staff_member_required
def admin_demo(request):
    return render(
        request,
        "admin_demo.html",
        {
            "page_title": "Admin Demo",
            "system_record_text": "System of record: PostgreSQL + Django ORM. Nostr is optional.",
            "admin_sections": [
                {"label": "Merchants", "url": "/admin/merchants/merchant/"},
                {"label": "Policies", "url": "/admin/rewards/rewardpolicy/"},
                {"label": "Transactions", "url": "/admin/transactions/btctransaction/"},
                {"label": "Receipts", "url": "/admin/receipts/rewardreceipt/"},
                {"label": "Treasury", "url": "/admin/treasury/treasurywallet/"},
            ],
        },
    )
