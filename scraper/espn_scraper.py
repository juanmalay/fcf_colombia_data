import requests
import json
from datetime import datetime

URL = "https://site.web.api.espn.com/apis/v2/sports/soccer/fifa.world/events"

def scrape_espn():
    print("=== Scraping ESPN ===")

    res = requests.get(URL, headers={
        "User-Agent": "Mozilla/5.0"
    })

    data = res.json()

    events = data.get("events", [])
    next_matches = []
    results = []

    for e in events:
        competitions = e.get("competitions", [])
        if not competitions:
            continue

        comp = competitions[0]

        competitors = comp.get("competitors", [])
        if len(competitors) != 2:
            continue

        home = competitors[0]
        away = competitors[1]

        # Buscar SOLO si juega COLOMBIA
        if "colombia" not in home["team"]["displayName"].lower() \
           and "colombia" not in away["team"]["displayName"].lower():
            continue

        match_date = e["date"]

        match = {
            "home": home["team"]["displayName"],
            "homeCode": home["team"]["abbreviation"],
            "away": away["team"]["displayName"],
            "awayCode": away["team"]["abbreviation"],
            "date": match_date
        }

        # ¿Tiene marcador?
        if "score" in home and "score" in away:
            match["homeScore"] = home["score"]
            match["awayScore"] = away["score"]
            results.append(match)
        else:
            next_matches.append(match)

    # Guardar archivo JSON
    with open("data/matches.json", "w", encoding="utf-8") as f:
        json.dump({
            "nextMatches": next_matches,
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print("✔ Archivo actualizado: data/matches.json")


if __name__ == "__main__":
    scrape_espn()
