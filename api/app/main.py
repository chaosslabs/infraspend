from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.routers import vendor_metrics, users, forecast, configuration, budget
from app.helpers.secrets import Secrets
from app.helpers.config import Config
from app.migrations.run_all import run_migrations
from pythonjsonlogger import jsonlogger

import logging

# Configure JSON logging
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Reduce SQLAlchemy logging verbosity
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
# Run migrations
run_migrations()


def setup_app():
    app = FastAPI()

    # Add exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.error(f"Validation error: {exc}")
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unexpected error: {str(exc)}")
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    secrets = Secrets()
    config = Config()
    app.add_middleware(SessionMiddleware, secret_key=secrets.AppSecretKey)

    # Set up CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CorsAllowedOrigins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = setup_app()

app.include_router(vendor_metrics.router)
app.include_router(users.router)
app.include_router(forecast.router)
app.include_router(configuration.router)
app.include_router(budget.router)
