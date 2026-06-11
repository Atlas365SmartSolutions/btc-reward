from __future__ import annotations

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command


@pytest.mark.django_db
def test_ensure_admins_creates_superusers_and_email_login() -> None:
    call_command(
        "ensure_admins",
        "--admin",
        "akeem:akeem@canurta.com",
        "--admin",
        "gurkamal:gurkamal@canurta.com",
        password="example-password-123",
    )

    user_model = get_user_model()
    akeem = user_model.objects.get(username="akeem")
    gurkamal = user_model.objects.get(username="gurkamal")

    assert akeem.email == "akeem@canurta.com"
    assert gurkamal.email == "gurkamal@canurta.com"
    assert akeem.is_staff and akeem.is_superuser
    assert gurkamal.is_staff and gurkamal.is_superuser
    assert authenticate(username="akeem@canurta.com", password="example-password-123") == akeem
    assert authenticate(username="gurkamal", password="example-password-123") == gurkamal


@pytest.mark.django_db
def test_ensure_admins_removes_old_local_admin(django_user_model) -> None:
    django_user_model.objects.create_superuser(username="localadmin", email="local@example.com", password="old")

    call_command(
        "ensure_admins",
        "--admin",
        "akeem:akeem@canurta.com",
        "--remove-username",
        "localadmin",
        password="example-password-123",
    )

    assert not django_user_model.objects.filter(username="localadmin").exists()


@pytest.mark.django_db
def test_admin_dashboard_renders_operational_metrics(client, django_user_model, seeded_core_entities) -> None:
    superuser = django_user_model.objects.create_superuser(
        username="ops",
        email="ops@example.com",
        password="example-password-123",
    )
    client.force_login(superuser)

    response = client.get("/admin/")

    assert response.status_code == 200
    body = response.content.decode()
    assert "Operations Dashboard" in body
    assert "Reserve Health" in body
    assert "Recent Transactions" in body
