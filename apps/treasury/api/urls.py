from __future__ import annotations

from django.urls import path

from apps.treasury.api.views import ReserveHealthView, TreasurySnapshotCreateView

urlpatterns = [
    path("reserve-health", ReserveHealthView.as_view(), name="reserve-health"),
    path(
        "snapshots",
        TreasurySnapshotCreateView.as_view(),
        name="treasury-snapshot-create",
    ),
]
