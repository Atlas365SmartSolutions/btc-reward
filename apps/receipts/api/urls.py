from __future__ import annotations

from django.urls import path

from apps.receipts.api.views import ReceiptDetailView

urlpatterns = [
    path("<str:receipt_id>", ReceiptDetailView.as_view(), name="receipt-detail"),
]
