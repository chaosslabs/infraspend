import logging
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from app.models import User
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


async def verify_api_key(api_key: str = Security(api_key_header)):
    secrets = SecretsService()
    stored_api_key = secrets.get_secret("INTERNAL_API_KEY")
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
        service = VendorMetricsService(user.id, db)
        metrics = await service.get_and_store_vendor_metrics(vendor, identifier)

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
        raise HTTPException(
            status_code=400,
            detail={
                "message": str(e),
                "code": "INVALID_VENDOR",
            },
        )
    except VendorConfigurationNotFound as e:
        raise HTTPException(
            status_code=404,
            detail={
                "message": str(e),
                "code": "CONFIG_NOT_FOUND",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"message": str(e), "code": "VENDOR_ERROR"},
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
