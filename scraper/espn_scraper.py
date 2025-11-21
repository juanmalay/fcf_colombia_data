# scraper/espn_scraper.py
from __future__ import annotations

import json
from pathlib import Path

from espn.fixtures import fetch_next_matches
from espn.results import fetch_last_results


DATA_PATH = Path("data") / "matches.json"


def run():
    next_matches = fetch_next_matches(limit=5)
    results = fetch_last_results(limit=10)

    payload = {
        "nextMatches": next_matches,
        "results": results,
    }

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"✔ Archivo actualizado: {DATA_PATH}")


if __name__ == "__main__":
    run()
