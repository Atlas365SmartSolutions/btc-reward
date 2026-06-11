from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.receipts.api.serializers import ReceiptSerializer
from apps.receipts.models import RewardReceipt


class ReceiptDetailView(APIView):
    def get(self, request, receipt_id: str):
        receipt = get_object_or_404(
            RewardReceipt.objects.select_related("transaction", "customer", "merchant").prefetch_related(
                "calculations"
            ),
            id=receipt_id,
        )
        return Response(ReceiptSerializer(receipt).data)
