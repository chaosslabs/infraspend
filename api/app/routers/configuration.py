import logging
import os
import re
import uuid
from datetime import date, timedelta
from app.services.aws_service import role_client

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import (
    User,
    DatadogAPIConfiguration,
    AWSAPIConfiguration,
    HerokuAPIConfiguration,
)
from app.routers.models import APIConfigResponse
from app.helpers.database import get_db
from app.helpers.auth import get_authenticated_user
from app.services.configuration_service import ConfigurationService
from pydantic import BaseModel, Field, constr, condecimal, validator
from typing import Literal
from datetime import datetime
from hashlib import sha256
from app.models import AI_CONFIG_MODELS, VendorMetrics
from app.services.monthly_costs import add_month
from app.helpers.secrets_service import SecretsService

router = APIRouter(prefix="/v1/configuration", tags=["configuration"])

logger = logging.getLogger(__name__)


class DatadogConfig(BaseModel):
    app_key: str
    api_key: str
    identifier: str = "Default Configuration"


class AWSConfig(BaseModel):
    role_arn: constr(
        regex=r"^arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9_+=,.@/\-]+$", max_length=2048
    )
    identifier: str = "Default Configuration"


class HerokuConfig(BaseModel):
    api_key: str
    team_name_or_id: str | None = None
    identifier: str = "Default Configuration"


def get_user(
    auth_user: dict = Depends(get_authenticated_user), db: Session = Depends(get_db)
) -> User:
    user = db.query(User).filter(User.sub == auth_user["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/datadog")
async def configure_datadog(
    config: DatadogConfig,
    user: User = Depends(get_user),
    db: Session = Depends(get_db),
) -> APIConfigResponse:
    secrets_data = {
        "DATADOG_APP_KEY": config.app_key,
        "DATADOG_API_KEY": config.api_key,
    }

    try:
        config_service = ConfigurationService(db, user)
        config_id, message = config_service.configure_vendor(
            "datadog", secrets_data, config.identifier
        )

        return APIConfigResponse(id=config_id, type="datadog", message=message)
    except Exception as e:
        logger.error(f"Failed to configure Datadog: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to configure Datadog: {str(e)}"
        )


@router.post("/aws")
async def configure_aws(
    config: AWSConfig,
    user: User = Depends(get_user),
    db: Session = Depends(get_db),
) -> APIConfigResponse:
    if not user.aws_external_id:
        raise HTTPException(400, "Generate the AWS trust policy first")
    try:
        client = role_client(config.role_arn, user.aws_external_id, user.id)
        today = date.today()
        client.get_cost_and_usage(
            TimePeriod={
                "Start": (today - timedelta(days=2)).isoformat(),
                "End": today.isoformat(),
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
    except Exception:
        logger.warning("AWS role validation failed for user %s", user.id)
        raise HTTPException(
            400,
            "Unable to read AWS costs. Check the role trust policy, external ID, and Cost Explorer permissions.",
        )
    existing = (
        db.query(AWSAPIConfiguration)
        .filter(
            AWSAPIConfiguration.user_id == user.id,
            AWSAPIConfiguration.identifier == config.identifier,
        )
        .first()
    )
    if existing is None:
        existing = AWSAPIConfiguration(user_id=user.id, identifier=config.identifier)
        db.add(existing)
    existing.role_arn = config.role_arn
    existing.external_id = user.aws_external_id
    existing.aws_access_key_id = None
    existing.aws_secret_access_key = None
    try:
        db.commit()
        db.refresh(existing)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Unable to save AWS configuration")
    return APIConfigResponse(
        id=existing.id, type="aws", message="AWS role connected successfully"
    )


@router.post("/aws/setup")
async def aws_setup(user: User = Depends(get_user), db: Session = Depends(get_db)):
    principal = os.environ.get("AWS_INFRASPEND_ROLE_ARN")
    if not principal or not re.fullmatch(
        r"arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9_+=,.@/\-]+", principal
    ):
        raise HTTPException(503, "AWS integration is not configured by the operator")
    # Lock the tenant row so concurrent onboarding requests get the same ID.
    user = db.query(User).filter(User.id == user.id).with_for_update().one()
    if not user.aws_external_id:
        user.aws_external_id = str(uuid.uuid4())
        db.commit()
    return {
        "external_id": user.aws_external_id,
        "trust_policy": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": principal},
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {"sts:ExternalId": user.aws_external_id}
                    },
                }
            ],
        },
        "permissions_policy": {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": "ce:GetCostAndUsage", "Resource": "*"}
            ],
        },
    }


@router.post("/heroku")
async def configure_heroku(
    config: HerokuConfig,
    user: User = Depends(get_user),
    db: Session = Depends(get_db),
) -> APIConfigResponse:
    secrets_data = {
        "HEROKU_API_KEY": config.api_key,
        "HEROKU_TEAM_NAME_OR_ID": config.team_name_or_id,
    }

    config_service = ConfigurationService(db, user)
    try:
        config_id, message = config_service.configure_vendor(
            "heroku", secrets_data, config.identifier
        )

        return APIConfigResponse(id=config_id, type="heroku", message=message)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to configure Heroku: {str(e)}"
        )


