import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Clock3,
  Crosshair,
  ExternalLink,
  Gauge,
  Info,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Trophy,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  API_DOCS_URL,
  getDataStatus,
  getFixtures,
  getForecast,
  getHealth,
  type DataStatus,
  type Fixture,
  type ForecastResponse,
} from "./api";
import "./App.css";

type Scenario = "conservative" | "base" | "optimistic";
type ScenarioConfig = {
  label: string;
  detail: string;
  goalsPerAppearance: number;
  appearanceProbability: number;
  matchesPerMonth: number;
};

const scenarios: Record<Scenario, ScenarioConfig> = {
  conservative: {
    label: "Conservative",
    detail: "Lower scoring rate and availability",
    goalsPerAppearance: 0.68,
    appearanceProbability: 0.72,
    matchesPerMonth: 3.0,
  },
  base: {
    label: "Base case",
    detail: "Current working assumptions",
    goalsPerAppearance: 0.82,
    appearanceProbability: 0.82,
    matchesPerMonth: 3.5,
  },
  optimistic: {
    label: "Optimistic",
    detail: "Higher scoring rate and availability",
    goalsPerAppearance: 0.95,
    appearanceProbability: 0.9,
    matchesPerMonth: 4.0,
  },
};

function formatDate(value: string | null | undefined, options?: Intl.DateTimeFormatOptions) {
  if (!value) return "Not reached in this scenario";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Unavailable";
  return parsed.toLocaleDateString("en-GB", options ?? { day: "numeric", month: "short", year: "numeric" });
}

