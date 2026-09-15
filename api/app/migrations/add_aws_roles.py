"""Add role fields while preserving existing key-based AWS configurations."""

from sqlalchemy import inspect, text
from app.helpers.database import engine


def upgrade():
    with engine.begin() as conn:
        for table, additions in (
            ("users", ("aws_external_id",)),
            ("aws_api_configurations", ("role_arn", "external_id")),
        ):
            columns = {column["name"] for column in inspect(conn).get_columns(table)}
            for column in additions:
                if column not in columns:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {column} VARCHAR")
                    )
