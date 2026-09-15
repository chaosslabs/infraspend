from typing import List, Dict, Any, TypedDict
from datetime import date, datetime, timezone
from math import isfinite

from app.services.monthly_costs import add_month, parse_iso_date


class HistoricalDataPoint(TypedDict):
    month: str
    cost: float


class ForecastService:
    @staticmethod
    def predict_mom_growth(
        historical_data: List[HistoricalDataPoint],
        months_to_predict: int = 12,
        *,
        as_of: date | None = None,
    ) -> Dict[str, Any]:
        """Estimate from consecutive completed UTC months, never partial totals.

        Missing months are unknown. Use only the most recent contiguous history;
        do not extrapolate from stale history or a zero-to-positive transition.
        Scenarios are illustrative growth variations, not confidence intervals.
        """
        today = as_of or datetime.now(timezone.utc).date()
        current_month = today.replace(day=1)
        result = {
            "forecast_data": [],
            "sums": {"total_forecast": 0, "total_best_case": 0, "total_worst_case": 0},
            "growth_rates": {"trend_based": 0, "best_case": 0, "worst_case": 0},
            "basis": {
                "status": "insufficient_history",
                "message": "At least two consecutive completed months are needed for a forecast.",
                "base_month": None,
                "base_cost": None,
                "excluded_months": [],
            },
        }
        complete = {}
        for row in historical_data:
            month = datetime.strptime(row["month"], "%m-%Y").date()
            end = add_month(month)
            if (
                month >= current_month
                or (
                    row.get("period_start")
                    and parse_iso_date(row["period_start"], "period_start") != month
                )
                or (
                    row.get("period_end")
                    and parse_iso_date(row["period_end"], "period_end") != end
                )
            ):
                result["basis"]["excluded_months"].append(row["month"])
                continue
            if month in complete or not isfinite(row["cost"]) or row["cost"] < 0:
                result["basis"].update(
                    status="unsupported_history",
                    message="Forecast unavailable: duplicate months or unsupported cost values.",
                )
                return result
            complete[month] = row["cost"]

        months = sorted(complete)
        if not months:
            return result
        last = months[-1]
        if add_month(last) != current_month:
            result["basis"].update(
                status="stale_history",
                message=(
                    "Forecast unavailable until the last completed "
                    "month's costs are available."
                ),
            )
            return result
        consecutive = [last]
        for month in reversed(months[:-1]):
            if add_month(month) != consecutive[-1]:
                break
            consecutive.append(month)
        consecutive.reverse()
        if len(consecutive) < 2:
            return result
        growth = []
        for previous, current in zip(consecutive, consecutive[1:]):
            before, after = complete[previous], complete[current]
            if before == 0 and after > 0:
                result["basis"].update(
                    status="zero_baseline",
                    message=(
                        "Forecast unavailable: growth from a zero-cost month "
                        "cannot be estimated reliably."
                    ),
                )
                return result
            growth.append((after - before) / before if before else 0.0)
        avg_growth = sum(growth) / len(growth)
        spread = abs(avg_growth) * 0.5
        rates = (max(-1.0, avg_growth - spread), avg_growth, avg_growth + spread)
        costs = [complete[last]] * 3
        rows = []
        month = last
        for _ in range(months_to_predict):
            month = add_month(month)
            costs = [cost * (1 + rate) for cost, rate in zip(costs, rates)]
            if not all(isfinite(cost) for cost in costs):
                result["basis"].update(
                    status="unsupported_history",
                    message="Forecast unavailable: growth is too large to estimate reliably.",
                )
                return result
            rows.append(
                {
                    "month": month.strftime("%m-%Y"),
                    "best_case": round(costs[0], 2),
                    "cost": round(costs[1], 2),
                    "worst_case": round(costs[2], 2),
                }
            )
        result["forecast_data"] = rows
        result["sums"] = {
            "total_forecast": round(sum(row["cost"] for row in rows), 2),
            "total_best_case": round(sum(row["best_case"] for row in rows), 2),
            "total_worst_case": round(sum(row["worst_case"] for row in rows), 2),
        }
        result["growth_rates"] = {
            key: round(rate * 100, 2)
            for key, rate in zip(("best_case", "trend_based", "worst_case"), rates)
        }
        result["basis"].update(
            status="ready",
            message=(
                "Estimate from consecutive completed months. Current partial "
                "months are excluded; scenarios are illustrative, not bills."
            ),
            base_month=last.strftime("%m-%Y"),
            base_cost=complete[last],
        )
        return result
