from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.merchants.models import Merchant
from apps.rewards.models import RewardPolicy


class RewardCalculationRequestSerializer(serializers.Serializer):
    btc_spent_sats = serializers.IntegerField(min_value=1)
    merchant_retention_bps = serializers.IntegerField(min_value=0, max_value=10000)
    customer_share_bps = serializers.IntegerField(min_value=0, max_value=10000)
    btc_usd_price_at_purchase = serializers.DecimalField(
        max_digits=18, decimal_places=8, min_value=Decimal("0.00000001")
    )
    high_water_mark_value_usd = serializers.DecimalField(max_digits=18, decimal_places=8, min_value=0)


class RewardCalculationResponseSerializer(serializers.Serializer):
    eligible_btc_notional_sats = serializers.IntegerField()
    eligible_btc_notional_btc = serializers.DecimalField(max_digits=28, decimal_places=8)
    current_value_usd = serializers.DecimalField(max_digits=18, decimal_places=8)
    basis_value_usd = serializers.DecimalField(max_digits=18, decimal_places=8)
    incremental_appreciation_usd = serializers.DecimalField(max_digits=18, decimal_places=8)
    customer_reward_usd = serializers.DecimalField(max_digits=18, decimal_places=8)
    next_high_water_mark_value_usd = serializers.DecimalField(max_digits=18, decimal_places=8)


class RewardPolicyCreateSerializer(serializers.Serializer):
    merchant_id = serializers.CharField(min_length=1)
    merchant_retention_bps = serializers.IntegerField(min_value=0, max_value=10000)
    customer_share_bps = serializers.IntegerField(min_value=0, max_value=10000)
    min_coverage_ratio = serializers.DecimalField(max_digits=8, decimal_places=4, min_value=Decimal("0.0001"))

    def validate_merchant_id(self, value):
        if not Merchant.objects.filter(id=value).exists():
            raise serializers.ValidationError("Merchant does not exist.")
        return value


class RewardPolicySerializer(serializers.ModelSerializer):
    merchant_id = serializers.CharField()

    class Meta:
        model = RewardPolicy
        fields = (
            "id",
            "merchant_id",
            "merchant_retention_bps",
            "customer_share_bps",
            "min_coverage_ratio",
            "status",
        )
