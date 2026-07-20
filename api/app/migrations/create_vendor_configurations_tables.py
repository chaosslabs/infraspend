import logging
from sqlalchemy import text
from app.helpers.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    logger.info("Starting migration: Creating vendor configuration tables")

    try:
        with engine.begin() as conn:
            # Drop the old table
            logger.info("Dropping old api_configurations table...")
            conn.execute(text("DROP TABLE IF EXISTS api_configurations"))

            # Create datadog configurations table
            logger.info("Creating datadog_api_configurations table...")
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS datadog_api_configurations (
                    id SERIAL PRIMARY KEY,
                    type VARCHAR,
                    user_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    app_key VARCHAR,
                    api_key VARCHAR
                )
            """
                )
            )

            # Create AWS configurations table
            logger.info("Creating aws_api_configurations table...")
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS aws_api_configurations (
                    id SERIAL PRIMARY KEY,
                    type VARCHAR,
                    user_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    aws_access_key_id VARCHAR,
                    aws_secret_access_key VARCHAR
                )
            """
                )
            )

            # Create Heroku configurations table
            logger.info("Creating heroku_api_configurations table...")
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS heroku_api_configurations (
                    id SERIAL PRIMARY KEY,
                    type VARCHAR,
                    user_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    api_key VARCHAR,
                    team_name_or_id VARCHAR
                )
            """
                )
            )

            logger.info("Vendor configuration tables created successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


def downgrade():
    logger.info("Starting downgrade: Reverting to original api_configurations table")

    try:
        with engine.begin() as conn:
            # Drop the new tables
            logger.info("Dropping vendor-specific configuration tables...")
            conn.execute(text("DROP TABLE IF EXISTS datadog_api_configurations"))
            conn.execute(text("DROP TABLE IF EXISTS aws_api_configurations"))
            conn.execute(text("DROP TABLE IF EXISTS heroku_api_configurations"))

            # Recreate original table
            logger.info("Recreating original api_configurations table...")
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS api_configurations (
                    id SERIAL PRIMARY KEY,
                    type VARCHAR,
                    user_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )

            logger.info("Downgrade completed successfully")
    except Exception as e:
        logger.error(f"Downgrade failed: {e}")
        raise


if __name__ == "__main__":
    upgrade()
