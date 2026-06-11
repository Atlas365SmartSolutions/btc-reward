from __future__ import annotations

from uuid import uuid4

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.merchants.api.serializers import (
    MerchantCreateSerializer,
    MerchantReserveHealthSerializer,
    MerchantSerializer,
)
from apps.merchants.models import Merchant
from apps.treasury.services.reserve_health import get_merchant_reserve_health


class MerchantCreateView(APIView):
    def post(self, request):
        serializer = MerchantCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        merchant = Merchant.objects.create(id=uuid4().hex, **serializer.validated_data)
        return Response(
            {"ok": True, "merchant": MerchantSerializer(merchant).data},
            status=status.HTTP_201_CREATED,
        )


class MerchantReserveHealthView(APIView):
    def get(self, request, merchant_id: str):
        result = get_merchant_reserve_health(merchant_id=merchant_id)
        payload = {"merchant_id": merchant_id, **result.__dict__}
        return Response(MerchantReserveHealthSerializer(payload).data)
