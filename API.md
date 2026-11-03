# Messi 1000 API

This API exposes the existing Python forecast engine to a separate React frontend. It does not replace or rewrite `src/predictor.py`.

## Run locally

```bash
python -m pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Interactive API documentation: `http://localhost:8000/docs`.

## Endpoints

- `GET /api/health` — service health.
- `GET /api/fixtures` — published fixture rows from `data/fixtures.csv`.
- `GET /api/fixture-windows` — conditional playoff windows, kept separate from confirmed fixtures.
- `GET /api/history?team=All&search=&limit=100&offset=0` — historical match rows. It returns an explicit empty state while the archive is empty.
- `GET /api/data-status` — record counts and source coverage.
- `POST /api/forecast` — invokes the existing Monte Carlo simulation.

## Forecast request

```json
{
  "current_goals": 943,
  "target_goals": 1000,
  "goals_per_appearance": 0.82,
  "appearance_probability": 0.82,
  "projected_matches_per_month": 3.5,
  "simulations": 20000,
  "end_date": "2030-12-31",
  "seed": 42
}
```

The response includes the milestone probability, conditional P10/median/P90 dates, year-end probabilities, median calendar slot and confirmed/projected calendar coverage. The model is explicitly labelled as a baseline Monte Carlo model, not trained machine learning.

## React example

```ts
const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/forecast`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    current_goals: 943,
    target_goals: 1000,
    goals_per_appearance: 0.82,
    appearance_probability: 0.82,
    projected_matches_per_month: 3.5,
    simulations: 20000,
    end_date: "2030-12-31",
    seed: 42
  })
});
if (!response.ok) throw new Error(`Forecast API failed: ${response.status}`);
const forecast = await response.json();
```

Set `VITE_API_BASE_URL` to the API origin, for example `http://localhost:8000` during local development.

## CORS

Set `MESSI1000_CORS_ORIGINS` to a comma-separated list of exact frontend origins. For example:

```bash
MESSI1000_CORS_ORIGINS="http://localhost:5173,https://YOUR-CODESPACE-5173.app.github.dev"
```

Do not use an unrestricted wildcard origin for a deployed frontend. Keep the forwarded API port private in Codespaces unless you have a deliberate deployment and access-control plan.

## Data integrity

- The current default goal total (943) is returned as an **unverified working baseline**.
- `data/historical_matches.csv` is a schema-only file until source-backed records are added.
- Synthetic future slots are separated from published fixtures.
- Conditional playoff windows are not represented as guaranteed fixtures.
- Every historical match record should carry its source URL.
