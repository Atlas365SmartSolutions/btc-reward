from __future__ import annotations

from uuid import uuid4

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.adapters.providers import get_btc_price_oracle
from apps.rewards.api.serializers import (
    RewardCalculationRequestSerializer,
    RewardCalculationResponseSerializer,
    RewardPolicyCreateSerializer,
    RewardPolicySerializer,
)
from apps.rewards.domain.reward import RewardInput, calculate_reward
from apps.rewards.models import PolicyStatus, RewardPolicy


class RewardCalculationView(APIView):
    def post(self, request):
        serializer = RewardCalculationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        result = calculate_reward(
            RewardInput(
                btc_spent_sats=payload["btc_spent_sats"],
                merchant_retention_bps=payload["merchant_retention_bps"],
                customer_share_bps=payload["customer_share_bps"],
                current_btc_usd_price=get_btc_price_oracle().get_current_price_usd(),
                btc_usd_price_at_purchase=payload["btc_usd_price_at_purchase"],
                high_water_mark_value_usd=payload["high_water_mark_value_usd"],
            )
        )
        return Response(RewardCalculationResponseSerializer(result.__dict__).data)


class RewardPolicyCreateView(APIView):
    def post(self, request):
        serializer = RewardPolicyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            policy = RewardPolicy.objects.create(
                id=uuid4().hex,
                merchant_id=serializer.validated_data["merchant_id"],
                merchant_retention_bps=serializer.validated_data["merchant_retention_bps"],
                customer_share_bps=serializer.validated_data["customer_share_bps"],
                min_coverage_ratio=serializer.validated_data["min_coverage_ratio"],
                status=PolicyStatus.DRAFT,
            )
        except IntegrityError:
            return Response(
                {"detail": "Reward policy could not be created."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"ok": True, "policy": RewardPolicySerializer(policy).data},
            status=status.HTTP_201_CREATED,
        )
