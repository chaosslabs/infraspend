from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Date
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import sqlalchemy

Base = declarative_base()

INGESTION_RUN_RUNNING_STATUS = "running"
INGESTION_RUN_TERMINAL_STATUSES = ("success", "partial", "failed")
INGESTION_RUN_STATUSES = (
    INGESTION_RUN_RUNNING_STATUS,
    *INGESTION_RUN_TERMINAL_STATUSES,
)
INGESTION_RUN_ERROR_CATEGORIES = (
    "provider_error",
    "row_validation",
    "storage_error",
    "configuration_error",
    "incomplete_source",
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    sub = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    datadog_configurations = relationship(
        "DatadogAPIConfiguration", back_populates="user"
    )
    aws_configurations = relationship("AWSAPIConfiguration", back_populates="user")
    heroku_configurations = relationship(
        "HerokuAPIConfiguration", back_populates="user"
    )
    budget_plans = relationship("BudgetPlan", back_populates="user")
    metric_ingestion_runs = relationship(
        "VendorMetricIngestionRun", back_populates="user"
    )


class APIConfiguration(Base):
    __abstract__ = True

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    identifier = Column(String, default="Default Configuration")

    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey("users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DatadogAPIConfiguration(APIConfiguration):
    __tablename__ = "datadog_api_configurations"

    app_key = Column(String)
    api_key = Column(String)
    user = relationship("User", back_populates="datadog_configurations")
    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "user_id", "identifier", name="uq_datadog_user_identifier"
        ),
    )


class AWSAPIConfiguration(APIConfiguration):
    __tablename__ = "aws_api_configurations"

    aws_access_key_id = Column(String)
    aws_secret_access_key = Column(String)
    user = relationship("User", back_populates="aws_configurations")
    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "user_id", "identifier", name="uq_aws_user_identifier"
        ),
    )


class HerokuAPIConfiguration(APIConfiguration):
    __tablename__ = "heroku_api_configurations"

    api_key = Column(String)
    team_name_or_id = Column(String, nullable=True)
    user = relationship("User", back_populates="heroku_configurations")
    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "user_id", "identifier", name="uq_heroku_user_identifier"
        ),
    )


class BudgetPlan(Base):
    __tablename__ = "budget_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    vendor = Column(String)  # "datadog", "aws", or "heroku"
    type = Column(String, default="default")  # For future use with different plan types
    budgets = Column(JSON)  # Store monthly budgets as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to User model
    user = relationship("User", back_populates="budget_plans")


class VendorMetrics(Base):
    __tablename__ = "vendor_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    vendor = Column(String)  # "datadog", "aws", or "heroku"
    identifier = Column(String)  # Configuration identifier
    month = Column(String)  # Format: MM-YYYY
    cost = Column(sqlalchemy.Float)
    source_provider = Column(String, nullable=True)
    source_period_start = Column(Date, nullable=True)
    source_period_end = Column(Date, nullable=True)
    provider_currency = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to User model
    user = relationship("User", backref="vendor_metrics")

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "user_id",
            "vendor",
            "identifier",
            "month",
            name="uq_vendor_metrics_user_vendor_identifier_month",
        ),
    )


class VendorMetricIngestionRun(Base):
    __tablename__ = "vendor_metric_ingestion_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    vendor = Column(String, nullable=False, index=True)
    identifier = Column(String, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    requested_period_start = Column(Date, nullable=True)
    requested_period_end = Column(Date, nullable=True)
    source_period_start = Column(Date, nullable=True)
    source_period_end = Column(Date, nullable=True)
    status = Column(
        String, default=INGESTION_RUN_RUNNING_STATUS, nullable=False, index=True
    )
    records_received = Column(Integer, default=0, nullable=False)
    records_stored = Column(Integer, default=0, nullable=False)
    error_category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="metric_ingestion_runs")

    __table_args__ = (
        sqlalchemy.CheckConstraint(
            "status IN ('running', 'success', 'partial', 'failed')",
            name="ck_vendor_metric_ingestion_runs_status",
        ),
        sqlalchemy.CheckConstraint(
            "error_category IS NULL OR error_category IN "
            "('provider_error', 'row_validation', 'storage_error', "
            "'configuration_error', 'incomplete_source')",
            name="ck_vendor_metric_ingestion_runs_error_category",
        ),
        sqlalchemy.Index(
            "idx_vendor_metric_ingestion_runs_scope_started",
            "user_id",
            "vendor",
            "identifier",
            "started_at",
        ),
    )

    def complete(
        self,
        *,
        status: str,
        completed_at: datetime,
        records_received: int = 0,
        records_stored: int = 0,
        source_period_start=None,
        source_period_end=None,
        error_category: str | None = None,
    ):
        if self.status != INGESTION_RUN_RUNNING_STATUS:
            raise ValueError("Only running ingestion runs can be completed")
        if status not in INGESTION_RUN_TERMINAL_STATUSES:
            raise ValueError(f"Invalid terminal ingestion status: {status}")
        if error_category and error_category not in INGESTION_RUN_ERROR_CATEGORIES:
            raise ValueError(f"Invalid ingestion error category: {error_category}")
        if records_received < 0 or records_stored < 0:
            raise ValueError("Ingestion record counts cannot be negative")

        self.status = status
        self.completed_at = completed_at
        self.records_received = records_received
        self.records_stored = records_stored
        self.source_period_start = source_period_start
        self.source_period_end = source_period_end
        self.error_category = error_category
        self.updated_at = completed_at
