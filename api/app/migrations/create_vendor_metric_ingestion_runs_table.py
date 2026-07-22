import logging
from sqlalchemy import text
from app.helpers.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    logger.info("Starting migration: Creating vendor metric ingestion runs table")

    try:
        with engine.begin() as conn:
            logger.info("Creating vendor_metric_ingestion_runs table...")
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS vendor_metric_ingestion_runs (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        vendor VARCHAR NOT NULL,
                        identifier VARCHAR NOT NULL,
                        started_at TIMESTAMP WITH TIME ZONE NOT NULL
                            DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP WITH TIME ZONE NULL,
                        requested_period_start DATE NULL,
                        requested_period_end DATE NULL,
                        source_period_start DATE NULL,
                        source_period_end DATE NULL,
                        status VARCHAR NOT NULL DEFAULT 'running',
                        records_received INTEGER NOT NULL DEFAULT 0,
                        records_stored INTEGER NOT NULL DEFAULT 0,
                        error_category VARCHAR NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT ck_vendor_metric_ingestion_runs_status
                            CHECK (status IN (
                                'running', 'success', 'partial', 'failed'
                            )),
                        CONSTRAINT ck_vendor_metric_ingestion_runs_error_category
                            CHECK (
                                error_category IS NULL OR error_category IN (
                                    'provider_error',
                                    'row_validation',
                                    'storage_error',
                                    'configuration_error',
                                    'incomplete_source'
                                )
                            )
                    )
                    """
                )
            )

            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_vendor_metric_ingestion_runs_user_id
                    ON vendor_metric_ingestion_runs(user_id);
                    CREATE INDEX IF NOT EXISTS idx_vendor_metric_ingestion_runs_vendor
                    ON vendor_metric_ingestion_runs(vendor);
                    CREATE INDEX IF NOT EXISTS idx_vendor_metric_ingestion_runs_scope_started
                    ON vendor_metric_ingestion_runs(
                        user_id, vendor, identifier, started_at
                    );
                    """
                )
            )

            logger.info("Vendor metric ingestion runs table created successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise


def downgrade():
    logger.info("Starting downgrade: Dropping vendor metric ingestion runs table")
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS vendor_metric_ingestion_runs"))
            logger.info("Vendor metric ingestion runs table dropped successfully")
    except Exception as e:
        logger.error(f"Downgrade failed: {str(e)}")
        raise


if __name__ == "__main__":
    upgrade()
