"""
Home.py — NFL Stats Tracker
Main page: weekly scoreboard
"""

import json
from pathlib import Path
from datetime import datetime
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

st.set_page_config(
    page_title="NFL Stats Tracker",
    page_icon="🏈",
    layout="wide",
)

# ── helpers ──────────────────────────────────────────────────────────────────

def load_json(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        return None
    return json.loads(path.read_text())

def get_week_index():
    idx = load_json("index.json")
    if not idx:
        return []
    return sorted(idx["weeks"], key=lambda w: (w["season"], w["week"]), reverse=True)

def get_week_data(season: int, week: int):
    return load_json(f"week_{season}_{str(week).zfill(2)}.json")

# ── sidebar: week picker ──────────────────────────────────────────────────────

all_weeks = get_week_index()

with st.sidebar:
    st.title("🏈 NFL Stats")
    st.caption("Data via ESPN · No API key needed")
    st.divider()

    if all_weeks:
        options = {f"{w['season']} · Week {w['week']}": (w["season"], w["week"]) for w in all_weeks}
        chosen_label = st.selectbox("Select week", list(options.keys()))
        chosen_season, chosen_week = options[chosen_label]
    else:
        st.warning("No data yet. Run `python fetch_stats.py current` locally, or trigger the GitHub Action.")
        st.stop()

    st.divider()

    idx = load_json("index.json")
    if idx:
        updated = idx.get("updated_at", "")[:16].replace("T", " ")
        st.caption(f"Last updated: {updated} UTC")

# ── main: game cards ──────────────────────────────────────────────────────────

week = get_week_data(chosen_season, chosen_week)

if not week:
    st.error(f"No data found for {chosen_season} Week {chosen_week}.")
    st.stop()

st.title(f"Week {week['week']} · {week['season']} Season")

games = week.get("games", [])
if not games:
    st.info("No games found for this week.")
    st.stop()

# Render games in a 3-column grid
cols_per_row = 3
for i in range(0, len(games), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, game in enumerate(games[i : i + cols_per_row]):
        with cols[j]:
            home = game["home"]
            away = game["away"]
            status = "Final" if game["completed"] else game["status"]

            # score colours
            home_color = "#D50A0A" if home["winner"] else "#888888"
            away_color = "#D50A0A" if away["winner"] else "#888888"
            home_weight = "700" if home["winner"] else "400"
            away_weight = "700" if away["winner"] else "400"

            venue = game.get("venue", "")
            venue_html = f"<span style='font-size:11px;color:#999'>{venue}</span>" if venue else ""

            card_html = f"""
            <div style="
                border:1px solid #e0e0e0;
                border-left: 4px solid {'#D50A0A' if game['completed'] else '#cccccc'};
                border-radius:10px;
                padding:14px 16px;
                margin-bottom:14px;
                background:#ffffff;
            ">
              <div style="font-size:11px;font-weight:600;text-transform:uppercase;
                          letter-spacing:.5px;color:#999;margin-bottom:10px;">
                {status} {('· ' + venue) if venue else ''}
              </div>

              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <div>
                  <span style="font-size:15px;font-weight:700;">{away['abbr']}</span>
                  <span style="font-size:12px;color:#888;margin-left:6px;">{away['name']}</span>
                </div>
                <span style="font-size:22px;font-weight:{away_weight};color:{away_color};">{away['score']}</span>
              </div>

              <hr style="border:none;border-top:1px solid #eee;margin:6px 0;">

              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <span style="font-size:15px;font-weight:700;">{home['abbr']}</span>
                  <span style="font-size:12px;color:#888;margin-left:6px;">{home['name']}</span>
                </div>
                <span style="font-size:22px;font-weight:{home_weight};color:{home_color};">{home['score']}</span>
              </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
