"""Preserve existing vendor-wide budgets; new account plans opt in to scope."""

from sqlalchemy import inspect, text
from app.helpers.database import engine


def upgrade():
    with engine.begin() as connection:
        columns = {
            column["name"] for column in inspect(connection).get_columns("budget_plans")
        }
        if "identifier" not in columns:
            connection.execute(
                text("ALTER TABLE budget_plans ADD COLUMN identifier VARCHAR")
            )
