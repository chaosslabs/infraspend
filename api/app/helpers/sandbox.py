"""Disposable preview data. Authentication is still handled by Auth0."""

import os
import secrets
from datetime import date

session_secret = secrets.token_urlsafe(48)


def sandbox_enabled():
    return os.getenv("PREVIEW_SANDBOX") == "true"


def seed_user(db, user_id):
    from app.models import (
        AWSAPIConfiguration,
        DatadogAPIConfiguration,
        HerokuAPIConfiguration,
        VendorMetrics,
        BudgetPlan,
    )

    today = date.today()
    for vendor, model, cost in (
        ("aws", AWSAPIConfiguration, 1250),
        ("datadog", DatadogAPIConfiguration, 420),
        ("heroku", HerokuAPIConfiguration, 180),
    ):
        db.add(model(user_id=user_id, identifier="Default Configuration", type=vendor))
        budgets = []
        for offset in range(12):
            month_index = today.year * 12 + today.month - 1 - offset
            year, month = divmod(month_index, 12)
            label = f"{month + 1:02d}-{year}"
            budgets.append({"month": label, "amount": cost * 1.2})
            db.add(
                VendorMetrics(
                    user_id=user_id,
                    vendor=vendor,
                    identifier="Default Configuration",
                    month=label,
                    cost=round(cost * (1 - offset * 0.025), 2),
                    source_provider="sandbox",
                    provider_currency="USD",
                )
            )
        db.add(BudgetPlan(user_id=user_id, vendor=vendor, budgets={"budgets": budgets}))
    db.commit()
