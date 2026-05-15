# 🏈 NFL Stats Tracker — Streamlit Edition

A Python app that fetches NFL scores and standings from the **free ESPN public API** (no key needed), displays them in Streamlit, and auto-updates weekly via GitHub Actions.

**Live at**: `https://your-app-name.streamlit.app`

---

## Pages

| Page | What it shows |
|---|---|
| 🏠 Home | Weekly scoreboard — all games, scores, winner highlighted |
| 📊 Standings | AFC/NFC standings by division with points and streak |
| 🏟️ Team Schedule | Full season game log for any team |

---

## Quick start (local)

```bash
git clone https://github.com/YOUR_USERNAME/nfl-stats.git
cd nfl-stats

# Fetch initial data (uses only Python stdlib — no pip needed for this step)
python fetch_stats.py current       # current week + standings
python fetch_stats.py all --season 2025   # all 18 weeks

# Run Streamlit
pip install -r requirements.txt
streamlit run Home.py
```

### fetch_stats.py commands

| Command | What it does |
|---|---|
| `python fetch_stats.py current` | Current week scores + standings + index |
| `python fetch_stats.py week 12` | Week 12, current season |
| `python fetch_stats.py week 12 --season 2024` | Week 12, 2024 season |
| `python fetch_stats.py all --season 2025` | All 18 regular season weeks |
| `python fetch_stats.py standings` | Standings only |
| `python fetch_stats.py team NE` | New England full schedule |
| `python fetch_stats.py index` | Rebuild week index from local files |

---

## Deploy to Streamlit Community Cloud (free)

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_USERNAME/nfl-stats.git
git push -u origin main
```

### 2. Connect Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **New app**
4. Select your repo, branch `main`, main file `Home.py`
5. Click **Deploy** — done

Streamlit Cloud automatically redeploys whenever you push to `main`. Since GitHub Actions commits new data every week, your live app updates automatically with zero manual work.

### 3. Enable GitHub Actions to push

Repo → **Settings → Actions → General → Workflow permissions** → **Read and write permissions**

---

## How auto-updates work

```
Every Tuesday 6 AM UTC
    │
    ▼
GitHub Actions runs fetch_stats.py current
    │
    ▼
New JSON files committed to data/
    │
    ▼
Streamlit Cloud detects push → redeploys app
    │
    ▼
Users see updated scores automatically
```

You can also trigger a manual update anytime:
**Actions tab → Update NFL Stats → Run workflow**

---

## Project structure

```
nfl-stats/
├── Home.py                         # Streamlit main page (scoreboard)
├── pages/
│   ├── 1_Standings.py              # NFL standings
│   └── 2_Team_Schedule.py          # Per-team game log
├── fetch_stats.py                  # ESPN API fetcher (stdlib only)
├── requirements.txt                # streamlit + pandas
├── .gitignore
├── data/                           # Auto-populated JSON (committed to repo)
│   ├── index.json
│   ├── standings.json
│   ├── week_2025_01.json
│   └── ...
└── .github/workflows/
    └── update_stats.yml            # Weekly cron job
```

---

## Extending

- **Game detail / box score**: ESPN has play-by-play at `/apis/site/v2/sports/football/nfl/summary?event=GAME_ID` — add a `3_Game_Detail.py` page
- **Charts**: add `plotly` or `altair` to requirements.txt and plot scoring trends
- **More teams**: `python fetch_stats.py team DAL && python fetch_stats.py team SF` etc.
- **Historical seasons**: `python fetch_stats.py all --season 2023`
