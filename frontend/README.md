# Messi 1000 Frontend

React + TypeScript + Vite dashboard for the Messi 1000 milestone forecasting project.

## Run in Codespaces

Start FastAPI in a separate terminal from the repository root:

```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

Start Vite from this directory:

```bash
npm run dev -- --host 0.0.0.0
```

The Vite development server proxies `/api` to `http://127.0.0.1:8000` by default. Override with `VITE_PROXY_TARGET` when needed.

## Build

```bash
npm run build
```

## API configuration

For development, leave `VITE_API_BASE_URL` unset so same-origin `/api` calls use the Vite proxy. For a separately deployed frontend, set `VITE_API_BASE_URL` to the FastAPI origin and allow the exact frontend origin in the backend's `MESSI1000_CORS_ORIGINS` setting.

The UI intentionally identifies the 943-goal starting value as unverified and describes the forecast engine as a Monte Carlo/Poisson baseline, not a trained ML model.
