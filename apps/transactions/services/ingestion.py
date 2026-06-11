from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from apps.common.adapters.btc_price_oracle import BtcPriceOracle
from apps.common.adapters.payment_processor import PaymentProcessor
from apps.receipts.models import RewardCalculation, RewardReceipt
from apps.rewards.domain.reward import RewardInput, calculate_reward
from apps.rewards.models import RewardPolicy
from apps.transactions.models import (
    BtcTransaction,
    IngestionRequest,
    IngestionRequestStatus,
)


@dataclass(frozen=True)
class IngestTransactionInput:
    """Validated transaction data passed from the API layer into ingestion."""

    merchant_id: str
    customer_id: str
    reward_policy_id: str | None
    sats_spent: int
    btc_usd_price_at_purchase: Decimal
    idempotency_key: str | None = None


@dataclass(frozen=True)
class RewardCalculationSummary:
    """Compact reward calculation returned by transaction ingestion."""

    customer_reward_usd: Decimal
    incremental_appreciation_usd: Decimal
    current_value_usd: Decimal
    basis_value_usd: Decimal


@dataclass(frozen=True)
class IngestTransactionResult:
    """IDs and reward summary produced after persisting a transaction graph."""

    transaction_id: str
    payment_external_id: str
    reward_receipt_id: str
    reward_calculation: RewardCalculationSummary
    idempotent_replay: bool


class IdempotencyConflict(ValueError):
    """Raised when an idempotency key is reused for an incompatible request."""

    pass


class IdempotencyInProgress(ValueError):
    """Raised when another request currently owns the same idempotency key."""

    pass


def _new_id() -> str:
    return uuid4().hex


def _request_hash(payload: IngestTransactionInput) -> str:
    normalized = {
        "merchant_id": payload.merchant_id,
        "customer_id": payload.customer_id,
        "reward_policy_id": payload.reward_policy_id,
        "sats_spent": payload.sats_spent,
        "btc_usd_price_at_purchase": str(payload.btc_usd_price_at_purchase),
    }
    body = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _json_payload(result: IngestTransactionResult) -> dict[str, object]:
    return {
        "transaction_id": result.transaction_id,
        "payment_external_id": result.payment_external_id,
        "reward_receipt_id": result.reward_receipt_id,
        "reward_calculation": {key: str(value) for key, value in asdict(result.reward_calculation).items()},
    }


def ingest_transaction(
    payload: IngestTransactionInput,
    *,
    payment_processor: PaymentProcessor,
    price_oracle: BtcPriceOracle,
) -> IngestTransactionResult:
    """Record a BTC transaction, reward receipt, and calculation atomically.

    The service owns idempotency semantics for transaction creation. A replay
    with the same request hash returns the original persisted result; a changed
    payload under the same key is rejected.
    """
    request_hash = _request_hash(payload)
    ingestion_request: IngestionRequest | None = None

    if payload.idempotency_key:
        with transaction.atomic():
            existing = (
                IngestionRequest.objects.select_for_update()
                .filter(idempotency_key=payload.idempotency_key)
                .select_related("transaction")
                .first()
            )
            if existing is not None:
                if existing.request_hash and existing.request_hash != request_hash:
                    raise IdempotencyConflict("Idempotency-Key was already used with a different request payload.")
                if existing.status == IngestionRequestStatus.PROCESSING:
                    raise IdempotencyInProgress("Idempotency-Key is already processing.")
                if existing.status == IngestionRequestStatus.FAILED:
                    raise IdempotencyConflict("Idempotency-Key belongs to a failed ingestion; retry with a new key.")
                if existing.transaction_id is None:
                    raise IdempotencyConflict("Idempotency-Key has no completed transaction.")
                return _load_existing_result(existing.transaction_id, idempotent_replay=True)

            ingestion_request = IngestionRequest.objects.create(
                id=_new_id(),
                idempotency_key=payload.idempotency_key,
                request_hash=request_hash,
                status=IngestionRequestStatus.PROCESSING,
            )

    try:
        payment = payment_processor.record_btc_payment(
            amount_sats=payload.sats_spent,
            merchant_id=payload.merchant_id,
            customer_id=payload.customer_id,
        )
    except Exception:
        _mark_ingestion_failed(ingestion_request)
        raise

    try:
        return _persist_transaction_graph(
            payload=payload,
            payment_external_id=payment.external_id,
            price_oracle=price_oracle,
            ingestion_request=ingestion_request,
        )
    except Exception:
        _mark_ingestion_failed(ingestion_request)
        raise


