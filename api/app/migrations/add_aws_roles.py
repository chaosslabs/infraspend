from sqlalchemy import text
from app.helpers.database import engine


def upgrade():
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS aws_external_id VARCHAR")
        )
        conn.execute(
            text(
                "ALTER TABLE aws_api_configurations ADD COLUMN IF NOT EXISTS role_arn VARCHAR"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE aws_api_configurations ADD COLUMN IF NOT EXISTS external_id VARCHAR"
            )
        )
