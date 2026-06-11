from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.merchants.models import Customer, Merchant
from apps.rewards.models import RewardPolicy


@pytest.fixture()
def staff_user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="staff",
        password="test-password",
        is_staff=True,
    )


@pytest.fixture()
def client(staff_user) -> APIClient:
    api_client = APIClient()
    api_client.force_authenticate(user=staff_user)
    api_client.force_login(staff_user)
    return api_client


@pytest.fixture()
def anonymous_client() -> APIClient:
    return APIClient()


@pytest.fixture()
def seeded_core_entities(db) -> dict[str, str]:
    merchant = Merchant.objects.create(id="m_1", name="Merchant One")
    customer = Customer.objects.create(id="c_1", merchant=merchant, email="alice@example.com")
    policy = RewardPolicy.objects.create(
        id="rp_1",
        merchant=merchant,
        merchant_retention_bps=5000,
        customer_share_bps=2000,
        min_coverage_ratio=Decimal("1.1000"),
    )
    return {
        "merchant_id": merchant.id,
        "customer_id": customer.id,
        "reward_policy_id": policy.id,
    }
