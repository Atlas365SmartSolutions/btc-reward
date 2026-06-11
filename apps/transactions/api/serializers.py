from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.merchants.models import Customer, Merchant
from apps.rewards.models import RewardPolicy


class TransactionCreateSerializer(serializers.Serializer):
    merchant_id = serializers.CharField(min_length=1)
    customer_id = serializers.CharField(min_length=1)
    reward_policy_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    sats_spent = serializers.IntegerField(min_value=1)
    btc_usd_price_at_purchase = serializers.DecimalField(
        max_digits=18, decimal_places=8, min_value=Decimal("0.00000001")
    )

    def validate_reward_policy_id(self, value):
        return value or None

    def validate(self, attrs):
        merchant_id = attrs["merchant_id"]
        customer_id = attrs["customer_id"]
        reward_policy_id = attrs.get("reward_policy_id")

        if not Merchant.objects.filter(id=merchant_id).exists():
            raise serializers.ValidationError({"merchant_id": "Merchant does not exist."})

        if not Customer.objects.filter(id=customer_id, merchant_id=merchant_id).exists():
            raise serializers.ValidationError({"customer_id": "Customer does not belong to merchant."})

        if reward_policy_id and not RewardPolicy.objects.filter(id=reward_policy_id, merchant_id=merchant_id).exists():
            raise serializers.ValidationError({"reward_policy_id": "Reward policy does not belong to merchant."})

        return attrs


class PaymentRecordSerializer(serializers.Serializer):
    external_id = serializers.CharField()


class RewardCalculationSummarySerializer(serializers.Serializer):
    customer_reward_usd = serializers.DecimalField(max_digits=18, decimal_places=8)
    incremental_appreciation_usd = serializers.DecimalField(max_digits=18, decimal_places=8)
    current_value_usd = serializers.DecimalField(max_digits=18, decimal_places=8)
    basis_value_usd = serializers.DecimalField(max_digits=18, decimal_places=8)
