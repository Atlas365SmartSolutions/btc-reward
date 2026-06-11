from __future__ import annotations

from django.urls import path

from apps.rewards.api.views import RewardPolicyCreateView

urlpatterns = [
    path("", RewardPolicyCreateView.as_view(), name="reward-policy-create"),
]
