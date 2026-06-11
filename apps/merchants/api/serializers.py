from __future__ import annotations

from rest_framework import serializers

from apps.merchants.models import Merchant


class MerchantCreateSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=1)
    nostr_pubkey = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    lightning_address = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ("id", "name", "nostr_pubkey", "lightning_address")


class MerchantReserveHealthSerializer(serializers.Serializer):
    merchant_id = serializers.CharField()
    eligible_liabilities_usd = serializers.DecimalField(max_digits=18, decimal_places=8)
    treasury_allocated_usd = serializers.DecimalField(max_digits=18, decimal_places=8)
    min_coverage_ratio = serializers.DecimalField(max_digits=18, decimal_places=8)
    coverage_ratio = serializers.DecimalField(max_digits=28, decimal_places=8)
    is_healthy = serializers.BooleanField()
    pause_accrual = serializers.BooleanField()
