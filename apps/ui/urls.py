from __future__ import annotations

from django.urls import path

from apps.ui import views

urlpatterns = [
    path("", views.home, name="home"),
    path("summary", views.home_summary, name="home-summary"),
    path("demo", views.demo_dashboard, name="demo-dashboard"),
    path("demo/action", views.demo_action, name="demo-action"),
    path(
        "demo/actions/alice-buys",
        views.demo_action,
        {"action": "alice_purchase"},
        name="demo-action-alice-buys",
    ),
    path(
        "demo/actions/reset",
        views.demo_action,
        {"action": "reset"},
        name="demo-action-reset",
    ),
    path(
        "demo/actions/simulate-payment",
        views.demo_action,
        {"action": "simulate_payment"},
        name="demo-action-simulate-payment",
    ),
    path(
        "demo/actions/authorize-payout",
        views.demo_action,
        {"action": "authorize_payout"},
        name="demo-action-authorize-payout",
    ),
    path(
        "demo/actions/set-price",
        views.demo_action,
        {"action": "set_price"},
        name="demo-action-set-price",
    ),
    path(
        "demo/actions/advance-price",
        views.demo_action,
        {"action": "advance_price"},
        name="demo-action-advance-price",
    ),
    path(
        "demo/actions/current-live-price",
        views.demo_action,
        {"action": "current_live_price"},
        name="demo-action-current-live-price",
    ),
    path(
        "demo/actions/sync-live-price",
        views.demo_action,
        {"action": "sync_live_price"},
        name="demo-action-sync-live-price",
    ),
    path(
        "demo/actions/demo-upside",
        views.demo_action,
        {"action": "demo_upside"},
        name="demo-action-demo-upside",
    ),
    path(
        "demo/actions/reset-alice",
        views.demo_action,
        {"action": "reset_alice"},
        name="demo-action-reset-alice",
    ),
    path(
        "demo/actions/select-receipt",
        views.demo_action,
        {"action": "select_receipt"},
        name="demo-action-select-receipt",
    ),
    path("demo/receipt/<str:receipt_id>", views.demo_receipt_page, name="demo-receipt"),
    path("merchants", views.merchants_page, name="merchants"),
    path("merchants/<str:merchant_id>", views.merchant_detail, name="merchant-detail"),
    path(
        "merchants/<str:merchant_id>/policies",
        views.merchant_policies,
        name="merchant-policies",
    ),
    path(
        "merchants/<str:merchant_id>/transactions",
        views.merchant_transactions,
        name="merchant-transactions",
    ),
    path(
        "merchants/<str:merchant_id>/treasury",
        views.merchant_treasury,
        name="merchant-treasury",
    ),
    path("receipts/<str:receipt_id>", views.receipt_page, name="receipt-page"),
    path("admin/demo", views.admin_demo, name="admin-demo"),
]
