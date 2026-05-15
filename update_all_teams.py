"""
update_all_teams.py
Fetches schedule + box scores for all 32 NFL teams.
Run by GitHub Actions every Tuesday, or manually:
  python update_all_teams.py           # current season
  python update_all_teams.py 2026      # specific season
"""

import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

ALL_TEAMS = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB",  "HOU", "IND", "JAX", "KC",
    "LAC", "LAR", "LV",  "MIA", "MIN", "NE",  "NO",  "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF",  "TB",  "TEN", "WSH",
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "nfl-stats-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def parse_score(val):
    if isinstance(val, dict):
        val = val.get("value", val.get("displayValue", 0))
    try:
        return int(float(str(val)))
    except Exception:
        return 0


def parse_status(event):
    s = event.get("status", {})
    if "type" in s and isinstance(s["type"], dict):
        s = s["type"]
    completed = bool(s.get("completed", False))
    name = s.get("name", s.get("description", "Scheduled"))
    return completed, name


def get_team_id(team_abbr):
    raw = fetch(f"{BASE}/teams")
    for sport in raw.get("sports", []):
        for league in sport.get("leagues", []):
            for team in league.get("teams", []):
                t = team.get("team", {})
                if t.get("abbreviation", "").upper() == team_abbr.upper():
                    return t["id"]
    return None


def fetch_box_score(game_id, team_abbr, opponent_abbr):
    try:
        raw = fetch(f"{BASE}/summary?event={game_id}")
        teams_info = {}
        for td in raw.get("boxscore", {}).get("teams", []):
            abbr = td["team"]["abbreviation"].upper()
            stats = {s["name"]: s.get("displayValue", "") for s in td.get("statistics", [])}
            teams_info[abbr] = stats

        opp_stats = teams_info.get(opponent_abbr.upper(), {})

        def si(v):
            try: return int(str(v).split(".")[0])
            except: return None

        comp_line = opp_stats.get("completionAttempts", "")
        comp_pct = None
        if "/" in comp_line:
            parts = comp_line.split("/")
            try:
                comp_pct = round(int(parts[0]) / int(parts[1]) * 100, 1)
            except: pass

        return {
            "pass_yards_allowed":      si(opp_stats.get("netPassingYards")),
            "rush_yards_allowed":      si(opp_stats.get("rushingYards")),
            "receiving_yards_allowed": si(opp_stats.get("netPassingYards")),
            "total_yards_allowed":     si(opp_stats.get("totalYards")),
            "opp_comp_pct":            comp_pct,
            "opp_passing_line":        comp_line,
            "interceptions":           si(opp_stats.get("interceptions")),
            "third_down_eff":          opp_stats.get("thirdDownEff", ""),
            "possession_time":         opp_stats.get("possessionTime", ""),
        }
    except Exception as e:
        print(f"      box score error: {e}")
        return {}


def fetch_team(team_abbr, season):
    team_id = get_team_id(team_abbr)
    if not team_id:
        print(f"  {team_abbr}: team not found, skipping")
        return

    url = f"{BASE}/teams/{team_id}/schedule?season={season}"
    try:
        raw = fetch(url)
    except Exception as e:
        print(f"  {team_abbr}: schedule fetch failed — {e}")
        return

    # Load existing data so we don't re-fetch box scores we already have
    out_path = DATA_DIR / f"schedule_{team_abbr.lower()}_{season}.json"
    existing = {}
    if out_path.exists():
        try:
            old = json.loads(out_path.read_text())
            existing = {g["id"]: g.get("defensive_stats", {}) for g in old.get("games", [])}
        except Exception:
            pass

    games = []
    for event in raw.get("events", []):
        comp = event.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        home = next((t for t in competitors if t.get("homeAway") == "home"), {})
        away = next((t for t in competitors if t.get("homeAway") == "away"), {})

        completed, status_name = parse_status(event)

        home_abbr = home.get("team", {}).get("abbreviation", "").upper()
        away_abbr = away.get("team", {}).get("abbreviation", "").upper()
        is_home = home_abbr == team_abbr.upper()
        opponent_abbr = away_abbr if is_home else home_abbr

        home_score = parse_score(home.get("score", 0))
        away_score = parse_score(away.get("score", 0))

        # Fix completed flag if scores exist
        if not completed and (home_score > 0 or away_score > 0):
            completed = True

        points_allowed = away_score if is_home else home_score

        game = {
            "id": event["id"],
            "week": event.get("week", {}).get("number"),
            "date": event.get("date", ""),
            "completed": completed,
            "status": status_name,
            "is_home": is_home,
            "home_abbr": home_abbr,
            "away_abbr": away_abbr,
            "home_score": home_score,
            "away_score": away_score,
            "home_winner": home.get("winner", False),
            "away_winner": away.get("winner", False),
            "opponent": opponent_abbr,
            "defensive_stats": {},
        }

        if completed:
            # Re-use existing box score if we already have it
            if event["id"] in existing and existing[event["id"]]:
                game["defensive_stats"] = existing[event["id"]]
                game["defensive_stats"]["points_allowed"] = points_allowed
            else:
                print(f"    wk {game['week']} vs {opponent_abbr} — fetching box score...")
                ds = fetch_box_score(event["id"], team_abbr, opponent_abbr)
                if ds:
                    ds["points_allowed"] = points_allowed
                game["defensive_stats"] = ds
                time.sleep(0.3)

        games.append(game)

    result = {
        "team": team_abbr.upper(),
        "season": season,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "games": games,
    }
    out_path.write_text(json.dumps(result, indent=2))
    completed_count = sum(1 for g in games if g["completed"])
    print(f"  {team_abbr}: {completed_count} completed games saved")


def main():
    season = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else datetime.now().year
    print(f"\nUpdating all 32 teams for {season} season...\n")

    for team in ALL_TEAMS:
        print(f"{team}:")
        try:
            fetch_team(team, season)
        except Exception as e:
            print(f"  {team}: unexpected error — {e}")

    print("\nAll teams updated!")


if __name__ == "__main__":
    main()
