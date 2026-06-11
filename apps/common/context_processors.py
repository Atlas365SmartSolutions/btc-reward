from __future__ import annotations

from django.conf import settings

from apps.merchants.models import Merchant
from apps.receipts.models import RewardReceipt
from apps.rewards.models import PolicyStatus, RewardPolicy
from apps.transactions.models import (
    BtcTransaction,
    IngestionRequest,
    IngestionRequestStatus,
)
from apps.treasury.models import PayoutBatch, PayoutStatus, TreasuryWallet
from apps.treasury.services.reserve_health import get_merchant_reserve_health


def admin_dashboard(request):
    if not request.path.startswith("/admin/") or not request.user.is_authenticated or not request.user.is_staff:
        return {}

    latest_transactions = list(
        BtcTransaction.objects.select_related("merchant", "customer").order_by("-created_at", "-id")[:5]
    )
    latest_ingestions = list(IngestionRequest.objects.select_related("transaction").order_by("-created_at", "-id")[:5])

    reserve_rows = []
    for merchant in Merchant.objects.order_by("created_at", "id")[:6]:
        health = get_merchant_reserve_health(merchant_id=merchant.id)
        reserve_rows.append(
            {
                "merchant": merchant,
                "coverage_ratio": str(health.coverage_ratio),
                "liabilities_usd": health.eligible_liabilities_usd,
                "allocated_usd": health.treasury_allocated_usd,
                "is_healthy": health.is_healthy,
            }
        )

    return {
        "ops_dashboard": {
            "counts": {
                "merchants": Merchant.objects.count(),
                "active_policies": RewardPolicy.objects.filter(status=PolicyStatus.ACTIVE).count(),
                "transactions": BtcTransaction.objects.count(),
                "receipts": RewardReceipt.objects.count(),
                "active_wallets": TreasuryWallet.objects.filter(status="ACTIVE").count(),
                "pending_ingestions": IngestionRequest.objects.filter(status=IngestionRequestStatus.PROCESSING).count(),
                "failed_ingestions": IngestionRequest.objects.filter(status=IngestionRequestStatus.FAILED).count(),
                "queued_payouts": PayoutBatch.objects.filter(status=PayoutStatus.QUEUED).count(),
            },
            "latest_transactions": latest_transactions,
            "latest_ingestions": latest_ingestions,
            "reserve_rows": reserve_rows,
            "runtime": {
                "debug": settings.DEBUG,
                "payment_backend": settings.PAYMENT_PROCESSOR_BACKEND,
                "price_oracle_backend": settings.BTC_PRICE_ORACLE_BACKEND,
                "database_engine": settings.DATABASES["default"]["ENGINE"].rsplit(".", maxsplit=1)[-1],
                "database_host": settings.DATABASES["default"].get("HOST") or "local",
            },
        }
    }
