from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.treasury.models import TreasurySnapshot, TreasuryWallet


class ReserveHealthRequestSerializer(serializers.Serializer):
    eligible_liabilities_usd = serializers.DecimalField(max_digits=18, decimal_places=8, min_value=0)
    treasury_allocated_usd = serializers.DecimalField(max_digits=18, decimal_places=8, min_value=0)
    min_coverage_ratio = serializers.DecimalField(max_digits=18, decimal_places=8, min_value=Decimal("0.00000001"))


class ReserveHealthResponseSerializer(serializers.Serializer):
    coverage_ratio = serializers.DecimalField(max_digits=28, decimal_places=8)
    is_healthy = serializers.BooleanField()
    pause_accrual = serializers.BooleanField()


class TreasurySnapshotCreateSerializer(serializers.Serializer):
    treasury_wallet_id = serializers.CharField(min_length=1)
    btc_usd_price = serializers.DecimalField(max_digits=18, decimal_places=8, min_value=Decimal("0.00000001"))
    allocated_usd_value = serializers.DecimalField(max_digits=18, decimal_places=8, min_value=0)
    coverage_ratio = serializers.DecimalField(max_digits=18, decimal_places=8, min_value=0)
    snapshot_source = serializers.CharField(min_length=1)

    def validate_treasury_wallet_id(self, value):
        if not TreasuryWallet.objects.filter(id=value).exists():
            raise serializers.ValidationError("Treasury wallet does not exist.")
        return value


class TreasurySnapshotSerializer(serializers.ModelSerializer):
    treasury_wallet_id = serializers.CharField()

    class Meta:
        model = TreasurySnapshot
        fields = (
            "id",
            "treasury_wallet_id",
            "btc_usd_price",
            "allocated_usd_value",
            "coverage_ratio",
            "snapshot_source",
        )
