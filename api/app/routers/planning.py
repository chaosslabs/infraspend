"""Manual budget scenarios with immutable revisions; no provider mutation."""

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, confloat, constr, root_validator, validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.helpers.database import get_db
from app.models import PlanningRevision, User
from app.routers.budget import get_user

Amount = confloat(ge=0, le=1e10, allow_inf_nan=False)
ShortText = constr(strip_whitespace=True, max_length=200)
Notes = constr(strip_whitespace=True, max_length=4000)


class StrictModel(BaseModel):
    class Config:
        extra = "forbid"


class Action(StrictModel):
    title: ShortText = ""
    owner: ShortText = ""
    status: Literal[
        "Proposed", "Accepted", "Testing", "Measured", "Deferred", "Rejected"
    ] = "Proposed"
    criteria: Notes = ""
    baselineWindow: ShortText = ""
    comparisonWindow: ShortText = ""
    baselineCost: Amount | None = None
    baselineUnits: Amount | None = None
    resultCost: Amount | None = None
    resultUnits: Amount | None = None
    quality: Literal["Not reviewed", "Passed", "Failed"] = "Not reviewed"
    notes: Notes = ""

    @root_validator(skip_on_failure=True)
    def validate_action(cls, values):
        if values["status"] in ("Accepted", "Testing", "Measured"):
            if not all(values[k] for k in ("title", "owner", "criteria")):
                raise ValueError(
                    "An accepted action requires a title, owner and success criteria"
                )
        if values["status"] == "Measured":
            if (
                not all(
                    values[k] for k in ("baselineWindow", "comparisonWindow", "notes")
                )
                or values["baselineCost"] is None
                or values["resultCost"] is None
                or not values["baselineUnits"]
                or not values["resultUnits"]
                or values["quality"] == "Not reviewed"
            ):
                raise ValueError(
                    "Measured actions require windows, costs, positive task counts, "
                    "quality review and confounder notes"
                )
        return values


class Plan(StrictModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=200)
    month: str
    budget: Amount
    variableCost: Amount
    fixedCost: Amount
    growth: confloat(ge=-100, le=1000, allow_inf_nan=False)
    reduction: confloat(ge=0, le=100, allow_inf_nan=False)
    basis: Literal["Manual estimate", "Provider-reported", "Manual bill"]
    evidence: Notes = ""
    action: Action = Field(default_factory=Action)

    @validator("month")
    def valid_month(cls, value):
        parsed = date.fromisoformat(value + "-01")
        if parsed.strftime("%Y-%m") != value:
            raise ValueError("Use YYYY-MM")
        return value

    @root_validator(skip_on_failure=True)
    def require_evidence(cls, values):
        if values["basis"] != "Manual estimate" and not values["evidence"]:
            raise ValueError("Reported baselines require a source and billing period")
        return values


class SavePlan(StrictModel):
    plan_id: UUID
    expected_version: int = Field(ge=0)
    payload: Plan


router = APIRouter(prefix="/v1/planning", tags=["planning"])


def serialize(row: PlanningRevision) -> dict:
    return {
        "plan_id": row.plan_id,
        "version": row.version,
        "payload": row.payload,
        "created_at": row.created_at.isoformat() + "Z",
    }


@router.get("")
def list_plans(
    user: User = Depends(get_user),
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    latest = (
        db.query(
            PlanningRevision.plan_id,
            func.max(PlanningRevision.version).label("version"),
        )
        .filter(PlanningRevision.user_id == user.id)
        .group_by(PlanningRevision.plan_id)
        .subquery()
    )
    rows = (
        db.query(PlanningRevision)
        .join(
            latest,
            (PlanningRevision.plan_id == latest.c.plan_id)
            & (PlanningRevision.version == latest.c.version),
        )
        .filter(PlanningRevision.user_id == user.id)
        .order_by(PlanningRevision.created_at.desc(), PlanningRevision.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"data": [serialize(row) for row in rows]}


@router.get("/{plan_id}/history")
def history(
    plan_id: UUID,
    user: User = Depends(get_user),
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    rows = (
        db.query(PlanningRevision)
        .filter(
            PlanningRevision.user_id == user.id,
            PlanningRevision.plan_id == str(plan_id),
        )
        .order_by(PlanningRevision.version.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    if not rows:
        raise HTTPException(404, "Plan history not found")
    return {"data": [serialize(row) for row in rows]}


@router.post("")
def save_plan(
    request: SavePlan, user: User = Depends(get_user), db: Session = Depends(get_db)
):
    latest = (
        db.query(func.max(PlanningRevision.version))
        .filter(
            PlanningRevision.user_id == user.id,
            PlanningRevision.plan_id == str(request.plan_id),
        )
        .scalar()
        or 0
    )
    if latest != request.expected_version:
        raise HTTPException(
            409, "This plan changed in another session. Reload plans before saving."
        )
    row = PlanningRevision(
        user_id=user.id,
        plan_id=str(request.plan_id),
        version=latest + 1,
        payload=request.payload.dict(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "This plan changed in another session. Reload plans before saving."
        )
    db.refresh(row)
    return {"data": serialize(row)}
