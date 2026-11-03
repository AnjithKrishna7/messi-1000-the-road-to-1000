from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.predictor import (
    build_projection_calendar,
    load_fixtures,
    probability_by_date,
    simulate_milestone,
)

BASE_DIR = Path(__file__).resolve().parent
FIXTURE_PATH = BASE_DIR / "data" / "fixtures.csv"
FIXTURE_WINDOWS_PATH = BASE_DIR / "data" / "fixture_windows.csv"
HISTORICAL_MATCHES_PATH = BASE_DIR / "data" / "historical_matches.csv"

app = FastAPI(
    title="Messi 1000 API",
    version="0.1.0",
    description="Read-only data endpoints and a forecast adapter for the existing Monte Carlo engine.",
)

configured_origins = os.getenv(
    "MESSI1000_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in configured_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

HISTORICAL_COLUMNS = [
    "date", "team", "opponent", "competition", "venue", "appearance",
    "minutes", "goals", "penalty_goals", "source_url",
]


class ForecastRequest(BaseModel):
    current_goals: int = Field(default=943, ge=0, le=1500)
    target_goals: int = Field(default=1000, ge=1, le=1600)
    goals_per_appearance: float = Field(default=0.82, ge=0, le=5)
    appearance_probability: float = Field(default=0.82, ge=0, le=1)
    projected_matches_per_month: float = Field(default=3.5, gt=0, le=12)
    simulations: int = Field(default=20000, ge=100, le=50000)
    end_date: date = Field(default=date(2030, 12, 31))
    seed: int = Field(default=42, ge=0, le=2**32 - 1)


def _iso(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).isoformat()


def _load_historical_matches() -> pd.DataFrame:
    if not HISTORICAL_MATCHES_PATH.exists():
        return pd.DataFrame(columns=HISTORICAL_COLUMNS)

    history = pd.read_csv(HISTORICAL_MATCHES_PATH)
    missing = set(HISTORICAL_COLUMNS) - set(history.columns)
    if missing:
        raise ValueError(f"Historical match CSV is missing columns: {sorted(missing)}")

    if not history.empty:
        history["date"] = pd.to_datetime(history["date"], errors="coerce")
        if history["date"].isna().any():
            raise ValueError("Historical match rows must have valid dates.")
        history = history.sort_values("date", ascending=False).reset_index(drop=True)

    return history


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "messi-1000-api", "version": app.version}


@app.get("/api/fixtures")
def fixtures() -> dict[str, Any]:
    try:
        frame = load_fixtures(FIXTURE_PATH)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not load fixture data: {exc}") from exc

    rows = frame.copy()
    rows["date"] = rows["date"].dt.strftime("%Y-%m-%d")
    rows["fixture_type"] = "Confirmed"
    return {"count": len(rows), "fixtures": rows.to_dict(orient="records")}


