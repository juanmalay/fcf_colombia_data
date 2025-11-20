# scraper/espn/results.py
from __future__ import annotations

from typing import List, Dict

import requests

from .parser import parse_results_html

RESULTS_URL = "https://www.espn.com/soccer/team/results/_/id/208/colombia"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}


def fetch_last_results(limit: int = 8) -> List[Dict]:
    print("=== ESPN Results (Últimos partidos) ===")
    resp = requests.get(RESULTS_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    matches = parse_results_html(resp.text, limit=limit)
    return [m.to_dict() for m in matches]