def _persist_transaction_graph(
    *,
    payload: IngestTransactionInput,
    payment_external_id: str,
    price_oracle: BtcPriceOracle,
    ingestion_request: IngestionRequest | None,
) -> IngestTransactionResult:
    with transaction.atomic():
        btc_transaction = BtcTransaction.objects.create(
            id=_new_id(),
            merchant_id=payload.merchant_id,
            customer_id=payload.customer_id,
            reward_policy_id=payload.reward_policy_id,
            sats_spent=payload.sats_spent,
            btc_usd_price_at_purchase=payload.btc_usd_price_at_purchase,
            payment_external_id=payment_external_id,
        )

        merchant_retention_bps = 0
        customer_share_bps = 0
        if payload.reward_policy_id:
            policy = RewardPolicy.objects.filter(id=payload.reward_policy_id).first()
            if policy is not None:
                merchant_retention_bps = policy.merchant_retention_bps
                customer_share_bps = policy.customer_share_bps

        reward_result = calculate_reward(
            RewardInput(
                btc_spent_sats=payload.sats_spent,
                merchant_retention_bps=merchant_retention_bps,
                customer_share_bps=customer_share_bps,
                current_btc_usd_price=price_oracle.get_current_price_usd(),
                btc_usd_price_at_purchase=payload.btc_usd_price_at_purchase,
                high_water_mark_value_usd=Decimal("0"),
            )
        )

        receipt = RewardReceipt.objects.create(
            id=_new_id(),
            merchant_id=payload.merchant_id,
            customer_id=payload.customer_id,
            transaction=btc_transaction,
            high_water_mark_value_usd=reward_result.next_high_water_mark_value_usd,
            merchant_coverage_ratio=Decimal("1.0"),
            accrual_paused=False,
        )

        RewardCalculation.objects.create(
            id=_new_id(),
            reward_receipt=receipt,
            eligible_btc_notional_sats=reward_result.eligible_btc_notional_sats,
            basis_value_usd=reward_result.basis_value_usd,
            current_value_usd=reward_result.current_value_usd,
            incremental_appreciation_usd=reward_result.incremental_appreciation_usd,
            customer_reward_usd=reward_result.customer_reward_usd,
        )

        result = IngestTransactionResult(
            transaction_id=btc_transaction.id,
            payment_external_id=payment_external_id,
            reward_receipt_id=receipt.id,
            reward_calculation=RewardCalculationSummary(
                customer_reward_usd=reward_result.customer_reward_usd,
                incremental_appreciation_usd=reward_result.incremental_appreciation_usd,
                current_value_usd=reward_result.current_value_usd,
                basis_value_usd=reward_result.basis_value_usd,
            ),
            idempotent_replay=False,
        )

        if payload.idempotency_key:
            if ingestion_request is None:
                raise RuntimeError("Expected claimed ingestion request for idempotent transaction")
            locked_request = IngestionRequest.objects.select_for_update().get(id=ingestion_request.id)
            locked_request.response_payload = _json_payload(result)
            locked_request.transaction = btc_transaction
            locked_request.status = IngestionRequestStatus.COMPLETED
            locked_request.save(
                update_fields=[
                    "response_payload",
                    "transaction",
                    "status",
                    "updated_at",
                ]
            )

        return result


def _mark_ingestion_failed(ingestion_request: IngestionRequest | None) -> None:
    if ingestion_request is None:
        return
    with transaction.atomic():
        IngestionRequest.objects.filter(id=ingestion_request.id, status=IngestionRequestStatus.PROCESSING).update(
            status=IngestionRequestStatus.FAILED,
            response_payload={"error": "ingestion_failed"},
        )


def _load_existing_result(transaction_id: str, *, idempotent_replay: bool) -> IngestTransactionResult:
    btc_transaction = BtcTransaction.objects.get(id=transaction_id)
    receipt = RewardReceipt.objects.get(transaction_id=transaction_id)
    calculation = receipt.calculations.order_by("-created_at", "-id").first()
    if calculation is None:
        raise RuntimeError("Expected reward calculation for existing transaction")

    return IngestTransactionResult(
        transaction_id=btc_transaction.id,
        payment_external_id=btc_transaction.payment_external_id or "",
        reward_receipt_id=receipt.id,
        reward_calculation=RewardCalculationSummary(
            customer_reward_usd=calculation.customer_reward_usd,
            incremental_appreciation_usd=calculation.incremental_appreciation_usd,
            current_value_usd=calculation.current_value_usd,
            basis_value_usd=calculation.basis_value_usd,
        ),
        idempotent_replay=idempotent_replay,
    )
