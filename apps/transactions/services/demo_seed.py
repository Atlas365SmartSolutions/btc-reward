from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.merchants.models import Customer, Merchant
from apps.receipts.models import RewardCalculation, RewardReceipt
from apps.rewards.domain.reward import RewardInput, calculate_reward
from apps.rewards.models import PolicyStatus, RewardPolicy
from apps.transactions.models import BtcTransaction
from apps.treasury.models import TreasurySnapshot, TreasuryWallet, WalletStatus


def seed_demo_data() -> dict[str, str]:
    with transaction.atomic():
        merchant, _ = Merchant.objects.get_or_create(
            id="m_demo",
            defaults={
                "name": "Satoshi Cafe",
                "nostr_pubkey": "npub1merchant",
                "lightning_address": "ops@sats.cafe",
                "encrypted_nwc_uri": "enc://placeholder",
            },
        )
        customer, _ = Customer.objects.get_or_create(
            id="c_demo",
            defaults={
                "merchant": merchant,
                "email": "alice@example.com",
                "nostr_pubkey": "npub1alice",
                "lightning_address": "alice@getalby.com",
            },
        )
        policy, _ = RewardPolicy.objects.get_or_create(
            id="rp_demo",
            defaults={
                "merchant": merchant,
                "merchant_retention_bps": 3500,
                "customer_share_bps": 2500,
                "min_coverage_ratio": Decimal("1.1000"),
                "status": PolicyStatus.ACTIVE,
            },
        )
        btc_transaction, _ = BtcTransaction.objects.get_or_create(
            id="tx_demo",
            defaults={
                "merchant": merchant,
                "customer": customer,
                "reward_policy": policy,
                "sats_spent": 500_000,
                "btc_usd_price_at_purchase": Decimal("64000.00000000"),
                "payment_external_id": "mockpay_seed_demo",
            },
        )

        reward = calculate_reward(
            RewardInput(
                btc_spent_sats=500_000,
                merchant_retention_bps=policy.merchant_retention_bps,
                customer_share_bps=policy.customer_share_bps,
                current_btc_usd_price=Decimal("70000.00000000"),
                btc_usd_price_at_purchase=Decimal("64000.00000000"),
                high_water_mark_value_usd=Decimal("100.00000000"),
            )
        )

        receipt, _ = RewardReceipt.objects.get_or_create(
            id="rr_demo",
            defaults={
                "merchant": merchant,
                "customer": customer,
                "transaction": btc_transaction,
                "signed_reward_receipt_hash": "signed_hash_placeholder",
                "high_water_mark_value_usd": reward.next_high_water_mark_value_usd,
                "merchant_coverage_ratio": Decimal("1.25000000"),
                "accrual_paused": False,
            },
        )
        RewardCalculation.objects.get_or_create(
            id="rc_demo",
            defaults={
                "reward_receipt": receipt,
                "eligible_btc_notional_sats": reward.eligible_btc_notional_sats,
                "basis_value_usd": reward.basis_value_usd,
                "current_value_usd": reward.current_value_usd,
                "incremental_appreciation_usd": reward.incremental_appreciation_usd,
                "customer_reward_usd": reward.customer_reward_usd,
            },
        )
        wallet, _ = TreasuryWallet.objects.get_or_create(
            id="tw_demo",
            defaults={
                "merchant": merchant,
                "label": "Primary Treasury",
                "status": WalletStatus.ACTIVE,
                "btc_balance": Decimal("0.25000000"),
            },
        )
        TreasurySnapshot.objects.get_or_create(
            id="ts_demo",
            defaults={
                "treasury_wallet": wallet,
                "btc_usd_price": Decimal("70000.00000000"),
                "allocated_usd_value": Decimal("130.00000000"),
                "coverage_ratio": Decimal("1.25000000"),
                "snapshot_source": "seed",
            },
        )

    return {
        "merchant_id": "m_demo",
        "customer_id": "c_demo",
        "reward_policy_id": "rp_demo",
        "transaction_id": "tx_demo",
        "receipt_id": "rr_demo",
        "wallet_id": "tw_demo",
        "snapshot_id": "ts_demo",
    }