@app.get("/api/fixture-windows")
def fixture_windows() -> dict[str, Any]:
    if not FIXTURE_WINDOWS_PATH.exists():
        return {"count": 0, "windows": []}

    try:
        frame = pd.read_csv(FIXTURE_WINDOWS_PATH)
        required = {"window_start", "window_end", "round", "status", "source_url", "notes"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Fixture-window CSV is missing columns: {sorted(missing)}")
        for column in ("window_start", "window_end"):
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
            if frame[column].isna().any():
                raise ValueError(f"Invalid dates in {column}.")
            frame[column] = frame[column].dt.strftime("%Y-%m-%d")
        return {"count": len(frame), "windows": frame.to_dict(orient="records")}
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not load fixture windows: {exc}") from exc


@app.get("/api/history")
def history(
    team: str = Query(default="All", pattern="^(All|Club|Argentina)$"),
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    try:
        frame = _load_historical_matches()
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not load historical match data: {exc}") from exc

    if team == "Argentina" and not frame.empty:
        frame = frame[frame["team"].astype(str).str.contains("Argentina", case=False, na=False)]
    elif team == "Club" and not frame.empty:
        frame = frame[~frame["team"].astype(str).str.contains("Argentina", case=False, na=False)]

    if search and not frame.empty:
        searchable = frame[["team", "opponent", "competition"]].fillna("").astype(str)
        mask = searchable.apply(
            lambda column: column.str.contains(search, case=False, regex=False)
        ).any(axis=1)
        frame = frame[mask]

    total = len(frame)
    page = frame.iloc[offset : offset + limit].copy()
    if not page.empty:
        page["date"] = page["date"].dt.strftime("%Y-%m-%d")
        page = page.astype(object).where(pd.notna(page), None)

    return {
        "available": total > 0,
        "total": total,
        "limit": limit,
        "offset": offset,
        "matches": page.to_dict(orient="records"),
        "message": None if total else "No verified historical match records have been imported yet.",
    }


@app.get("/api/data-status")
def data_status() -> dict[str, Any]:
    try:
        fixture_frame = load_fixtures(FIXTURE_PATH)
        history_frame = _load_historical_matches()
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not inspect data status: {exc}") from exc

    history_count = len(history_frame)
    sourced_count = 0
    if history_count and "source_url" in history_frame:
        sourced_count = int(
            history_frame["source_url"].fillna("").astype(str).str.strip().ne("").sum()
        )

    fixture_sourced_count = int(
        fixture_frame["source_url"].fillna("").astype(str).str.strip().ne("").sum()
    )
    return {
        "historical_matches": {
            "count": history_count,
            "available": history_count > 0,
            "rows_with_source_url": sourced_count,
            "source_coverage": sourced_count / history_count if history_count else 0.0,
            "file": "data/historical_matches.csv",
        },
        "fixtures": {
            "count": len(fixture_frame),
            "rows_with_source_url": fixture_sourced_count,
            "source_coverage": fixture_sourced_count / len(fixture_frame) if len(fixture_frame) else 0.0,
            "file": "data/fixtures.csv",
        },
        "starting_goal_total": {
            "default": 943,
            "verified": False,
            "note": "Working baseline only; reconcile against a consistent match-level record.",
        },
        "forecast_engine": "existing Monte Carlo predictor; not a trained ML model",
    }


@app.post("/api/forecast")
def forecast(request: ForecastRequest) -> dict[str, Any]:
    if request.target_goals <= request.current_goals:
        raise HTTPException(status_code=422, detail="target_goals must be greater than current_goals.")

    try:
        confirmed = load_fixtures(FIXTURE_PATH)
        calendar = build_projection_calendar(
            confirmed,
            end_date=request.end_date.isoformat(),
            projected_matches_per_month=request.projected_matches_per_month,
        )
        # The existing calendar builder retains confirmed fixtures beyond the horizon.
        # The API trims them so a forecast cannot silently simulate past its requested end date.
        calendar = calendar.loc[calendar["date"] <= pd.Timestamp(request.end_date)].copy()
        if calendar.empty:
            raise ValueError("No confirmed or projected fixtures fall on or before end_date.")
        result = simulate_milestone(
            current_goals=request.current_goals,
            target_goals=request.target_goals,
            fixtures=calendar,
            goals_per_appearance=request.goals_per_appearance,
            appearance_probability=request.appearance_probability,
            simulations=request.simulations,
            seed=request.seed,
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    summary = result.summary
    median_number = summary["median_fixture_number"]
    median_fixture = None
    if median_number is not None:
        index = int(median_number) - 1
        if 0 <= index < len(calendar):
            row = calendar.iloc[index]
            median_fixture = {
                "fixture_number": int(median_number),
                "date": _iso(row["date"]),
                "team": str(row["team"]),
                "opponent": str(row["opponent"]),
                "competition": str(row["competition"]),
                "fixture_type": str(row["fixture_type"]),
            }

    year_probabilities = {}
    for year in range(date.today().year, request.end_date.year + 1):
        year_probabilities[str(year)] = probability_by_date(result, f"{year}-12-31")

    confirmed_count = int((calendar["fixture_type"] == "Confirmed").sum())
    projected_count = int((calendar["fixture_type"] == "Projected").sum())
    return {
        "model": "monte_carlo_poisson_baseline",
        "assumptions": {
            "current_goals": request.current_goals,
            "target_goals": request.target_goals,
            "goals_per_appearance": request.goals_per_appearance,
            "appearance_probability": request.appearance_probability,
            "projected_matches_per_month": request.projected_matches_per_month,
            "simulations": request.simulations,
            "seed": request.seed,
            "end_date": request.end_date.isoformat(),
        },
        "summary": {
            "probability_reached_by_horizon": summary["probability_reached_by_horizon"],
            "p10_date": _iso(summary["p10_date"]),
            "median_date": _iso(summary["median_date"]),
            "p90_date": _iso(summary["p90_date"]),
            "median_fixture_number": median_number,
            "simulations": summary["simulations"],
            "reached_count": summary["reached_count"],
            "median_fixture": median_fixture,
            "probability_by_year_end": year_probabilities,
        },
        "calendar": {
            "confirmed_fixture_count": confirmed_count,
            "projected_slot_count": projected_count,
            "total_rows": len(calendar),
        },
        "data_warning": (
            "This is a configurable baseline simulation, not a trained model. "
            "Historical match data has not yet been imported, and the default goal total is unverified."
        ),
    }
