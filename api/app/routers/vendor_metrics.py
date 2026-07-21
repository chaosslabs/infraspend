import logging
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.models import (
    AWSAPIConfiguration,
    DatadogAPIConfiguration,
    HerokuAPIConfiguration,
    User,
)
from app.helpers.database import get_db
from app.helpers.auth import get_authenticated_user
from app.services.vendor_metrics_service import (
    VendorConfigurationNotFound,
    VendorMetricsService,
)
from app.helpers.secrets_service import SecretsService

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/vendors-metrics", tags=["vendors"])

VENDOR_CONFIG_MODELS = {
    "aws": AWSAPIConfiguration,
    "datadog": DatadogAPIConfiguration,
    "heroku": HerokuAPIConfiguration,
}


def get_secrets_service() -> SecretsService:
    return SecretsService()


async def verify_api_key(
    api_key: str = Security(api_key_header),
    secrets_service: SecretsService = Depends(get_secrets_service),
):
    stored_api_key = secrets_service.get_secret("INTERNAL_API_KEY")
    if not stored_api_key:
        raise HTTPException(
            status_code=500,
            detail={"message": "API key not configured", "code": "API_KEY_ERROR"},
        )
    if api_key != stored_api_key:
        raise HTTPException(
            status_code=403,
            detail={"message": "Invalid API key", "code": "INVALID_API_KEY"},
        )
    return api_key


def get_user(
    auth_user: dict = Depends(get_authenticated_user), db: Session = Depends(get_db)
) -> User:
    user = db.query(User).filter(User.sub == auth_user["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{vendor}")
async def get_vendor_metrics(
    vendor: str,
    identifier: str = "Default Configuration",
    user: User = Depends(get_user),
    db: Session = Depends(get_db),
):
    try:
        vendor_name = vendor.lower()
        config_model = VENDOR_CONFIG_MODELS.get(vendor_name)
        if not config_model:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid vendor",
                    "message": f"Vendor type '{vendor}' not implemented",
                    "code": "INVALID_VENDOR",
                },
            )

        vendor_config = (
            db.query(config_model)
            .filter(config_model.user_id == user.id)
            .filter(config_model.identifier == identifier)
            .first()
        )
        if not vendor_config:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Configuration not found",
                    "message": (
                        f"{vendor_name.upper()} API configuration not found "
                        f"for this user with identifier {identifier}"
                    ),
                    "code": "CONFIG_NOT_FOUND",
                },
            )

        service = VendorMetricsService(user.id, db)
        metrics = await service.get_and_store_vendor_metrics(vendor_name, identifier)

        # Sort metrics by date
        if isinstance(metrics, dict) and "data" in metrics:
            metrics["data"] = sorted(
                metrics["data"],
                key=lambda x: (
                    int(x["month"].split("-")[1]),  # Year
                    int(x["month"].split("-")[0]),  # Month
                ),
            )

        return metrics
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid vendor",
                "message": str(e),
                "code": "INVALID_VENDOR",
            },
        )
    except VendorConfigurationNotFound as e:
        return JSONResponse(
            status_code=404,
            content={
                "error": "Configuration not found",
                "message": str(e),
                "code": "CONFIG_NOT_FOUND",
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Vendor metrics error",
                "message": str(e),
                "code": "VENDOR_ERROR",
            },
        )


@router.post("/batch-update")
async def batch_update_metrics(
    db: Session = Depends(get_db),
    api_key: str = Security(verify_api_key),
):
    """
    Update vendor metrics for all users and their configurations.
    This endpoint is meant to be called by a cron job and requires an API key.
    """
    if not api_key:
        raise HTTPException(
            status_code=403,
            detail={"message": "Invalid API key", "code": "INVALID_API_KEY"},
        )
    try:
        results = await VendorMetricsService.batch_update_all_vendor_metrics(db)
        return {"message": "Batch update completed", "results": results}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"message": str(e), "code": "BATCH_UPDATE_ERROR"},
        )
