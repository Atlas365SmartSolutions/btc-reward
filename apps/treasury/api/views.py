from __future__ import annotations

from uuid import uuid4

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.treasury.api.serializers import (
    ReserveHealthRequestSerializer,
    ReserveHealthResponseSerializer,
    TreasurySnapshotCreateSerializer,
    TreasurySnapshotSerializer,
)
from apps.treasury.domain.treasury import calculate_reserve_health
from apps.treasury.models import TreasurySnapshot


class ReserveHealthView(APIView):
    def post(self, request):
        serializer = ReserveHealthRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = calculate_reserve_health(**serializer.validated_data)
        return Response(ReserveHealthResponseSerializer(result.__dict__).data)


class TreasurySnapshotCreateView(APIView):
    def post(self, request):
        serializer = TreasurySnapshotCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            snapshot = TreasurySnapshot.objects.create(id=uuid4().hex, **serializer.validated_data)
        except IntegrityError:
            return Response(
                {"detail": "Treasury snapshot could not be created."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"ok": True, "snapshot": TreasurySnapshotSerializer(snapshot).data},
            status=status.HTTP_201_CREATED,
        )
