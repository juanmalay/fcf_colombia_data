# scraper/espn/fixtures.py
from __future__ import annotations

from typing import List, Dict

import requests

from .parser import parse_fixtures_html

FIXTURES_URL = "https://www.espn.com/soccer/team/fixtures/_/id/208/colombia"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}


def fetch_next_matches(limit: int = 5) -> List[Dict]:
    print("=== ESPN Fixtures (Próximos partidos) ===")
    resp = requests.get(FIXTURES_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    matches = parse_fixtures_html(resp.text, limit=limit)
    return [m.to_dict() for m in matches]
