"""
pages/1_Standings.py
NFL Standings — AFC and NFC by division
"""

import json
from pathlib import Path
import streamlit as st
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"

st.set_page_config(page_title="NFL Standings", page_icon="📊", layout="wide")

def load_json(filename):
    path = DATA_DIR / filename
    return json.loads(path.read_text()) if path.exists() else None

standings = load_json("standings.json")

with st.sidebar:
    st.title("🏈 NFL Stats")
    st.caption("Data via ESPN · No API key needed")

st.title("📊 NFL Standings")

if not standings:
    st.warning("No standings data yet. Run `python fetch_stats.py standings`.")
    st.stop()

updated = standings.get("fetched_at", "")[:16].replace("T", " ")
st.caption(f"Updated {updated} UTC")

CLINCH_LABELS = {
    "x": "x – clinched division",
    "y": "y – clinched first seed",
    "z": "z – clinched home field",
    "w": "w – clinched playoff berth",
}

tab_afc, tab_nfc = st.tabs(["AFC", "NFC"])

def render_conf(conf_data, tab):
    with tab:
        for div in conf_data["divisions"]:
            st.subheader(div["name"])
            rows = []
            for t in div["teams"]:
                diff = t["points_for"] - t["points_against"]
                clinch = t.get("clinched") or ""
                name = f"{clinch + ' ' if clinch else ''}{t['name']}"
                rows.append({
                    "Team": name,
                    "W": t["wins"],
                    "L": t["losses"],
                    "T": t["ties"],
                    "PCT": round(t["pct"], 3),
                    "PF": t["points_for"],
                    "PA": t["points_against"],
                    "DIFF": diff,
                    "Streak": t.get("streak") or "—",
                })
            df = pd.DataFrame(rows)

            def color_diff(val):
                if val > 0:
                    return "color: #1a6e2e; font-weight: 600"
                elif val < 0:
                    return "color: #b91c1c; font-weight: 600"
                return ""

            styled = (
                df.style
                .applymap(color_diff, subset=["DIFF"])
                .format({"PCT": "{:.3f}", "DIFF": "{:+d}"})
                .hide(axis="index")
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)

# find AFC and NFC
afc = next((c for c in standings["conferences"] if "AFC" in c.get("abbreviation", c["name"])), None)
nfc = next((c for c in standings["conferences"] if "NFC" in c.get("abbreviation", c["name"])), None)

if afc:
    render_conf(afc, tab_afc)
if nfc:
    render_conf(nfc, tab_nfc)

st.divider()
st.caption("x = division · y = first seed · z = home field · w = playoff berth")
