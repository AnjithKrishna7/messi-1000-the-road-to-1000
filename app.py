from pathlib import Path
import pandas as pd
import streamlit as st

from src.predictor import load_fixtures, build_projection_calendar, simulate_milestone, probability_by_date

BASE_DIR = Path(__file__).resolve().parent
FIXTURE_PATH = BASE_DIR / "data" / "fixtures.csv"

st.set_page_config(page_title="Messi 1000 | GOAT Predictor", page_icon="🐐", layout="wide")

st.title("🐐 MESSI 1000")
st.subheader("The GOAT Milestone Predictor")
st.caption("Fixture-aware Monte Carlo simulation. Estimate the road to 1,000 official senior goals.")

with st.sidebar:
    st.header("Simulation settings")
    current_goals = st.number_input(
        "Current career goals",
        min_value=0, max_value=1500, value=943, step=1,
        help="Editable because public sources currently disagree. Verify before publishing."
    )
    target_goals = st.number_input("Target goals", min_value=1, max_value=1600, value=1000, step=1)
    goals_rate = st.slider("Goals per appearance", 0.10, 1.50, 0.82, 0.01)
    appearance_chance = st.slider("Chance Messi appears in a fixture", 0.10, 1.00, 0.82, 0.01)
    matches_per_month = st.slider("Future projected matches per month", 1.0, 8.0, 3.5, 0.5)
    simulations = st.select_slider("Monte Carlo simulations", options=[1000, 5000, 10000, 20000, 50000], value=20000)
    forecast_end = st.selectbox("Forecast horizon", ["2028-12-31", "2029-12-31", "2030-12-31"], index=2)

st.info(
    "Source discrepancy: MessiStat listed 936 goals on 1 Nov 2026, while a Playmakerstats report "
    "syndicated by Yahoo Sports on 2 Nov 2026 reported 943. The starting total is editable. "
    "Check the match-by-match record before treating any forecast as definitive."
)

try:
    confirmed = load_fixtures(FIXTURE_PATH)
    calendar = build_projection_calendar(
        confirmed,
        end_date=forecast_end,
        projected_matches_per_month=matches_per_month,
    )
    result = simulate_milestone(
        current_goals=int(current_goals),
        target_goals=int(target_goals),
        fixtures=calendar,
        goals_per_appearance=float(goals_rate),
        appearance_probability=float(appearance_chance),
        simulations=int(simulations),
    )
except Exception as exc:
    st.error(f"Could not run the prediction: {exc}")
    st.stop()

summary = result.summary
remaining = max(0, int(target_goals) - int(current_goals))

c1, c2, c3 = st.columns(3)
c1.metric("Goals remaining", f"{remaining:,}")
c2.metric("Confirmed fixtures loaded", f"{len(confirmed):,}")
c3.metric("Simulation runs", f"{simulations:,}")

st.header("📅 Milestone forecast")
if summary["median_date"] is not None:
    p10 = summary["p10_date"].strftime("%d %b %Y")
    median = summary["median_date"].strftime("%d %b %Y")
    p90 = summary["p90_date"].strftime("%d %b %Y")
    st.metric("Median projected milestone date", median)
    st.write(f"**Central 80% simulation window (among runs that reach the target):** {p10} to {p90}")
    st.write(
        f"**Reached within selected horizon:** "
        f"{summary['probability_reached_by_horizon']:.1%} of simulations"
    )
    median_index = int(summary["median_fixture_number"]) - 1
    median_fixture = calendar.iloc[median_index]
    st.write(f"**Median fixture slot:** #{summary['median_fixture_number']} in the combined calendar")
    if median_fixture["fixture_type"] == "Confirmed":
        st.success(
            "Median predicted match: "
            + median_fixture["date"].strftime("%d %b %Y")
            + " | "
            + str(median_fixture["team"])
            + " vs "
            + str(median_fixture["opponent"])
        )
    else:
        st.write(
            "Median projected slot: "
            + median_fixture["date"].strftime("%d %b %Y")
            + " | Opponent not announced"
        )
else:
    st.warning("The target was not reached in any simulation within this forecast horizon.")

st.warning(
    "The median fixture number is not an exact official match prediction while the calendar "
    "contains projected slots. Replace those placeholders with confirmed fixtures when released."
)

st.header("Confirmed fixture data")
show_cols = ["date", "team", "opponent", "competition", "status", "notes"]
confirmed_display = confirmed[show_cols].copy()
confirmed_display["date"] = confirmed_display["date"].dt.strftime("%d %b %Y")
st.dataframe(confirmed_display, use_container_width=True, hide_index=True)

st.header("Calendar coverage")
counts = calendar["fixture_type"].value_counts()
left, right = st.columns(2)
left.metric("Confirmed fixture rows", int(counts.get("Confirmed", 0)))
right.metric("Projected placeholder slots", int(counts.get("Projected", 0)))

st.caption(
    "Projected slots are synthetic dates generated from the selected matches-per-month assumption. "
    "They are not official Inter Miami or Argentina fixtures."
)

st.header("Probability by year-end")
for year in [2026, 2027, 2028, 2029, 2030]:
    date = f"{year}-12-31"
    if pd.Timestamp(date) <= calendar["date"].max():
        chance = probability_by_date(result, date)
        st.write(f"**By {year}:** {chance:.1%}")

with st.expander("Model assumptions and source links"):
    st.markdown(
        """
        - Goals are sampled from a Poisson distribution after a simulated appearance.
        - Appearance probability is constant across fixtures in this baseline.
        - Goals-per-appearance is constant across fixtures in this baseline.
        - The model does not currently account for minutes, opponent strength, home advantage,
          injuries, penalties, tactical role or retirement.
        - Public goal totals vary by source and update timing.
        """
    )
    st.markdown("[MessiStat career data](https://www.messistat.com/en)")
    st.markdown("[Playmakerstats report via Yahoo Sports](https://sports.yahoo.com/articles/messi-reaches-30-goal-mark-114200246.html)")
    st.markdown("[Official Inter Miami 2027 schedule](https://www.intermiamicf.com/news/inter-miami-cf-s-2027-mls-sprint-season-schedule-unveiled)")

st.caption("Independent educational project. No affiliation with Lionel Messi or any football organisation.")
