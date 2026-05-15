"""
pages/2_Team_Schedule.py
Per-team game log with defensive stats breakdown + team logo in header.
"""

import json
from pathlib import Path
import streamlit as st
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"

st.set_page_config(page_title="Team Stats", page_icon="🏟️", layout="wide")


def load_json(filename):
    path = DATA_DIR / filename
    return json.loads(path.read_text()) if path.exists() else None


LOGO_URL = "https://a.espncdn.com/i/teamlogos/nfl/500/{abbr}.png"

def logo(abbr: str) -> str:
    return LOGO_URL.format(abbr=abbr.lower())


# ── sidebar ───────────────────────────────────────────────────────────────────

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
        st.warning("No team data yet.\n\nIn Terminal run:\n```\npython3 fetch_stats.py team NE\n```")
        st.stop()

# ── load data ─────────────────────────────────────────────────────────────────

if not season:
    st.info("Select a team in the sidebar.")
    st.stop()

schedule = load_json(f"schedule_{team_abbr.lower()}_{season}.json")
if not schedule:
    st.warning(f"No data for {team_abbr} {season}.")
    st.stop()

games = schedule.get("games", [])
completed = [g for g in games if g["completed"]]

wins = sum(
    1 for g in completed
    if (g["home_abbr"] == team_abbr and g["home_winner"])
    or (g["away_abbr"] == team_abbr and g["away_winner"])
)
losses = len(completed) - wins

# ── header with team logo ─────────────────────────────────────────────────────

col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.image(logo(team_abbr), width=72)
with col_title:
    st.title(f"{team_abbr} · {season} Defensive Stats")
    st.caption("Stats shown are yards/points *allowed* to the opponent each game")

c1, c2, c3 = st.columns(3)
c1.metric("Record", f"{wins}–{losses}")
c2.metric("Games Played", len(completed))
c3.metric("Remaining", len(games) - len(completed))

st.divider()

# ── build rows ────────────────────────────────────────────────────────────────

def build_rows(game_list):
    rows = []
    for g in game_list:
        if not g["completed"]:
            continue
        is_home = g.get("is_home", g["home_abbr"] == team_abbr)
        opp = g["away_abbr"] if is_home else g["home_abbr"]
        team_score = g["home_score"] if is_home else g["away_score"]
        opp_score  = g["away_score"] if is_home else g["home_score"]
        won = g["home_winner"] if is_home else g["away_winner"]
        d = g.get("defensive_stats", {})

        rows.append({
            "Wk":               g.get("week") or "—",
            "Date":             g["date"][:10],
            "H/A":              "vs" if is_home else "@",
            "Opponent":         opp,
            "Score":            f"{team_score}–{opp_score}",
            "W/L":              "W" if won else "L",
            "Pts Allowed":      d.get("points_allowed"),
            "Pass Yds Allowed": d.get("pass_yards_allowed"),
            "Rush Yds Allowed": d.get("rush_yards_allowed"),
            "Total Yds Allowed":d.get("total_yards_allowed"),
            "Opp Comp%":        d.get("opp_comp_pct"),
            "Pass Line":        d.get("opp_passing_line", ""),
            "INTs":             d.get("interceptions"),
            "3rd Down":         d.get("third_down_eff", ""),
            "Possession":       d.get("possession_time", ""),
        })
    return rows


def avg(vals):
    v = [x for x in vals if x is not None]
    return round(sum(v) / len(v), 1) if v else None


