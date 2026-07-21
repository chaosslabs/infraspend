import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
import io
import csv
import json
from sqlalchemy.orm import Session
from app.models import User
from app.models import (
    DatadogAPIConfiguration,
    AWSAPIConfiguration,
    HerokuAPIConfiguration,
)
from app.helpers.database import get_db
from app.helpers.auth import get_authenticated_user
from app.services.forecast_service import ForecastService
from app.services.datadog_service import DatadogService
from app.services.aws_service import AWSService
from app.services.heroku_service import HerokuService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cloud-cost-forecast"])


@router.get("/v1/vendors-forecast/{vendor_name}")
async def get_vendor_forecast(
    vendor_name: str,
    format: str = Query(None, description="Response format (csv or json)"),
    your_forecast: str = Query(None, description="Your forecast data as JSON string"),
    identifier: str = Query(
        "Default Configuration", description="Configuration identifier"
    ),
    auth_user: dict = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    try:
        user = db.query(User).filter(User.sub == auth_user["sub"]).first()
        if not user:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "User not found",
                    "message": "Unable to find user record",
                    "code": "USER_NOT_FOUND",
                },
            )

        vendor_name = vendor_name.lower()
        if vendor_name == "datadog":
            datadog_config = (
                db.query(DatadogAPIConfiguration)
                .filter(DatadogAPIConfiguration.user_id == user.id)
                .filter(DatadogAPIConfiguration.identifier == identifier)
                .first()
            )

            if not datadog_config:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "Configuration not found",
                        "message": (
                            "Datadog API configuration not found "
                            f"for this user with identifier {identifier}"
                        ),
                        "code": "CONFIG_NOT_FOUND",
                    },
                )

            service = DatadogService(user.id, db, identifier)
        elif vendor_name == "aws":
            aws_config = (
                db.query(AWSAPIConfiguration)
                .filter(AWSAPIConfiguration.user_id == user.id)
                .filter(AWSAPIConfiguration.identifier == identifier)
                .first()
            )

            if not aws_config:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "Configuration not found",
                        "message": (
                            "AWS API configuration not found "
                            f"for this user with identifier {identifier}"
                        ),
                        "code": "CONFIG_NOT_FOUND",
                    },
                )

            service = AWSService(user.id, db, identifier)
        elif vendor_name == "heroku":
            heroku_config = (
                db.query(HerokuAPIConfiguration)
                .filter(HerokuAPIConfiguration.user_id == user.id)
                .filter(HerokuAPIConfiguration.identifier == identifier)
                .first()
            )

            if not heroku_config:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "Configuration not found",
                        "message": (
                            "Heroku API configuration not found "
                            f"for this user with identifier {identifier}"
                        ),
                        "code": "CONFIG_NOT_FOUND",
                    },
                )

            service = HerokuService(user.id, db, identifier)
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid vendor",
                    "message": f"Vendor type '{vendor_name}' not implemented",
                    "code": "INVALID_VENDOR",
                },
            )

        historical_data = service.get_monthly_costs()
        if isinstance(historical_data, JSONResponse):
            return historical_data

        # Generate forecast using the ForecastService
        forecast_data = ForecastService.predict_mom_growth(historical_data["data"])

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers with Your Forecast column
            writer.writerow(
                [
                    "Month",
                    "Best Case",
                    "Trend-based Forecast",
                    "Worst Case",
                    "Your Forecast",
                ]
            )

            # Parse your_forecast data if provided
            your_forecast_data = []
            if your_forecast:
                try:
                    your_forecast_data = json.loads(your_forecast)
                except json.JSONDecodeError:
                    your_forecast_data = []

            # Write forecast data including Your Forecast
            for i, entry in enumerate(forecast_data["forecast_data"]):
                row = [
                    entry["month"],
                    entry["best_case"],
                    entry["cost"],
                    entry["worst_case"],
                    # If your_forecast is not provided, use the trend-based forecast
                    (
                        your_forecast_data[i]
                        if your_forecast_data and i < len(your_forecast_data)
                        else entry["cost"]
                    ),
                ]
                writer.writerow(row)

            output.seek(0)
            output_value = output.getvalue()
            response = Response(
                content=output_value,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={vendor_name}_forecast.csv",
                    "Content-Type": "text/csv; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "no-cache",
                },
            )
            return response

        return JSONResponse(
            status_code=200,
            content={
                "historical": historical_data["data"],
                "forecast": forecast_data["forecast_data"],
                "sums": forecast_data["sums"],
                "growth_rates": forecast_data["growth_rates"],
                "message": "Successfully retrieved forecast",
            },
        )

    except Exception as e:
        logger.error(f"Error in forecast: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(e),
                "code": "INTERNAL_ERROR",
            },
        )
