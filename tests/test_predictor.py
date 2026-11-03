from pathlib import Path
import pandas as pd
import pytest

from src.predictor import load_fixtures, build_projection_calendar, simulate_milestone

ROOT = Path(__file__).resolve().parents[1]


def test_fixture_file_loads_and_is_sorted():
    fixtures = load_fixtures(ROOT / "data" / "fixtures.csv")
    assert len(fixtures) == 15
    assert fixtures["date"].is_monotonic_increasing
    assert set(fixtures["status"]) == {"confirmed"}


def test_projection_calendar_labels_synthetic_rows():
    fixtures = load_fixtures(ROOT / "data" / "fixtures.csv")
    calendar = build_projection_calendar(fixtures, end_date="2027-12-31", projected_matches_per_month=4)
    assert (calendar["fixture_type"] == "Confirmed").sum() == len(fixtures)
    assert (calendar["fixture_type"] == "Projected").sum() > 0
    projected = calendar[calendar["fixture_type"] == "Projected"]
    assert projected["opponent"].eq("Opponent not announced").all()


def test_simulation_reaches_target_when_goals_are_certain():
    fixtures = pd.DataFrame({
        "date": pd.to_datetime(["2027-01-01", "2027-01-08"]),
        "team": ["A", "A"],
        "opponent": ["B", "C"],
        "competition": ["Test", "Test"],
        "status": ["confirmed", "confirmed"],
        "source_url": ["", ""],
        "notes": ["", ""],
    })
    result = simulate_milestone(
        current_goals=999,
        target_goals=1000,
        fixtures=fixtures,
        goals_per_appearance=100.0,
        appearance_probability=1.0,
        simulations=1000,
        seed=1,
    )
    assert result.summary["probability_reached_by_horizon"] == 1.0
    assert result.summary["median_date"] == pd.Timestamp("2027-01-01")


def test_invalid_appearance_probability_is_rejected():
    fixtures = load_fixtures(ROOT / "data" / "fixtures.csv")
    with pytest.raises(ValueError):
        simulate_milestone(943, 1000, fixtures, appearance_probability=1.5)
