from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd


REQUIRED_FIXTURE_COLUMNS = {
    "date", "team", "opponent", "competition", "status", "source_url", "notes"
}


@dataclass
class SimulationResult:
    summary: dict
    milestone_dates: pd.Series
    milestone_fixture_numbers: pd.Series
    fixture_table: pd.DataFrame


def load_fixtures(path: str | Path) -> pd.DataFrame:
    """Load and validate fixture rows from CSV."""
    fixtures = pd.read_csv(path)
    missing = REQUIRED_FIXTURE_COLUMNS - set(fixtures.columns)
    if missing:
        raise ValueError(f"Fixture CSV missing columns: {sorted(missing)}")

    fixtures["date"] = pd.to_datetime(fixtures["date"], errors="coerce")
    if fixtures["date"].isna().any():
        raise ValueError("Every fixture row must have a valid ISO date (YYYY-MM-DD).")

    fixtures = fixtures.sort_values("date").reset_index(drop=True)
    if fixtures.duplicated(subset=["date", "team", "opponent", "competition"]).any():
        raise ValueError("Duplicate fixture rows found.")
    return fixtures


def build_projection_calendar(
    confirmed_fixtures: pd.DataFrame,
    end_date: str = "2030-12-31",
    projected_matches_per_month: float = 3.5,
) -> pd.DataFrame:
    """
    Append explicitly synthetic future fixture slots after the final confirmed fixture.
    These slots are planning assumptions, not published fixtures.
    """
    if projected_matches_per_month <= 0 or projected_matches_per_month > 12:
        raise ValueError("Projected matches per month must be between 0 and 12.")

    confirmed = confirmed_fixtures.copy()
    if confirmed.empty:
        raise ValueError("At least one confirmed fixture is required.")

    confirmed["fixture_type"] = "Confirmed"
    start = confirmed["date"].max() + pd.Timedelta(days=1)
    end = pd.Timestamp(end_date)
    if start > end:
        return confirmed

    # Generate evenly spaced placeholder dates to represent the selected monthly cadence.
    days_between = 30.4375 / projected_matches_per_month
    projected_dates = []
    current = start + pd.Timedelta(days=days_between)
    while current <= end:
        projected_dates.append(current.normalize())
        current += pd.Timedelta(days=days_between)

    projected = pd.DataFrame({
        "date": projected_dates,
        "team": "Inter Miami CF / future club or country fixture",
        "opponent": "Opponent not announced",
        "competition": "Unscheduled future fixture slot",
        "status": "projected",
        "source_url": "",
        "notes": "Synthetic placeholder; replace when official fixture is released.",
        "fixture_type": "Projected"
    })

    combined = pd.concat([confirmed, projected], ignore_index=True)
    return combined.sort_values("date").reset_index(drop=True)


def simulate_milestone(
    current_goals: int,
    target_goals: int,
    fixtures: pd.DataFrame,
    goals_per_appearance: float = 0.82,
    appearance_probability: float = 0.82,
    simulations: int = 20000,
    seed: int = 42,
) -> SimulationResult:
    """
    Simulate match-by-match goals.

    For each fixture, first sample whether the player appears. If he appears,
    sample goals from a Poisson distribution. This is a transparent baseline,
    not a trained player-performance model.
    """
    if current_goals < 0 or target_goals <= current_goals:
        raise ValueError("Target goals must be greater than a non-negative current total.")
    if goals_per_appearance < 0:
        raise ValueError("Goals per appearance cannot be negative.")
    if not 0 <= appearance_probability <= 1:
        raise ValueError("Appearance probability must be between 0 and 1.")
    if simulations < 100:
        raise ValueError("Use at least 100 simulations.")
    if fixtures.empty:
        raise ValueError("No fixtures supplied.")

    ordered = fixtures.sort_values("date").reset_index(drop=True)
    rng = np.random.default_rng(seed)
    n = len(ordered)

    totals = np.full(simulations, current_goals, dtype=int)
    reached = np.zeros(simulations, dtype=bool)
    milestone_dates = np.full(simulations, np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
    milestone_numbers = np.full(simulations, -1, dtype=int)

    for idx, fixture in ordered.iterrows():
        active = ~reached
        if not active.any():
            break

        # Confirmed and projected slots share the same user-selected appearance assumption.
        appeared = rng.random(simulations) < appearance_probability
        scored = np.zeros(simulations, dtype=int)
        playing = active & appeared
        scored[playing] = rng.poisson(goals_per_appearance, size=int(playing.sum()))
        totals += scored

        crossed = active & (totals >= target_goals)
        if crossed.any():
            reached[crossed] = True
            milestone_dates[crossed] = np.datetime64(fixture["date"].to_datetime64(), "ns")
            milestone_numbers[crossed] = idx + 1

    valid = reached
    if valid.any():
        dates = pd.to_datetime(milestone_dates[valid])
        fixture_numbers = pd.Series(milestone_numbers[valid], dtype=int)
        date_quantiles = pd.to_datetime(np.quantile(dates.asi8, [0.10, 0.50, 0.90]).astype("int64"))
        summary = {
            "probability_reached_by_horizon": float(valid.mean()),
            "p10_date": date_quantiles[0],
            "median_date": date_quantiles[1],
            "p90_date": date_quantiles[2],
            "median_fixture_number": int(fixture_numbers.median()),
            "simulations": int(simulations),
            "reached_count": int(valid.sum()),
        }
    else:
        dates = pd.Series(dtype="datetime64[ns]")
        fixture_numbers = pd.Series(dtype=int)
        summary = {
            "probability_reached_by_horizon": 0.0,
            "p10_date": None,
            "median_date": None,
            "p90_date": None,
            "median_fixture_number": None,
            "simulations": int(simulations),
            "reached_count": 0,
        }

    return SimulationResult(
        summary=summary,
        milestone_dates=pd.Series(dates).reset_index(drop=True),
        milestone_fixture_numbers=fixture_numbers.reset_index(drop=True),
        fixture_table=ordered,
    )


def probability_by_date(result: SimulationResult, date: str) -> float:
    """Probability that the milestone is reached on or before a date."""
    if result.milestone_dates.empty:
        return 0.0
    target = pd.Timestamp(date)
    return float((result.milestone_dates <= target).sum() / result.summary["simulations"])
