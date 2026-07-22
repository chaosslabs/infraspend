import logging
from sqlalchemy import text
from app.helpers.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    logger.info("Starting migration: Adding lineage columns to vendor metrics")
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    ALTER TABLE vendor_metrics
                    ADD COLUMN IF NOT EXISTS source_provider VARCHAR;
                    ALTER TABLE vendor_metrics
                    ADD COLUMN IF NOT EXISTS source_period_start DATE;
                    ALTER TABLE vendor_metrics
                    ADD COLUMN IF NOT EXISTS source_period_end DATE;
                    ALTER TABLE vendor_metrics
                    ADD COLUMN IF NOT EXISTS provider_currency VARCHAR;
                    """
                )
            )
            logger.info("Added vendor metrics lineage columns successfully")
    except Exception:
        logger.exception("Migration failed")
        raise


def downgrade():
    logger.info("Starting downgrade: Removing lineage columns from vendor metrics")
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    ALTER TABLE vendor_metrics
                    DROP COLUMN IF EXISTS provider_currency;
                    ALTER TABLE vendor_metrics
                    DROP COLUMN IF EXISTS source_period_end;
                    ALTER TABLE vendor_metrics
                    DROP COLUMN IF EXISTS source_period_start;
                    ALTER TABLE vendor_metrics
                    DROP COLUMN IF EXISTS source_provider;
                    """
                )
            )
            logger.info("Removed vendor metrics lineage columns successfully")
    except Exception:
        logger.exception("Downgrade failed")
        raise


if __name__ == "__main__":
    upgrade()
