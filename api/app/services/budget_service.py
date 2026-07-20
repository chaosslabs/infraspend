from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
import logging
from app.models import BudgetPlan, User
from app.routers.models import BudgetPlanCreate

SUPPORTED_VENDORS = ["datadog", "aws", "heroku"]


class BudgetService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def create_budget_plan(self, plan_data: BudgetPlanCreate) -> BudgetPlan:
        """Create or update a budget plan for the user"""
        # Validate vendor
        if plan_data.vendor.lower() not in SUPPORTED_VENDORS:
            raise HTTPException(
                status_code=400, detail=f"Invalid vendor: {plan_data.vendor}"
            )

        # Try to find existing default plan for this vendor
        existing_plan = (
            self.db.query(BudgetPlan)
            .filter(
                BudgetPlan.user_id == self.user.id,
                BudgetPlan.vendor == plan_data.vendor.lower(),
                BudgetPlan.type == "default",
            )
            .first()
        )

        if existing_plan:
            # Update existing plan
            existing_plan.budgets = {
                "budgets": [
                    {"month": entry.month, "amount": entry.amount}
                    for entry in plan_data.budgets
                ]
            }
            existing_plan.updated_at = datetime.utcnow()
            budget_plan = existing_plan
        else:
            # Create new plan
            budget_plan = BudgetPlan(
                user_id=self.user.id,
                vendor=plan_data.vendor.lower(),
                budgets={
                    "budgets": [
                        {"month": entry.month, "amount": entry.amount}
                        for entry in plan_data.budgets
                    ]
                },
                type="default",
            )
            self.db.add(budget_plan)

        try:
            self.db.commit()
            self.db.refresh(budget_plan)
            return budget_plan
        except Exception as e:
            logging.error(f"Error creating/updating budget plan: {e}")
            self.db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def get_budget_plans(self, vendor: Optional[str] = None) -> List[BudgetPlan]:
        """Get all budget plans for the user, optionally filtered by vendor"""
        query = self.db.query(BudgetPlan).filter(BudgetPlan.user_id == self.user.id)

        if vendor:
            if vendor.lower() not in SUPPORTED_VENDORS:
                raise HTTPException(status_code=400, detail=f"Invalid vendor: {vendor}")
            query = query.filter(BudgetPlan.vendor == vendor.lower())

        return query.all()

    def update_budget_plan(
        self, plan_id: int, plan_data: BudgetPlanCreate
    ) -> BudgetPlan:
        """Update an existing budget plan"""
        budget_plan = (
            self.db.query(BudgetPlan)
            .filter(BudgetPlan.id == plan_id, BudgetPlan.user_id == self.user.id)
            .first()
        )

        if not budget_plan:
            raise HTTPException(status_code=404, detail="Budget plan not found")

        if plan_data.vendor.lower() != budget_plan.vendor:
            raise HTTPException(
                status_code=400, detail="Cannot change vendor for existing budget plan"
            )

        budget_plan.budgets = {
            "budgets": [
                {"month": entry.month, "amount": entry.amount}
                for entry in plan_data.budgets
            ]
        }
        budget_plan.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            self.db.refresh(budget_plan)
            return budget_plan
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def delete_budget_plan(self, plan_id: int) -> None:
        """Delete a budget plan"""
        budget_plan = (
            self.db.query(BudgetPlan)
            .filter(BudgetPlan.id == plan_id, BudgetPlan.user_id == self.user.id)
            .first()
        )

        if not budget_plan:
            raise HTTPException(status_code=404, detail="Budget plan not found")

        try:
            self.db.delete(budget_plan)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
