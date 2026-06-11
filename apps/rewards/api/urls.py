from __future__ import annotations

from django.urls import path

from apps.rewards.api.views import RewardCalculationView

urlpatterns = [
    path("calculate", RewardCalculationView.as_view(), name="reward-calculate"),
]
