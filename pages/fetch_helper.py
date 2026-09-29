"""
fetch_helper.py
Shared fetch function that uses requests (with retries) when available,
falling back to urllib. ESPN blocks urllib from GitHub Actions IPs.
"""
import json
import os
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.espn.com",
    "Referer": "https://www.espn.com/nfl/scoreboard",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def fetch(url: str) -> dict:
    """Fetch JSON from url. Uses requests with retries if available."""
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
