from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.merchants.models import Customer, Merchant
from apps.rewards.models import PolicyStatus, RewardPolicy
from apps.transactions.models import (
    BtcTransaction,
    IngestionRequest,
    IngestionRequestStatus,
)


@pytest.mark.django_db
def test_reward_policy_rejects_out_of_range_bps(seeded_core_entities) -> None:
    with pytest.raises(IntegrityError):
        RewardPolicy.objects.create(
            id="rp_invalid",
            merchant_id=seeded_core_entities["merchant_id"],
            merchant_retention_bps=10001,
            customer_share_bps=2000,
            min_coverage_ratio=Decimal("1.1000"),
        )


@pytest.mark.django_db
def test_transaction_rejects_non_positive_amounts(seeded_core_entities) -> None:
    with pytest.raises(IntegrityError):
        BtcTransaction.objects.create(
            id="tx_invalid",
            merchant_id=seeded_core_entities["merchant_id"],
            customer_id=seeded_core_entities["customer_id"],
            reward_policy_id=seeded_core_entities["reward_policy_id"],
            sats_spent=0,
            btc_usd_price_at_purchase=Decimal("60000.00000000"),
            payment_external_id="mockpay_invalid",
        )


@pytest.mark.django_db
def test_ingestion_request_rejects_duplicate_idempotency_key(
    seeded_core_entities,
) -> None:
    first_tx = BtcTransaction.objects.create(
        id="tx_one",
        merchant_id=seeded_core_entities["merchant_id"],
        customer_id=seeded_core_entities["customer_id"],
        reward_policy_id=seeded_core_entities["reward_policy_id"],
        sats_spent=100,
        btc_usd_price_at_purchase=Decimal("60000.00000000"),
        payment_external_id="mockpay_one",
    )
    second_tx = BtcTransaction.objects.create(
        id="tx_two",
        merchant_id=seeded_core_entities["merchant_id"],
        customer_id=seeded_core_entities["customer_id"],
        reward_policy_id=seeded_core_entities["reward_policy_id"],
        sats_spent=200,
        btc_usd_price_at_purchase=Decimal("60000.00000000"),
        payment_external_id="mockpay_two",
    )
    IngestionRequest.objects.create(id="ir_one", idempotency_key="dup-key", transaction=first_tx)

    with pytest.raises(IntegrityError):
        IngestionRequest.objects.create(id="ir_two", idempotency_key="dup-key", transaction=second_tx)


@pytest.mark.django_db
def test_merchant_rejects_duplicate_lightning_address() -> None:
    Merchant.objects.create(id="m_one", name="Merchant One", lightning_address="ops@example.com")

    with pytest.raises(IntegrityError):
        Merchant.objects.create(id="m_two", name="Merchant Two", lightning_address="ops@example.com")


@pytest.mark.django_db
def test_customer_rejects_duplicate_email_per_merchant_case_insensitive(
    seeded_core_entities,
) -> None:
    with pytest.raises(IntegrityError):
        Customer.objects.create(
            id="c_duplicate",
            merchant_id=seeded_core_entities["merchant_id"],
            email="ALICE@example.com",
        )


@pytest.mark.django_db
def test_reward_policy_allows_only_one_active_policy_per_merchant(
    seeded_core_entities,
) -> None:
    RewardPolicy.objects.create(
        id="rp_draft",
        merchant_id=seeded_core_entities["merchant_id"],
        merchant_retention_bps=4000,
        customer_share_bps=1500,
        min_coverage_ratio=Decimal("1.1000"),
        status=PolicyStatus.DRAFT,
    )

    with pytest.raises(IntegrityError):
        RewardPolicy.objects.create(
            id="rp_active_two",
            merchant_id=seeded_core_entities["merchant_id"],
            merchant_retention_bps=4000,
            customer_share_bps=1500,
            min_coverage_ratio=Decimal("1.1000"),
            status=PolicyStatus.ACTIVE,
        )


@pytest.mark.django_db
def test_payment_external_id_is_unique_when_present(seeded_core_entities) -> None:
    BtcTransaction.objects.create(
        id="tx_pay_one",
        merchant_id=seeded_core_entities["merchant_id"],
        customer_id=seeded_core_entities["customer_id"],
        reward_policy_id=seeded_core_entities["reward_policy_id"],
        sats_spent=100,
        btc_usd_price_at_purchase=Decimal("60000.00000000"),
        payment_external_id="provider_payment_1",
    )

    with pytest.raises(IntegrityError):
        BtcTransaction.objects.create(
            id="tx_pay_two",
            merchant_id=seeded_core_entities["merchant_id"],
            customer_id=seeded_core_entities["customer_id"],
            reward_policy_id=seeded_core_entities["reward_policy_id"],
            sats_spent=200,
            btc_usd_price_at_purchase=Decimal("60000.00000000"),
            payment_external_id="provider_payment_1",
        )


@pytest.mark.django_db
def test_completed_ingestion_request_requires_transaction() -> None:
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IngestionRequest.objects.create(
                id="ir_completed_without_tx",
                idempotency_key="completed-without-tx",
                status=IngestionRequestStatus.COMPLETED,
            )

    IngestionRequest.objects.create(
        id="ir_processing_without_tx",
        idempotency_key="processing-without-tx",
        status=IngestionRequestStatus.PROCESSING,
    )
