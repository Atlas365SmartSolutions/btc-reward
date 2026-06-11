from __future__ import annotations

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.adapters.providers import get_btc_price_oracle, get_payment_processor
from apps.transactions.api.serializers import (
    RewardCalculationSummarySerializer,
    TransactionCreateSerializer,
)
from apps.transactions.services.ingestion import (
    IdempotencyConflict,
    IdempotencyInProgress,
    IngestTransactionInput,
    ingest_transaction,
)


class TransactionCreateView(APIView):
    def post(self, request):
        serializer = TransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            result = ingest_transaction(
                IngestTransactionInput(
                    merchant_id=payload["merchant_id"],
                    customer_id=payload["customer_id"],
                    reward_policy_id=payload.get("reward_policy_id"),
                    sats_spent=payload["sats_spent"],
                    btc_usd_price_at_purchase=payload["btc_usd_price_at_purchase"],
                    idempotency_key=request.headers.get("Idempotency-Key"),
                ),
                payment_processor=get_payment_processor(),
                price_oracle=get_btc_price_oracle(),
            )
        except IdempotencyConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except IdempotencyInProgress as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except IntegrityError:
            return Response(
                {"detail": "Transaction could not be created."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "ok": True,
                "transaction_id": result.transaction_id,
                "payment": {"external_id": result.payment_external_id},
                "reward_receipt_id": result.reward_receipt_id,
                "reward_calculation": RewardCalculationSummarySerializer(result.reward_calculation).data,
                "idempotent_replay": result.idempotent_replay,
            }
        )
