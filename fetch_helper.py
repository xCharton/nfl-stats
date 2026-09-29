"""
fetch_helper.py
Uses sports-skills CLI to fetch NFL data, which bypasses ESPN 403 blocks.
Falls back to direct ESPN request if sports-skills is unavailable.
"""
import json
import subprocess
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.espn.com",
    "Referer": "https://www.espn.com/nfl/scoreboard",
}

def fetch(url: str) -> dict:
    """Fetch ESPN JSON. Uses requests with retries."""
    try:
        import requests
        session = requests.Session()
        session.headers.update(HEADERS)
        for attempt in range(3):
            try:
                resp = session.get(url, timeout=20)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise
    except ImportError:
        import urllib.request
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())


def fetch_scoreboard_via_cli(week: int = None, season: int = None) -> dict:
    """Use sports-skills CLI to get scoreboard — bypasses 403."""
    cmd = ["sports-skills", "nfl", "get_scoreboard"]
    if week:
        cmd += ["--week", str(week)]
    if season:
        cmd += ["--season", str(season)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"sports-skills error: {result.stderr}")
    data = json.loads(result.stdout)
    return data.get("data", data)


def fetch_standings_via_cli(season: int = None) -> dict:
    """Use sports-skills CLI to get standings."""
    cmd = ["sports-skills", "nfl", "get_standings"]
    if season:
        cmd += ["--season", str(season)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"sports-skills error: {result.stderr}")
    data = json.loads(result.stdout)
    return data.get("data", data)


def fetch_schedule_via_cli(team_id: str, season: int = None) -> dict:
    """Use sports-skills CLI to get team schedule."""
    cmd = ["sports-skills", "nfl", "get_team_schedule", "--team_id", str(team_id)]
    if season:
        cmd += ["--season", str(season)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"sports-skills error: {result.stderr}")
    data = json.loads(result.stdout)
    return data.get("data", data)
