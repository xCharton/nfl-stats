"""
fetch_stats.py
Pulls NFL data using sports-skills CLI (no ESPN 403 issues).
Run manually or via GitHub Actions cron.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"


def save(name: str, data: dict):
    path = DATA_DIR / name
    path.write_text(json.dumps(data, indent=2))
    print(f"  saved {path}")


def cli(cmd: list, timeout: int = 60) -> dict:
    """Run a sports-skills CLI command and return parsed JSON."""
    result = subprocess.run(
        ["sports-skills", "nfl"] + cmd,
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(f"sports-skills error: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    return data.get("data", data)


def fetch_direct(url: str) -> dict:
    """Direct HTTP fetch for box scores (still needed for detailed stats)."""
    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://www.espn.com",
        "Referer": "https://www.espn.com/nfl/",
    }
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise


def fetch_scoreboard(week: int = None, season: int = None):
    """Fetch scores for a given week using sports-skills CLI."""
    cmd = ["get_scoreboard"]
    if week:
        cmd += ["--week", str(week)]
    if season:
        cmd += ["--season", str(season)]

    print(f"Fetching scoreboard (week={week}, season={season})...")
    raw = cli(cmd)

    games = []
    season_year = raw.get("season", {}).get("year", season or datetime.now().year)
    week_num = raw.get("week", {}).get("number", week)

    for event in raw.get("events", []):
        competitors = event.get("competitors", [])
        home = next((c for c in competitors if c.get("home_away") == "home"), {})
        away = next((c for c in competitors if c.get("home_away") == "away"), {})

        completed = event.get("status") in ("closed", "complete", "final")
        status_name = event.get("status_detail", event.get("status", ""))

        games.append({
            "id": event["id"],
            "name": event.get("name", ""),
            "short_name": event.get("short_name", ""),
            "date": event.get("start_time", ""),
            "status": status_name,
            "completed": completed,
            "home": {
                "id": home.get("team", {}).get("id", ""),
                "abbr": home.get("team", {}).get("abbreviation", ""),
                "name": home.get("team", {}).get("name", ""),
                "score": int(home.get("score", 0) or 0),
                "winner": home.get("winner", False),
                "logo": home.get("team", {}).get("logo", ""),
            },
            "away": {
                "id": away.get("team", {}).get("id", ""),
                "abbr": away.get("team", {}).get("abbreviation", ""),
                "name": away.get("team", {}).get("name", ""),
                "score": int(away.get("score", 0) or 0),
                "winner": away.get("winner", False),
                "logo": away.get("team", {}).get("logo", ""),
            },
            "venue": event.get("venue", {}).get("name", ""),
        })

    result = {
        "season": season_year,
        "week": week_num,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "games": games,
    }
    fname = f"week_{season_year}_{str(week_num).zfill(2)}.json"
    save(fname, result)
    return result


def fetch_standings(season: int = None):
    """Fetch standings using sports-skills CLI."""
    cmd = ["get_standings"]
    if season:
        cmd += ["--season", str(season)]

    print("Fetching standings...")
    raw = cli(cmd)

    # Group by conference and division
    conf_map = {}
    for entry in raw.get("groups", []):
        for team_entry in entry.get("entries", []):
            conf_name = entry.get("conference", "")
            div_name = team_entry.get("division", entry.get("division", ""))

            if conf_name not in conf_map:
                conf_map[conf_name] = {}
            if div_name not in conf_map[conf_name]:
                conf_map[conf_name][div_name] = []

            conf_map[conf_name][div_name].append({
                "id": team_entry.get("team", {}).get("id"),
                "name": team_entry.get("team", {}).get("name"),
                "abbr": team_entry.get("team", {}).get("abbreviation"),
                "logo": team_entry.get("team", {}).get("logo", ""),
                "wins": int(team_entry.get("wins", 0)),
                "losses": int(team_entry.get("losses", 0)),
                "ties": int(team_entry.get("ties", 0)),
                "pct": float(team_entry.get("win_pct", 0)),
                "points_for": int(team_entry.get("points_for", 0)),
                "points_against": int(team_entry.get("points_against", 0)),
                "streak": team_entry.get("streak", ""),
                "clinched": team_entry.get("clinch", ""),
            })

    conferences = []
    for conf_name, divisions in conf_map.items():
        abbr = "AFC" if "American" in conf_name else "NFC"
        conf = {"name": conf_name, "abbreviation": abbr, "divisions": []}
        for div_name, teams in sorted(divisions.items()):
            conf["divisions"].append({
                "name": div_name,
                "teams": sorted(teams, key=lambda t: (-t["wins"], t["losses"]))
            })
        conferences.append(conf)

    result = {"fetched_at": datetime.utcnow().isoformat() + "Z", "conferences": conferences}
    save("standings.json", result)
    return result


def fetch_box_score(game_id: str, opponent_abbr: str) -> dict:
    """Fetch box score stats via direct ESPN request (still needed for detailed stats)."""
    url = f"{BASE}/summary?event={game_id}"
    try:
        raw = fetch_direct(url)
    except Exception as e:
        print(f"    box score error: {e}")
        return {}

    teams_info = {}
    for team_data in raw.get("boxscore", {}).get("teams", []):
        abbr = team_data["team"]["abbreviation"].upper()
        stats = {s["name"]: s.get("displayValue", "") for s in team_data.get("statistics", [])}
        teams_info[abbr] = stats

    opp = teams_info.get(opponent_abbr.upper(), {})

    def si(v):
        try: return int(str(v).split(".")[0])
        except: return None

    comp_line = opp.get("completionAttempts", "")
    comp_pct = None
    if "/" in comp_line:
        parts = comp_line.split("/")
        try: comp_pct = round(int(parts[0]) / int(parts[1]) * 100, 1)
        except: pass

    return {
        "pass_yards_allowed":      si(opp.get("netPassingYards")),
        "rush_yards_allowed":      si(opp.get("rushingYards")),
        "receiving_yards_allowed": si(opp.get("netPassingYards")),
        "total_yards_allowed":     si(opp.get("totalYards")),
        "opp_comp_pct":            comp_pct,
        "opp_passing_line":        comp_line,
        "interceptions":           si(opp.get("interceptions")),
        "third_down_eff":          opp.get("thirdDownEff", ""),
        "possession_time":         opp.get("possessionTime", ""),
    }


def fetch_team_schedule(team_abbr: str, season: int = None):
    """Fetch team schedule using sports-skills CLI."""
    # Get team ID first
    teams_raw = cli(["get_teams"])
    team_id = None
    for t in teams_raw.get("teams", []):
        if t.get("abbreviation", "").upper() == team_abbr.upper():
            team_id = t.get("id")
            break

    if not team_id:
        print(f"  {team_abbr}: team not found")
        return None

    year = season or datetime.now().year
    cmd = ["get_team_schedule", "--team_id", str(team_id)]
    if season:
        cmd += ["--season", str(season)]

    print(f"Fetching {team_abbr} schedule (season={year})...")
    try:
        raw = cli(cmd)
    except Exception as e:
        print(f"  {team_abbr}: {e}")
        return None

    # Load existing data to avoid re-fetching box scores
    out_path = DATA_DIR / f"schedule_{team_abbr.lower()}_{year}.json"
    existing = {}
    if out_path.exists():
        try:
            old = json.loads(out_path.read_text())
            existing = {g["id"]: g.get("defensive_stats", {}) for g in old.get("games", [])}
        except Exception:
            pass

    games = []
    for event in raw.get("events", raw.get("games", [])):
        competitors = event.get("competitors", [])
        home = next((c for c in competitors if c.get("home_away") == "home"), {})
        away = next((c for c in competitors if c.get("home_away") == "away"), {})

        home_abbr = home.get("team", {}).get("abbreviation", "").upper()
        away_abbr = away.get("team", {}).get("abbreviation", "").upper()
        is_home = home_abbr == team_abbr.upper()
        opponent_abbr = away_abbr if is_home else home_abbr

        home_score = int(home.get("score", 0) or 0)
        away_score = int(away.get("score", 0) or 0)
        completed = event.get("status") in ("closed", "complete", "final") or (home_score > 0 or away_score > 0)
        points_allowed = away_score if is_home else home_score

        game = {
            "id": event["id"],
            "week": event.get("week"),
            "date": event.get("start_time", event.get("date", "")),
            "completed": completed,
            "status": event.get("status_detail", event.get("status", "")),
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
            if event["id"] in existing and existing[event["id"]]:
                game["defensive_stats"] = existing[event["id"]]
                game["defensive_stats"]["points_allowed"] = points_allowed
            else:
                print(f"    wk {game['week']} vs {opponent_abbr} — fetching box score...")
                ds = fetch_box_score(event["id"], opponent_abbr)
                if ds:
                    ds["points_allowed"] = points_allowed
                game["defensive_stats"] = ds
                time.sleep(0.3)

        games.append(game)

    result = {
        "team": team_abbr.upper(),
        "season": year,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "games": games,
    }
    out_path.write_text(json.dumps(result, indent=2))
    print(f"  {team_abbr}: {sum(1 for g in games if g['completed'])} completed games saved")
    return result


def fetch_all_weeks(season: int = None):
    year = season or datetime.now().year
    print(f"\nFetching all weeks for {year} season...")
    for week in range(1, 19):
        try:
            fetch_scoreboard(week=week, season=year)
        except Exception as e:
            print(f"  week {week}: {e}")


def index_weeks():
    weeks = []
    for f in sorted(DATA_DIR.glob("week_*.json")):
        data = json.loads(f.read_text())
        weeks.append({
            "file": f.name,
            "season": data["season"],
            "week": data["week"],
            "game_count": len(data["games"]),
        })
    index = {"updated_at": datetime.utcnow().isoformat() + "Z", "weeks": weeks}
    save("index.json", index)
    return index


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch NFL stats")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("current", help="Fetch current week + standings")
    p_week = sub.add_parser("week", help="Fetch a specific week")
    p_week.add_argument("week", type=int)
    p_week.add_argument("--season", type=int)

    p_all = sub.add_parser("all", help="Fetch all 18 weeks")
    p_all.add_argument("--season", type=int)

    p_team = sub.add_parser("team", help="Fetch team schedule + stats")
    p_team.add_argument("abbr")
    p_team.add_argument("--season", type=int)

    sub.add_parser("standings", help="Fetch standings only")
    sub.add_parser("index", help="Rebuild week index")

    args = parser.parse_args()

    if args.cmd == "current":
        fetch_scoreboard()
        fetch_standings()
        index_weeks()
    elif args.cmd == "week":
        fetch_scoreboard(week=args.week, season=args.season)
        index_weeks()
    elif args.cmd == "all":
        fetch_all_weeks(season=args.season)
        fetch_standings()
        index_weeks()
    elif args.cmd == "team":
        fetch_team_schedule(args.abbr, season=args.season)
    elif args.cmd == "standings":
        fetch_standings()
    elif args.cmd == "index":
        index_weeks()
    else:
        parser.print_help()
