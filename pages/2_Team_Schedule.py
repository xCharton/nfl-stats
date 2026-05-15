"""
pages/2_Team_Schedule.py
Per-team game log for the selected season
"""

import json
from pathlib import Path
import streamlit as st
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"

st.set_page_config(page_title="Team Schedule", page_icon="🏟️", layout="wide")

def load_json(filename):
    path = DATA_DIR / filename
    return json.loads(path.read_text()) if path.exists() else None

# Build team list from available schedule files
schedule_files = list(DATA_DIR.glob("schedule_*_*.json"))
available_teams = sorted({f.stem.split("_")[1].upper() for f in schedule_files})

with st.sidebar:
    st.title("🏈 NFL Stats")
    st.caption("Data via ESPN · No API key needed")
    st.divider()

    if available_teams:
        team_abbr = st.selectbox("Select team", available_teams)
        season_files = sorted(DATA_DIR.glob(f"schedule_{team_abbr.lower()}_*.json"), reverse=True)
        seasons = [f.stem.split("_")[-1] for f in season_files]
        season = st.selectbox("Season", seasons) if seasons else None
    else:
        st.warning("No team schedules yet.\nRun `python fetch_stats.py team NE` etc.")
        team_abbr = None
        season = None

st.title("🏟️ Team Schedule")

if not team_abbr or not season:
    st.info("Select a team in the sidebar. Fetch team data first with:\n```\npython fetch_stats.py team NE\n```")
    st.stop()

schedule = load_json(f"schedule_{team_abbr.lower()}_{season}.json")
if not schedule:
    st.warning(f"No data for {team_abbr} {season}. Run: `python fetch_stats.py team {team_abbr} --season {season}`")
    st.stop()

st.subheader(f"{team_abbr} · {season} Season")

games = schedule.get("games", [])
completed = [g for g in games if g["completed"]]
wins = sum(
    1 for g in completed
    if (g["home_abbr"] == team_abbr and g["home_winner"])
    or (g["away_abbr"] == team_abbr and g["away_winner"])
)
losses = len(completed) - wins

col1, col2, col3 = st.columns(3)
col1.metric("Record", f"{wins}–{losses}")
col2.metric("Games played", len(completed))
col3.metric("Remaining", len(games) - len(completed))

st.divider()

rows = []
for g in games:
    is_home = g["home_abbr"] == team_abbr
    opp = g["away_abbr"] if is_home else g["home_abbr"]
    team_score = g["home_score"] if is_home else g["away_score"]
    opp_score = g["away_score"] if is_home else g["home_score"]
    won = (g["home_winner"] if is_home else g["away_winner"]) if g["completed"] else None

    result = ("W" if won else "L") if g["completed"] else g.get("status", "—")
    score = f"{team_score}–{opp_score}" if g["completed"] else "—"
    location = "vs" if is_home else "@"

    rows.append({
        "Wk": g.get("week") or "—",
        "Date": g["date"][:10],
        "H/A": location,
        "Opponent": opp,
        "Score": score,
        "Result": result,
    })

df = pd.DataFrame(rows)

def style_result(val):
    if val == "W":
        return "color: #1a6e2e; font-weight: 700"
    elif val == "L":
        return "color: #b91c1c; font-weight: 700"
    return "color: #888888"

styled = df.style.applymap(style_result, subset=["Result"]).hide(axis="index")
st.dataframe(styled, use_container_width=True, hide_index=True)

fetched = schedule.get("fetched_at", "")[:16].replace("T", " ")
st.caption(f"Data fetched: {fetched} UTC")
