import logging
from sqlalchemy import text
from app.helpers.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    logger.info("Starting migration: Adding identifier field to API configurations")

    try:
        with engine.begin() as conn:
            # Add identifier column to datadog configurations
            logger.info("Adding identifier column to datadog_api_configurations...")
            conn.execute(
                text(
                    """
                    ALTER TABLE datadog_api_configurations
                    ADD COLUMN IF NOT EXISTS identifier VARCHAR DEFAULT 'Default Configuration';
                    """
                )
            )

            # Add identifier column to aws configurations
            logger.info("Adding identifier column to aws_api_configurations...")
            conn.execute(
                text(
                    """
                    ALTER TABLE aws_api_configurations
                    ADD COLUMN IF NOT EXISTS identifier VARCHAR DEFAULT 'Default Configuration';
                    """
                )
            )

            # Add identifier column to heroku configurations
            logger.info("Adding identifier column to heroku_api_configurations...")
            conn.execute(
                text(
                    """
                    ALTER TABLE heroku_api_configurations
                    ADD COLUMN IF NOT EXISTS identifier VARCHAR DEFAULT 'Default Configuration';
                    """
                )
            )

            # Remove old unique constraints
            logger.info("Removing old unique constraints...")
            conn.execute(
                text(
                    """
                    ALTER TABLE datadog_api_configurations
                    DROP CONSTRAINT IF EXISTS uq_datadog_user;
                    """
                )
            )

            conn.execute(
                text(
                    """
                    ALTER TABLE aws_api_configurations
                    DROP CONSTRAINT IF EXISTS uq_aws_user;
                    """
                )
            )

            conn.execute(
                text(
                    """
                    ALTER TABLE heroku_api_configurations
                    DROP CONSTRAINT IF EXISTS uq_heroku_user;
                    """
                )
            )

            # Add new unique constraints only if they don't exist
            logger.info("Adding new unique constraints for user_id + identifier...")
            conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint
                            WHERE conname = 'uq_datadog_user_identifier'
                        ) THEN
                            ALTER TABLE datadog_api_configurations
                            ADD CONSTRAINT uq_datadog_user_identifier
                            UNIQUE (user_id, identifier);
                        END IF;
                    END $$;
                    """
                )
            )

            conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint
                            WHERE conname = 'uq_aws_user_identifier'
                        ) THEN
                            ALTER TABLE aws_api_configurations
                            ADD CONSTRAINT uq_aws_user_identifier
                            UNIQUE (user_id, identifier);
                        END IF;
                    END $$;
                    """
                )
            )

            conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint
                            WHERE conname = 'uq_heroku_user_identifier'
                        ) THEN
                            ALTER TABLE heroku_api_configurations
                            ADD CONSTRAINT uq_heroku_user_identifier
                            UNIQUE (user_id, identifier);
                        END IF;
                    END $$;
                    """
                )
            )

            logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    upgrade()
