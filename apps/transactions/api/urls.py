from __future__ import annotations

from django.urls import path

from apps.transactions.api.views import TransactionCreateView

urlpatterns = [
    path("", TransactionCreateView.as_view(), name="transaction-create"),
]