def style_table(df):
    def color_wl(val):
        if val == "W": return "color: #1a6e2e; font-weight: 700"
        if val == "L": return "color: #b91c1c; font-weight: 700"
        return ""

    def color_pts(val):
        try:
            v = float(val)
            if v <= 17: return "color: #1a6e2e; font-weight: 600"
            if v >= 28: return "color: #b91c1c; font-weight: 600"
        except: pass
        return ""

    def color_pass(val):
        try:
            v = float(val)
            if v < 200: return "color: #1a6e2e"
            if v > 300: return "color: #b91c1c"
        except: pass
        return ""

    def color_rush(val):
        try:
            v = float(val)
            if v < 90:  return "color: #1a6e2e"
            if v > 140: return "color: #b91c1c"
        except: pass
        return ""

    def color_int(val):
        try:
            v = float(val)
            if v >= 2: return "color: #1a6e2e; font-weight: 600"
            if v == 0: return "color: #b91c1c"
        except: pass
        return ""

    styled = df.style
    for col, fn in [
        ("W/L",              color_wl),
        ("Pts Allowed",      color_pts),
        ("Pass Yds Allowed", color_pass),
        ("Rush Yds Allowed", color_rush),
        ("INTs",             color_int),
    ]:
        if col in df.columns:
            styled = styled.map(fn, subset=[col])

    return styled.format(na_rep="—", precision=1).hide(axis="index")


def show_averages(rows):
    if not rows:
        return
    cols = st.columns(6)
    cols[0].metric("Pts Allowed",  avg([r["Pts Allowed"]       for r in rows]))
    cols[1].metric("Pass Yds",     avg([r["Pass Yds Allowed"]  for r in rows]))
    cols[2].metric("Rush Yds",     avg([r["Rush Yds Allowed"]  for r in rows]))
    cols[3].metric("Total Yds",    avg([r["Total Yds Allowed"] for r in rows]))
    cols[4].metric("Opp Comp%",    avg([r["Opp Comp%"]         for r in rows]))
    cols[5].metric("INTs/game",    avg([r["INTs"]              for r in rows]))


all_rows  = build_rows(games)
home_rows = build_rows([g for g in games if g.get("is_home", g["home_abbr"] == team_abbr)])
away_rows = build_rows([g for g in games if not g.get("is_home", g["home_abbr"] == team_abbr)])

# ── tabs ──────────────────────────────────────────────────────────────────────

tab_all, tab_home, tab_away, tab_avgs = st.tabs([
    "📋 Game by Game", "🏠 Home Games", "✈️ Away Games", "📊 Season Averages"
])

with tab_all:
    if all_rows:
        st.dataframe(style_table(pd.DataFrame(all_rows)), use_container_width=True, hide_index=True)
        st.divider()
        show_averages(all_rows)
    else:
        st.info("No completed games with stats yet.")

with tab_home:
    if home_rows:
        st.dataframe(style_table(pd.DataFrame(home_rows)), use_container_width=True, hide_index=True)
        st.divider()
        show_averages(home_rows)
    else:
        st.info("No completed home games yet.")

with tab_away:
    if away_rows:
        st.dataframe(style_table(pd.DataFrame(away_rows)), use_container_width=True, hide_index=True)
        st.divider()
        show_averages(away_rows)
    else:
        st.info("No completed away games yet.")

with tab_avgs:
    st.subheader(f"{team_abbr} · Full season defensive averages")
    if all_rows:
        stat_cols = [
            ("Pts Allowed",       "Points allowed/game"),
            ("Pass Yds Allowed",  "Pass yards allowed/game"),
            ("Rush Yds Allowed",  "Rush yards allowed/game"),
            ("Total Yds Allowed", "Total yards allowed/game"),
            ("Opp Comp%",         "Opponent completion %"),
            ("INTs",              "Interceptions forced/game"),
        ]
        avgs = []
        for col, label in stat_cols:
            avgs.append({
                "Stat":    label,
                "Overall": avg([r[col] for r in all_rows  if r.get(col) is not None]),
                "Home":    avg([r[col] for r in home_rows if r.get(col) is not None]),
                "Away":    avg([r[col] for r in away_rows if r.get(col) is not None]),
            })
        df_avg = pd.DataFrame(avgs)
        st.dataframe(df_avg.style.format(na_rep="—", precision=1).hide(axis="index"),
                     use_container_width=True, hide_index=True)
    else:
        st.info("No stats to average yet.")

fetched = schedule.get("fetched_at", "")[:16].replace("T", " ")
st.caption(f"Data fetched: {fetched} UTC · Green = good defense · Red = poor defense")