function percent(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function App() {
  const [health, setHealth] = useState<"checking" | "online" | "offline">("checking");
  const [dataStatus, setDataStatus] = useState<DataStatus | null>(null);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [scenario, setScenario] = useState<Scenario>("base");
  const [currentGoals, setCurrentGoals] = useState(943);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const config = scenarios[scenario];
  const remaining = Math.max(0, 1000 - currentGoals);

  const loadReferenceData = useCallback(async () => {
    try {
      const [healthResult, statusResult, fixtureResult] = await Promise.all([
        getHealth(),
        getDataStatus(),
        getFixtures(),
      ]);
      setHealth(healthResult.status === "ok" ? "online" : "offline");
      setDataStatus(statusResult);
      setFixtures(fixtureResult.fixtures ?? []);
      setCurrentGoals(statusResult.starting_goal_total.default);
      setError(null);
    } catch (err) {
      setHealth("offline");
      setError(err instanceof Error ? err.message : "Unable to connect to the forecast API.");
    }
  }, []);

  const runForecast = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getForecast({
        current_goals: currentGoals,
        target_goals: 1000,
        goals_per_appearance: config.goalsPerAppearance,
        appearance_probability: config.appearanceProbability,
        projected_matches_per_month: config.matchesPerMonth,
        simulations: 20000,
        end_date: "2030-12-31",
        seed: 42,
      });
      setForecast(result);
      setLastUpdated(new Date().toISOString());
      setHealth("online");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Forecast request failed.");
    } finally {
      setLoading(false);
    }
  }, [config, currentGoals]);

  useEffect(() => {
    void loadReferenceData();
  }, [loadReferenceData]);

  useEffect(() => {
    if (health === "online" && dataStatus) void runForecast();
  }, [health, dataStatus, runForecast]);

  const probabilityData = useMemo(() => {
    if (!forecast) return [];
    return Object.entries(forecast.summary.probability_by_year_end).map(([year, value]) => ({
      year,
      probability: Number((value * 100).toFixed(1)),
    }));
  }, [forecast]);

  const nextFixtures = useMemo(() => fixtures.slice(0, 5), [fixtures]);
  const baselineVerified = dataStatus?.starting_goal_total.verified ?? false;

  return (
    <main className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="topbar">
        <a className="brand-lockup" href="#top" aria-label="Messi 1000 home">
          <span className="brand-mark"><CircleDot size={19} strokeWidth={1.8} /></span>
          <span className="brand-name">M1000<span>.</span></span>
        </a>
        <nav className="top-nav" aria-label="Main navigation">
          <a className="active" href="#story">The story</a>
          <a href="#forecast">Forecast</a>
          <a href="#fixtures">Fixtures</a>
        </nav>
        <div className="topbar-right">
          <span className={`api-state ${health}`}><span />{health === "online" ? "API live" : health === "checking" ? "Connecting" : "API offline"}</span>
          <span className="season-label">2026 / 30</span>
        </div>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-line" />THE ROAD TO FOUR DIGITS</div>
          <h1>One thousand.<br /><em>One career.</em></h1>
          <p className="hero-description">A live analytical view of Lionel Messi’s pursuit of 1,000 official senior career goals. Every projection is an assumption until the match data says otherwise.</p>
          <div className="hero-actions">
            <a className="button button-primary" href="#forecast">Explore the forecast <ArrowUpRight size={16} /></a>
            <a className="button button-quiet" href="#fixtures">Upcoming fixtures <ChevronRight size={16} /></a>
          </div>
          <div className="hero-footnote"><ShieldAlert size={14} /> Working baseline only. Career total has not been independently verified.</div>
        </div>
        <div className="hero-visual hero-visual-goat" aria-label="Lionel Messi surrounded by Ballon d'Or trophies">
          <img
            className="hero-goat-image"
            src="/images/messi-ballon-dor-goat.webp"
            alt="Lionel Messi at an awards stage, surrounded by golden Ballon d'Or trophies."
          />
          <div className="hero-goat-scrim" />
          <div className="hero-visual-caption"><span>A LEGACY IN GOLD</span><strong>1,000 <small>GOALS</small></strong></div>
          <div className="hero-visual-index">NO. 10 <span> / </span> THE STANDARD</div>
        </div>
      </section>

      <section className="story-section" id="story" aria-label="The story behind the numbers">
        <div className="story-intro">
          <div>
            <div className="eyebrow"><span className="eyebrow-line" />BEFORE THE NUMBER, THERE WAS THE MAGIC</div>
            <p>Some careers are measured in goals. A few are remembered in moments.</p>
          </div>
          <span className="story-index">NO. 10 / A CAREER IN MOTION</span>
        </div>

        <figure className="story-banner">
          <img src="/images/stadium-atmosphere.webp" alt="A packed Argentina stadium under the lights, with Messi on the pitch and supporters filling the stands." />
          <div className="story-banner-shade" />
          <div className="story-banner-copy">
            <span className="story-kicker">THE GOAT / THE LONG VIEW</span>
            <h2>THE <em>GOAT.</em></h2>
            <p>The number is the destination. The moments are the reason we follow.</p>
            <a href="#overview" className="story-text-link">Follow the numbers <ArrowUpRight size={15} /></a>
          </div>
          <figcaption className="story-banner-caption">A stadium full of stories. One number still left to chase.</figcaption>
        </figure>

        <div className="story-gallery">
          <figure className="story-photo-card story-photo-argentina">
            <img
              src="https://upload.wikimedia.org/wikipedia/commons/c/ce/Lionel-Messi-Argentina-2022-FIFA-World-Cup.jpg"
              alt="Lionel Messi wearing Argentina's number 10 shirt during the 2022 FIFA World Cup."
              loading="lazy"
              referrerPolicy="no-referrer"
            />
            <div className="story-photo-shade" />
            <div className="story-photo-copy">
              <span>02 / ARGENTINA · 2022</span>
              <h3>THE<br /><em>MAGICIAN.</em></h3>
              <p>A touch, a pause, a pass nobody else saw. The game always seemed to open up for him.</p>
            </div>
            <figcaption>Photo: Hossein Zohrevand / Tasnim News Agency · CC BY 4.0</figcaption>
          </figure>

          <figure className="story-photo-card story-photo-miami">
            <img
              src="https://upload.wikimedia.org/wikipedia/commons/4/42/Lionel_Messi_NE_Revolution_Inter_Miami_7.9.25-165.jpg"
              alt="Lionel Messi in Inter Miami's pink kit during a 2025 Major League Soccer match."
              loading="lazy"
              referrerPolicy="no-referrer"
            />
            <div className="story-photo-shade" />
            <div className="story-photo-copy">
              <span>03 / INTER MIAMI · 2025</span>
              <h3>STILL<br /><em>MAGIC.</em></h3>
              <p>A new shirt. A different chapter. The same instinct to make something happen.</p>
            </div>
            <figcaption>Photo: Bryan Berlin / Wikimedia Commons · CC BY-SA 4.0</figcaption>
          </figure>
        </div>
      </section>

      {error && (
        <div className="connection-alert" role="alert">
          <Info size={17} />
          <div><strong>Live data unavailable</strong><span>{error}</span></div>
          <button className="text-button" onClick={() => void loadReferenceData()}>Retry</button>
        </div>
      )}

      <section className="section-block" id="overview">
        <div className="section-heading">
          <div><div className="eyebrow">01 / CAREER SNAPSHOT</div><h2>The numbers behind the chase.</h2></div>
          <div className="section-meta">DATA STATUS <span className={baselineVerified ? "status-good" : "status-warn"}>{baselineVerified ? "VERIFIED" : "UNVERIFIED BASELINE"}</span></div>
        </div>
        <div className="stat-grid">
          <article className="stat-card stat-featured">
            <div className="stat-top"><span>WORKING GOAL TOTAL</span><Trophy size={18} /></div>
            <div className="stat-value">{currentGoals.toLocaleString("en-US")}<sup>*</sup></div>
            <div className="stat-bottom"><span className="stat-tag warning-tag">NOT VERIFIED</span><span>Editable starting point</span></div>
          </article>
          <article className="stat-card">
            <div className="stat-top"><span>TO THE MILESTONE</span><Crosshair size={18} /></div>
            <div className="stat-value">{remaining.toLocaleString("en-US")}</div>
            <div className="stat-bottom"><span>Goals remaining</span><span className="muted-inline">Target: 1,000</span></div>
          </article>
          <article className="stat-card">
            <div className="stat-top"><span>FORECAST MEDIAN</span><CalendarDays size={18} /></div>
            <div className="stat-value stat-date">{formatDate(forecast?.summary.median_date, { day: "numeric", month: "short", year: "numeric" })}</div>
            <div className="stat-bottom"><span>{config.label} projection</span><span className="muted-inline">Not a guarantee</span></div>
          </article>
          <article className="stat-card">
            <div className="stat-top"><span>CHANCE BY HORIZON</span><Gauge size={18} /></div>
            <div className="stat-value">{forecast ? percent(forecast.summary.probability_reached_by_horizon) : "—"}</div>
            <div className="stat-bottom"><span>By 31 Dec 2030</span><span className="muted-inline">20k simulations</span></div>
          </article>
        </div>
        <div className="baseline-note"><Info size={15} /><span>* The default starting total comes from a working baseline in the backend. It is deliberately labelled unverified; edit it below when a consistent, sourced total is established.</span></div>
      </section>

      <section className="section-block forecast-section" id="forecast">
        <div className="section-heading">
          <div><div className="eyebrow">02 / PROJECTION LAB</div><h2>Model the road ahead.</h2></div>
          <div className="section-meta"><span className="live-dot" /> MONTE CARLO / POISSON BASELINE</div>
        </div>
        <div className="forecast-layout">
          <div className="forecast-controls panel">
            <div className="panel-title"><div><span className="panel-kicker">SCENARIO BUILDER</span><h3>Set the assumptions.</h3></div><Sparkles size={20} /></div>
            <div className="scenario-tabs" role="group" aria-label="Forecast scenario">
              {(Object.keys(scenarios) as Scenario[]).map((key) => (
                <button key={key} className={scenario === key ? "scenario-tab selected" : "scenario-tab"} onClick={() => setScenario(key)} aria-pressed={scenario === key}>{scenarios[key].label}</button>
              ))}
            </div>
            <p className="scenario-description">{config.detail}. Each scenario changes the simulation inputs, not Messi’s real-world performance.</p>
            <label className="field-label" htmlFor="current-goals">Starting goal total <span>EDITABLE</span></label>
            <div className="number-field"><input id="current-goals" type="number" min={0} max={1500} value={currentGoals} onChange={(event) => setCurrentGoals(Math.max(0, Math.min(1500, Number(event.target.value))))} /><span>GOALS</span></div>
            <div className="assumption-list">
              <div><span>Goals per appearance</span><strong>{config.goalsPerAppearance.toFixed(2)}</strong></div>
              <div><span>Appearance probability</span><strong>{Math.round(config.appearanceProbability * 100)}%</strong></div>
              <div><span>Projected matches / month</span><strong>{config.matchesPerMonth.toFixed(1)}</strong></div>
              <div><span>Simulation runs</span><strong>20,000</strong></div>
            </div>
            <button className="button button-primary run-button" onClick={() => void runForecast()} disabled={loading || health !== "online"}>
              {loading ? <><RefreshCw className="spin" size={16} /> Running simulation</> : <><Zap size={16} /> Run forecast <ArrowUpRight size={16} /></>}
            </button>
            <p className="control-disclaimer">A configurable baseline model, not a trained machine-learning system.</p>
          </div>

          <div className="forecast-results">
            <div className="chart-panel panel">
              <div className="panel-title chart-title"><div><span className="panel-kicker">MILESTONE PROBABILITY</span><h3>Probability by year-end.</h3></div><span className="chart-unit">CHANCE %</span></div>
              {probabilityData.length ? (
                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={probabilityData} margin={{ top: 12, right: 8, left: -18, bottom: 0 }}>
                      <defs><linearGradient id="probabilityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#C6A15A" stopOpacity={0.22} /><stop offset="95%" stopColor="#C6A15A" stopOpacity={0.01} /></linearGradient></defs>
                      <CartesianGrid stroke="#282b2b" vertical={false} strokeDasharray="3 6" />
                      <XAxis dataKey="year" tick={{ fill: "#858b88", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={{ fill: "#858b88", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(value: number) => `${value}%`} />
                      <Tooltip contentStyle={{ background: "#171a19", border: "1px solid #343a34", borderRadius: 10, color: "#f1f3ed" }} formatter={(value) => [`${Number(value).toFixed(1)}%`, "Probability"]} labelStyle={{ color: "#a6aca7" }} />
                      <Area type="monotone" dataKey="probability" stroke="#C6A15A" strokeWidth={2.5} fill="url(#probabilityFill)" dot={{ r: 3, fill: "#C6A15A", stroke: "#111111", strokeWidth: 2 }} activeDot={{ r: 5, fill: "#C6A15A", stroke: "#111111", strokeWidth: 2 }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : <div className="chart-empty"><Activity size={22} /><span>{health === "online" ? "Run a forecast to generate the probability curve." : "Waiting for the forecast API connection."}</span></div>}
              <div className="chart-footer"><span><i className="legend-line" /> Selected scenario</span><span>Horizon: 31 Dec 2030</span></div>
            </div>
            <div className="date-grid">
              <article className="date-card"><div className="date-card-label"><ArrowDownRight size={15} /> P10 / EARLIER</div><strong>{formatDate(forecast?.summary.p10_date)}</strong><span>10th percentile date</span></article>
              <article className="date-card date-card-highlight"><div className="date-card-label"><Crosshair size={15} /> MEDIAN / CENTRAL</div><strong>{formatDate(forecast?.summary.median_date)}</strong><span>50th percentile date</span></article>
              <article className="date-card"><div className="date-card-label"><ArrowUpRight size={15} /> P90 / LATER</div><strong>{formatDate(forecast?.summary.p90_date)}</strong><span>90th percentile date</span></article>
            </div>
          </div>
        </div>
        <div className="model-warning"><ShieldAlert size={17} /><div><strong>Read the model, not just the date.</strong><span>{forecast?.data_warning ?? "Forecast outputs depend on the starting total, scoring rate, availability and synthetic future fixture cadence. Historical match-level data has not yet been imported."}</span></div></div>
      </section>

      <section className="section-block fixtures-section" id="fixtures">
        <div className="section-heading">
          <div><div className="eyebrow">03 / MATCH CALENDAR</div><h2>The next dates on the calendar.</h2></div>
          <a className="inline-link" href={API_DOCS_URL} target="_blank" rel="noreferrer">API documentation <ExternalLink size={14} /></a>
        </div>
        <div className="fixtures-panel panel">
          <div className="fixtures-header"><span>DATE</span><span>FIXTURE</span><span>COMPETITION</span><span>STATUS</span></div>
          {nextFixtures.length ? nextFixtures.map((fixture, index) => (
            <div className="fixture-row" key={`${fixture.date}-${fixture.opponent}`}>
              <div className="fixture-date"><span>{new Date(`${fixture.date}T12:00:00`).toLocaleDateString("en-GB", { day: "2-digit" })}</span><small>{new Date(`${fixture.date}T12:00:00`).toLocaleDateString("en-GB", { month: "short", year: "2-digit" })}</small></div>
              <div className="fixture-opponent"><span className="fixture-index">{String(index + 1).padStart(2, "0")}</span><div><strong>{fixture.team || "Inter Miami CF"}</strong><small>vs {fixture.opponent}</small></div></div>
              <div className="fixture-competition">{fixture.competition}</div>
              <div><span className="confirmed-pill"><CheckCircle2 size={12} /> {fixture.fixture_type ?? "Confirmed"}</span></div>
            </div>
          )) : <div className="fixtures-empty"><CalendarDays size={21} /><span>Fixture data will appear here when the API is connected.</span></div>}
          <div className="fixtures-foot"><span><CheckCircle2 size={13} /> {dataStatus?.fixtures.count ?? 0} published fixture records available</span><span>Source URLs included in API data</span></div>
        </div>
      </section>

      <section className="section-block integrity-section">
        <div className="section-heading">
          <div><div className="eyebrow">04 / DATA INTEGRITY</div><h2>Trust is part of the product.</h2></div>
          <div className="section-meta">SOURCE COVERAGE</div>
        </div>
        <div className="integrity-grid">
          <article className="integrity-card panel"><div className="integrity-icon"><ShieldAlert size={18} /></div><div><span className="panel-kicker">HISTORICAL MATCH ARCHIVE</span><strong>{dataStatus?.historical_matches.count ?? 0} <small>records</small></strong><p>{dataStatus?.historical_matches.available ? `${dataStatus.historical_matches.rows_with_source_url} records include source URLs.` : "No verified match-level history has been imported. No records are fabricated to fill the gap."}</p></div></article>
          <article className="integrity-card panel"><div className="integrity-icon"><CheckCircle2 size={18} /></div><div><span className="panel-kicker">FIXTURE SOURCE COVERAGE</span><strong>{dataStatus ? `${Math.round(dataStatus.fixtures.source_coverage * 100)}%` : "—"}</strong><p>{dataStatus?.fixtures.rows_with_source_url ?? 0} of {dataStatus?.fixtures.count ?? 0} fixture rows carry a source URL.</p></div></article>
          <article className="integrity-card panel"><div className="integrity-icon"><Gauge size={18} /></div><div><span className="panel-kicker">FORECAST ENGINE</span><strong>Monte Carlo</strong><p>Poisson-based baseline simulation. It is configurable, reproducible and not a trained ML model.</p></div></article>
        </div>
      </section>

      <footer className="footer">
        <a className="brand-lockup" href="#top"><span className="brand-mark"><CircleDot size={17} /></span><span className="brand-name">M1000<span>.</span></span></a>
        <span>AN ANALYTICAL PROJECT / NOT AN OFFICIAL MESSI OR INTER MIAMI PRODUCT</span>
        <span className="footer-time"><Clock3 size={13} /> {lastUpdated ? `Updated ${formatDate(lastUpdated, { hour: "2-digit", minute: "2-digit" })}` : "Awaiting live data"}</span>
      </footer>
    </main>
  );
}

export default App;
