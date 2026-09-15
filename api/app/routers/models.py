from pydantic import BaseModel, Field, validator
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
    month: str = Field(regex=r"^(0[1-9]|1[0-2])-\d{4}$")
    amount: float = Field(ge=0, allow_inf_nan=False)

    @validator("month")
    def valid_month(cls, value):
        datetime.strptime(value, "%m-%Y")
        return value


class BudgetPlanCreate(BaseModel):
    vendor: str
    budgets: List[BudgetEntry]
    # Omitted scope keeps the existing vendor-wide API contract.
    identifier: str | None = Field(default=None, min_length=1, max_length=255)

    @validator("identifier")
    def nonblank_identifier(cls, value):
        if value is not None and not value.strip():
            raise ValueError("identifier must not be blank")
        return value

    @validator("budgets")
    def unique_months(cls, entries):
        if len({entry.month for entry in entries}) != len(entries):
            raise ValueError("Budget months must be unique")
        return entries


class BudgetPlanResponse(BaseModel):
    id: int
    vendor: str
    type: str
    budgets: List[BudgetEntry]
    created_at: datetime
    updated_at: datetime
