from pydantic import BaseModel
from typing import List
from datetime import datetime


class DatadogAPIConfig(BaseModel):
    app_key: str | None = None
    api_key: str | None = None


class AWSAPIConfig(BaseModel):
    aws_access_key_id: str
    aws_secret_access_key: str


class HerokuAPIConfig(BaseModel):
    api_key: str
    team_name_or_id: str | None = None


class APIConfigResponse(BaseModel):
    id: int
    type: str
    message: str


class UserProfile(BaseModel):
    email: str | None = None
    name: str | None = None
    picture: str | None = None


class BudgetEntry(BaseModel):
    month: str  # Format: MM-YYYY
    amount: float


class BudgetPlanCreate(BaseModel):
    vendor: str
    budgets: List[BudgetEntry]


class BudgetPlanResponse(BaseModel):
    id: int
    vendor: str
    type: str
    budgets: List[BudgetEntry]
    created_at: datetime
    updated_at: datetime
