from datetime import date
import pytest
from app.services.forecast_service import ForecastService


def forecast(rows, as_of=date(2026, 9, 15), count=12):
    return ForecastService.predict_mom_growth(rows, count, as_of=as_of)


def test_calendar_months_do_not_repeat_or_skip():
    result = forecast(
        [{"month": "12-2025", "cost": 100}, {"month": "01-2026", "cost": 100}],
        date(2026, 2, 15),
    )
    months = [row["month"] for row in result["forecast_data"]]
    assert months == [f"{m:02d}-2026" for m in range(2, 13)] + ["01-2027"]


@pytest.mark.parametrize("cost", [0, 20, 80, 100, 120])
def test_scenarios_are_ordered_nonnegative_for_growth_and_decline(cost):
    result = forecast(
        [{"month": "07-2026", "cost": 100}, {"month": "08-2026", "cost": cost}]
    )
    assert len(result["forecast_data"]) == 12
    for row in result["forecast_data"]:
        assert 0 <= row["best_case"] <= row["cost"] <= row["worst_case"]


def test_partial_current_month_does_not_distort_growth():
    result = forecast(
        [
            {"month": "07-2026", "cost": 100},
            {"month": "08-2026", "cost": 100},
            {"month": "09-2026", "cost": 5},
        ]
    )
    assert result["growth_rates"]["trend_based"] == 0
    assert result["forecast_data"][0]["cost"] == 100
    assert result["basis"]["base_month"] == "08-2026"
    assert result["basis"]["excluded_months"] == ["09-2026"]


@pytest.mark.parametrize(
    "rows,status",
    [
        (
            [{"month": "06-2026", "cost": 100}, {"month": "08-2026", "cost": 200}],
            "insufficient_history",
        ),
        (
            [{"month": "06-2026", "cost": 100}, {"month": "07-2026", "cost": 200}],
            "stale_history",
        ),
        (
            [{"month": "07-2026", "cost": 0}, {"month": "08-2026", "cost": 100}],
            "zero_baseline",
        ),
        (
            [
                {"month": "07-2026", "cost": 100},
                {"month": "08-2026", "cost": 100, "period_end": "2026-08-15"},
            ],
            "stale_history",
        ),
    ],
)
def test_unknown_or_incomplete_history_is_not_invented(rows, status):
    result = forecast(rows)
    assert result["forecast_data"] == []
    assert result["basis"]["status"] == status


def test_gap_does_not_affect_latest_consecutive_history():
    result = forecast(
        [
            {"month": "01-2026", "cost": 10000},
            {"month": "07-2026", "cost": 100},
            {"month": "08-2026", "cost": 100},
        ]
    )
    assert result["basis"]["status"] == "ready"
    assert result["growth_rates"]["trend_based"] == 0
