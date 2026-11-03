export type Fixture = {
  date: string;
  team: string;
  opponent: string;
  competition: string;
  status?: string;
  fixture_type?: string;
  source_url?: string;
  notes?: string;
};

export type DataStatus = {
  historical_matches: {
    count: number;
    available: boolean;
    rows_with_source_url: number;
    source_coverage: number;
    file: string;
  };
  fixtures: {
    count: number;
    rows_with_source_url: number;
    source_coverage: number;
    file: string;
  };
  starting_goal_total: {
    default: number;
    verified: boolean;
    note: string;
  };
  forecast_engine: string;
};

export type ForecastResponse = {
  model: string;
  assumptions: {
    current_goals: number;
    target_goals: number;
    goals_per_appearance: number;
    appearance_probability: number;
    projected_matches_per_month: number;
    simulations: number;
    end_date: string;
    seed: number;
  };
  summary: {
    probability_reached_by_horizon: number;
    p10_date: string | null;
    median_date: string | null;
    p90_date: string | null;
    median_fixture_number: number | null;
    simulations: number;
    reached_count: number;
    median_fixture: Fixture | null;
    probability_by_year_end: Record<string, number>;
  };
  calendar: {
    confirmed_fixture_count: number;
    projected_slot_count: number;
    total_rows: number;
  };
  data_warning: string;
};

export type ForecastRequest = {
  current_goals: number;
  target_goals: number;
  goals_per_appearance: number;
  appearance_probability: number;
  projected_matches_per_month: number;
  simulations: number;
  end_date: string;
  seed: number;
};

// In development, Vite proxies /api to the FastAPI service on port 8000.
// For a separately deployed frontend, set VITE_API_BASE_URL to the API origin.
const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim();
export const API_BASE = configuredApiBase ? configuredApiBase.replace(/\/$/, "") : "";

function getApiDocsUrl(): string {
  if (API_BASE) return `${API_BASE}/docs`;
  const host = window.location.hostname;
  if (host.endsWith("-5173.app.github.dev")) {
    return `https://${host.replace("-5173.app.github.dev", "-8000.app.github.dev")}/docs`;
  }
  return "http://localhost:8000/docs";
}

export const API_DOCS_URL = getApiDocsUrl();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...(init?.headers ?? {}) },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `API request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

export const getHealth = () =>
  request<{ status: string; service: string; version: string }>("/api/health");

export const getFixtures = () =>
  request<{ count: number; fixtures: Fixture[] }>("/api/fixtures");

export const getDataStatus = () => request<DataStatus>("/api/data-status");

export const getForecast = (payload: ForecastRequest) =>
  request<ForecastResponse>("/api/forecast", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
