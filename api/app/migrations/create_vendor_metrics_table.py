import logging
from sqlalchemy import text
from app.helpers.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    logger.info("Starting migration: Creating vendor metrics table")

    try:
        with engine.begin() as conn:
            logger.info("Creating vendor_metrics table...")
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS vendor_metrics (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        vendor VARCHAR NOT NULL,
                        identifier VARCHAR NOT NULL,
                        month VARCHAR NOT NULL,
                        cost FLOAT NOT NULL,
                        source_provider VARCHAR NULL,
                        source_period_start DATE NULL,
                        source_period_end DATE NULL,
                        provider_currency VARCHAR NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_vendor_metrics_user_vendor_identifier_month
                            UNIQUE (user_id, vendor, identifier, month)
                    )
                    """
                )
            )

            # Create indexes
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_vendor_metrics_user_id
                    ON vendor_metrics(user_id);
                    CREATE INDEX IF NOT EXISTS idx_vendor_metrics_vendor
                    ON vendor_metrics(vendor);
                    CREATE INDEX IF NOT EXISTS idx_vendor_metrics_month
                    ON vendor_metrics(month);
                    """
                )
            )

            logger.info("Vendor metrics table created successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise


def downgrade():
    logger.info("Starting downgrade: Dropping vendor metrics table")
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS vendor_metrics"))
            logger.info("Vendor metrics table dropped successfully")
    except Exception as e:
        logger.error(f"Downgrade failed: {str(e)}")
        raise


if __name__ == "__main__":
    upgrade()
