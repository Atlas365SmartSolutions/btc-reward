from __future__ import annotations

from rest_framework import serializers

from apps.merchants.models import Customer, Merchant
from apps.receipts.models import RewardCalculation, RewardReceipt
from apps.transactions.models import BtcTransaction


class ReceiptTransactionSerializer(serializers.ModelSerializer):
    merchant_id = serializers.CharField()
    customer_id = serializers.CharField()
    reward_policy_id = serializers.CharField(allow_null=True)

    class Meta:
        model = BtcTransaction
        fields = (
            "id",
            "merchant_id",
            "customer_id",
            "reward_policy_id",
            "sats_spent",
            "btc_usd_price_at_purchase",
            "payment_external_id",
        )


class ReceiptCalculationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardCalculation
        fields = (
            "id",
            "eligible_btc_notional_sats",
            "basis_value_usd",
            "current_value_usd",
            "incremental_appreciation_usd",
            "customer_reward_usd",
        )


class ReceiptCustomerSerializer(serializers.ModelSerializer):
    merchant_id = serializers.CharField()

    class Meta:
        model = Customer
        fields = ("id", "merchant_id")


class ReceiptMerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ("id", "name")


class ReceiptSerializer(serializers.ModelSerializer):
    merchant_id = serializers.CharField()
    customer_id = serializers.CharField()
    transaction_id = serializers.CharField()
    transaction = ReceiptTransactionSerializer()
    calculations = ReceiptCalculationSerializer(many=True)
    customer = ReceiptCustomerSerializer()
    merchant = ReceiptMerchantSerializer()

    class Meta:
        model = RewardReceipt
        fields = (
            "id",
            "merchant_id",
            "customer_id",
            "transaction_id",
            "status",
            "high_water_mark_value_usd",
            "merchant_coverage_ratio",
            "accrual_paused",
            "transaction",
            "calculations",
            "customer",
            "merchant",
        )