@router.get("/list")
async def list_api_configurations(
    user: User = Depends(get_user), db: Session = Depends(get_db)
):
    datadog_configs = (
        db.query(DatadogAPIConfiguration)
        .filter(DatadogAPIConfiguration.user_id == user.id)
        .all()
    )

    aws_configs = (
        db.query(AWSAPIConfiguration)
        .filter(AWSAPIConfiguration.user_id == user.id)
        .all()
    )

    heroku_configs = (
        db.query(HerokuAPIConfiguration)
        .filter(HerokuAPIConfiguration.user_id == user.id)
        .all()
    )

    configurations = []
    for config in datadog_configs:
        configurations.append(
            {
                "id": config.id,
                "type": "datadog",
                "identifier": config.identifier,
                "created_at": config.created_at,
                "updated_at": config.updated_at,
            }
        )
    for config in aws_configs:
        configurations.append(
            {
                "id": config.id,
                "type": "aws",
                "identifier": config.identifier,
                "created_at": config.created_at,
                "updated_at": config.updated_at,
            }
        )
    for config in heroku_configs:
        configurations.append(
            {
                "id": config.id,
                "type": "heroku",
                "identifier": config.identifier,
                "created_at": config.created_at,
                "updated_at": config.updated_at,
            }
        )

    for vendor, model in AI_CONFIG_MODELS.items():
        for config in db.query(model).filter(model.user_id == user.id).all():
            configurations.append(
                {
                    "id": config.id,
                    "type": vendor,
                    "identifier": config.identifier,
                    "created_at": config.created_at,
                    "updated_at": config.updated_at,
                }
            )
    return {"data": configurations}


class AIConfig(BaseModel):
    api_key: constr(strip_whitespace=True, min_length=1)
    identifier: constr(strip_whitespace=True, min_length=1, max_length=200) = (
        "Default Configuration"
    )


class SubscriptionCharge(BaseModel):
    identifier: constr(strip_whitespace=True, min_length=1, max_length=200) = (
        "Default Configuration"
    )
    month: str = Field(..., regex=r"^(0[1-9]|1[0-2])-\d{4}$")
    cost: condecimal(ge=0, max_digits=12, decimal_places=2)
    currency: Literal["USD"] = "USD"

    @validator("month")
    def validate_month(cls, value: str) -> str:
        parsed = datetime.strptime(value, "%m-%Y")
        if parsed.date() > datetime.utcnow().date().replace(day=1):
            raise ValueError("Enter a charge for the current or a past month")
        return value


@router.post("/ai/{vendor}")
async def configure_ai(
    vendor: Literal["openai", "anthropic"],
    config: AIConfig,
    user: User = Depends(get_user),
    db: Session = Depends(get_db),
) -> APIConfigResponse:
    model = AI_CONFIG_MODELS[vendor]
    try:
        # Stable, distinct secret names for each user, vendor and account.
        scope = sha256(f"{user.sub}:{vendor}:{config.identifier}".encode()).hexdigest()
        secret_id = SecretsService().create_customer_secret(
            f"ai_{scope}", config.api_key, vendor
        )
        existing = (
            db.query(model)
            .filter(model.user_id == user.id, model.identifier == config.identifier)
            .first()
        )
        if existing is None:
            existing = model(user_id=user.id, identifier=config.identifier, type=vendor)
            db.add(existing)
        existing.api_key = secret_id
        db.commit()
        return APIConfigResponse(
            id=existing.id, type=vendor, message="API billing credentials saved"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Unable to save API billing credentials"
        ) from None


@router.post("/subscriptions/{vendor}")
async def save_subscription_charge(
    vendor: Literal["claude", "chatgpt"],
    charge: SubscriptionCharge,
    user: User = Depends(get_user),
    db: Session = Depends(get_db),
) -> APIConfigResponse:
    model = AI_CONFIG_MODELS[vendor]
    try:
        config = (
            db.query(model)
            .filter(model.user_id == user.id, model.identifier == charge.identifier)
            .first()
        )
        if config is None:
            config = model(user_id=user.id, identifier=charge.identifier, type=vendor)
            db.add(config)
        config.updated_at = datetime.utcnow()
        metric = (
            db.query(VendorMetrics)
            .filter(
                VendorMetrics.user_id == user.id,
                VendorMetrics.vendor == vendor,
                VendorMetrics.identifier == charge.identifier,
                VendorMetrics.month == charge.month,
            )
            .first()
        )
        if metric is None:
            metric = VendorMetrics(
                user_id=user.id,
                vendor=vendor,
                identifier=charge.identifier,
                month=charge.month,
            )
            db.add(metric)
        month = datetime.strptime(charge.month, "%m-%Y").date()
        metric.cost = float(charge.cost)
        metric.source_provider = vendor
        metric.source_period_start = month
        metric.source_period_end = add_month(month)
        metric.provider_currency = charge.currency
        metric.updated_at = datetime.utcnow()
        db.commit()
        return APIConfigResponse(
            id=config.id, type=vendor, message="Monthly subscription charge saved"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Unable to save subscription charge"
        ) from None
