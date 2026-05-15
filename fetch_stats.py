"""
fetch_stats.py
Pulls NFL data from the ESPN public API and saves to data/.
Run manually or via GitHub Actions cron.
"""

import json
import os
from datetime import datetime
from pathlib import Path
import urllib.request

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "nfl-stats-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def save(name: str, data: dict):
    path = DATA_DIR / name
    path.write_text(json.dumps(data, indent=2))
    print(f"  saved {path}")


def fetch_scoreboard(week: int = None, season: int = None):
    url = f"{BASE}/scoreboard"
    params = []
    if season and week:
        params.append(f"seasontype=2&week={week}&season={season}")
    elif week:
        params.append(f"seasontype=2&week={week}")
    if params:
        url += "?" + "&".join(params)

    print(f"Fetching scoreboard: {url}")
    raw = fetch(url)

    games = []
    season_year = raw.get("season", {}).get("year", datetime.now().year)
    week_num = raw.get("week", {}).get("number", week)

    for event in raw.get("events", []):
        comp = event["competitions"][0]
        status = event["status"]["type"]
        home = next(t for t in comp["competitors"] if t["homeAway"] == "home")
        away = next(t for t in comp["competitors"] if t["homeAway"] == "away")

        games.append({
            "id": event["id"],
            "name": event["name"],
            "short_name": event["shortName"],
            "date": event["date"],
            "status": status["name"],
            "completed": status["completed"],
            "home": {
                "id": home["id"],
                "abbr": home["team"]["abbreviation"],
                "name": home["team"]["displayName"],
                "score": int(home.get("score", 0) or 0),
                "winner": home.get("winner", False),
                "logo": home["team"].get("logo", ""),
                "color": home["team"].get("color", "013369"),
            },
            "away": {
                "id": away["id"],
                "abbr": away["team"]["abbreviation"],
                "name": away["team"]["displayName"],
                "score": int(away.get("score", 0) or 0),
                "winner": away.get("winner", False),
                "logo": away["team"].get("logo", ""),
                "color": away["team"].get("color", "D50A0A"),
            },
            "venue": comp.get("venue", {}).get("fullName", ""),
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


def fetch_standings():
    url = f"{BASE}/standings"
    print(f"Fetching standings: {url}")
    raw = fetch(url)

    conferences = []
    for conf_data in raw.get("children", []):
        conf = {"name": conf_data["name"], "abbreviation": conf_data.get("abbreviation", ""), "divisions": []}
        for div_data in conf_data.get("children", []):
            division = {"name": div_data["name"], "teams": []}
            for entry in div_data.get("standings", {}).get("entries", []):
                team_data = entry.get("team", {})
                stats = {s["name"]: s["value"] for s in entry.get("stats", [])}
                division["teams"].append({
                    "id": team_data.get("id"),
                    "name": team_data.get("displayName"),
                    "abbr": team_data.get("abbreviation"),
                    "logo": team_data.get("logos", [{}])[0].get("href", ""),
                    "wins": int(stats.get("wins", 0)),
                    "losses": int(stats.get("losses", 0)),
                    "ties": int(stats.get("ties", 0)),
                    "pct": round(float(stats.get("winPercent", 0)), 3),
                    "points_for": int(stats.get("pointsFor", 0)),
                    "points_against": int(stats.get("pointsAgainst", 0)),
                    "streak": stats.get("streak", ""),
                    "clinched": stats.get("clincher", ""),
                })
            conf["divisions"].append(division)
        conferences.append(conf)

    result = {"fetched_at": datetime.utcnow().isoformat() + "Z", "conferences": conferences}
    save("standings.json", result)
    return result


def fetch_team_schedule(team_abbr: str, season: int = None):
    url = f"{BASE}/teams"
    raw = fetch(url)
    team_id = None
    for sport in raw.get("sports", []):
        for league in sport.get("leagues", []):
            for team in league.get("teams", []):
                t = team.get("team", {})
                if t.get("abbreviation", "").upper() == team_abbr.upper():
                    team_id = t["id"]
                    break

    if not team_id:
        print(f"Team '{team_abbr}' not found.")
        return None

    year = season or datetime.now().year
    url = f"{BASE}/teams/{team_id}/schedule?season={year}"
    print(f"Fetching {team_abbr} schedule: {url}")
    raw = fetch(url)

    games = []
    for event in raw.get("events", []):
        comp = event["competitions"][0]
        home = next((t for t in comp["competitors"] if t["homeAway"] == "home"), {})
        away = next((t for t in comp["competitors"] if t["homeAway"] == "away"), {})
        status = event["status"]["type"]
        games.append({
            "id": event["id"],
            "week": event.get("week", {}).get("number"),
            "date": event["date"],
            "completed": status.get("completed", False),
            "status": status.get("name"),
            "home_abbr": home.get("team", {}).get("abbreviation"),
            "away_abbr": away.get("team", {}).get("abbreviation"),
            "home_score": int(home.get("score", 0) or 0),
            "away_score": int(away.get("score", 0) or 0),
            "home_winner": home.get("winner", False),
            "away_winner": away.get("winner", False),
        })

    result = {"team": team_abbr, "season": year, "fetched_at": datetime.utcnow().isoformat() + "Z", "games": games}
    save(f"schedule_{team_abbr.lower()}_{year}.json", result)
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

    parser = argparse.ArgumentParser(description="Fetch NFL stats from ESPN API")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("current", help="Fetch current week scoreboard + standings")
    p_week = sub.add_parser("week", help="Fetch a specific week")
    p_week.add_argument("week", type=int)
    p_week.add_argument("--season", type=int)

    p_all = sub.add_parser("all", help="Fetch all 18 weeks of a season")
    p_all.add_argument("--season", type=int)

    p_team = sub.add_parser("team", help="Fetch a team's full schedule")
    p_team.add_argument("abbr")
    p_team.add_argument("--season", type=int)

    sub.add_parser("standings", help="Fetch current standings only")
    sub.add_parser("index", help="Rebuild local week index")

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
