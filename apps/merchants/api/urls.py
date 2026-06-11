from __future__ import annotations

from django.urls import path

from apps.merchants.api.views import MerchantCreateView, MerchantReserveHealthView

urlpatterns = [
    path("", MerchantCreateView.as_view(), name="merchant-create"),
    path(
        "<str:merchant_id>/reserve-health",
        MerchantReserveHealthView.as_view(),
        name="merchant-reserve-health",
    ),
]
