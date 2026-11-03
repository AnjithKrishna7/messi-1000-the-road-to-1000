from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_fixtures_endpoint_returns_confirmed_rows():
    response = client.get("/api/fixtures")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 15
    assert len(payload["fixtures"]) == 15
    assert {row["fixture_type"] for row in payload["fixtures"]} == {"Confirmed"}


def test_history_endpoint_reports_empty_archive_without_fabricating_rows(tmp_path, monkeypatch):
    history_file = tmp_path / "historical_matches.csv"
    history_file.write_text(
        "date,team,opponent,competition,venue,appearance,minutes,goals,penalty_goals,source_url\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "HISTORICAL_MATCHES_PATH", history_file)

    response = client.get("/api/history")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert payload["total"] == 0
    assert payload["matches"] == []


def test_forecast_endpoint_reuses_existing_simulation_engine():
    response = client.post(
        "/api/forecast",
        json={
            "current_goals": 999,
            "target_goals": 1000,
            "goals_per_appearance": 5,
            "appearance_probability": 1,
            "simulations": 100,
            "end_date": "2026-12-31",
            "seed": 1,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "monte_carlo_poisson_baseline"
    assert payload["summary"]["probability_reached_by_horizon"] > 0.98
    assert payload["summary"]["median_date"].startswith("2026-11-07T")
    assert payload["calendar"]["confirmed_fixture_count"] == 1
    assert payload["calendar"]["total_rows"] == 1


def test_forecast_rejects_target_not_above_current_total():
    response = client.post(
        "/api/forecast",
        json={"current_goals": 1000, "target_goals": 1000},
    )
    assert response.status_code == 422
