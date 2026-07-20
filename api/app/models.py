from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import sqlalchemy

Base = declarative_base()


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
