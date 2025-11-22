# scraper/espn/parser.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict
import re

from bs4 import BeautifulSoup

# Mapa muy básico nombre -> código de país (puedes ir ampliándolo)
TEAM_CODE_MAP = {
    "Colombia": "co",
    "Argentina": "ar",
    "Peru": "pe",
    "Perú": "pe",
    "Brazil": "br",
    "Brasil": "br",
    "Uruguay": "uy",
    "Chile": "cl",
    "Ecuador": "ec",
    "Bolivia": "bo",
    "Paraguay": "py",
    "Venezuela": "ve",
    "Mexico": "mx",
    "México": "mx",
    "United States": "us",
    "Estados Unidos": "us",
    "Costa Rica": "cr",
    "Panama": "pa",
    "Panamá": "pa",
    "Spain": "es",
    "España": "es",
    "Romania": "ro",
    "New Zealand": "nz",
    "Canada": "ca",
}


def team_code(name: str) -> str:
    """Devuelve código de bandera para country_flags.
    Si no está en el mapa, devuelve 'xx'."""
    name = name.strip()
    return TEAM_CODE_MAP.get(name, "xx")

def map_competition(raw: str) -> str:
    r = raw.lower()

    if "friendly" in r:
        return "Amistoso"
    if "qualifying" in r or "conmebol" in r:
        return "Eliminatorias"
    if "copa américa" in r or "copa america" in r:
        return "Copa América"
    if "world cup" in r:
        return "Mundial"

    return "Internacional"

def fetch_match_details(game_id: str) -> Dict:
    import requests

    url = f"https://www.espn.com/soccer/match/_/gameId/{game_id}"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()

    return parse_match_details_html(resp.text)


@dataclass
class Match:
    home_team: str
    away_team: str
    date_iso: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    match_type: Optional[str] = None   # 👈 NUEVO
    game_id: Optional[str] = None      # 👈 NUEVO

    @property
    def home_code(self) -> str:
        return team_code(self.home_team)

    @property
    def away_code(self) -> str:
        return team_code(self.away_team)

    def to_dict(self) -> Dict:
        data = {
            "homeTeam": self.home_team,
            "homeTeamCode": self.home_code,
            "awayTeam": self.away_team,
            "awayTeamCode": self.away_code,
            "date": self.date_iso,
        }
        if self.home_score is not None and self.away_score is not None:
            data["homeScore"] = self.home_score
            data["awayScore"] = self.away_score
        if self.match_type:
            data["matchType"] = self.match_type  # 👈 EXPORTAR TIPO
        if self.game_id:
            data["gameId"] = self.game_id        # 👈 para stats/alineaciones

        return data



# -------- parsers ----------


def _parse_espn_date(date_str: str, time_str: str | None = None) -> str:
    """Convierte 'Sat, Nov 15' (+ hora opcional) a ISO 8601.

    ESPN no da año en todos lados, tomamos el año actual.
    Si quieres ser más preciso, aquí puedes hacer magia extra.
    """
    date_str = date_str.strip()
    now = datetime.utcnow()
    fmt = "%a, %b %d"
    dt = datetime.strptime(date_str, fmt).replace(year=now.year)

    if time_str:
        # Ej: '18:00'
        try:
            hh, mm = map(int, time_str.split(":"))
            dt = dt.replace(hour=hh, minute=mm)
        except Exception:
            pass

    return dt.isoformat() + "Z"


def parse_results_html(html: str, limit: int = 10) -> List[Match]:
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.select("table.Table tbody tr")
    matches: List[Match] = []

    for row in rows:
        cols = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        if len(cols) < 4:
            continue

        date_txt = cols[0]
        home_team = cols[1]
        result_txt = cols[2]
        away_team = cols[3]

        # 👇 NUEVO: COMPETICIÓN
        competition_raw = cols[5] if len(cols) >= 6 else ""
        competition = map_competition(competition_raw)

        m = re.search(r"(\d+)\s*-\s*(\d+)", result_txt)
        if not m:
            continue

        home_score = int(m.group(1))
        away_score = int(m.group(2))

        date_iso = _parse_espn_date(date_txt)

        game_id = extract_game_id_from_row(row) 

        matches.append(
            Match(
                home_team=home_team,
                away_team=away_team,
                date_iso=date_iso,
                home_score=home_score,
                away_score=away_score,
                match_type=competition,
                game_id=game_id,
            )
        )

        if len(matches) >= limit:
            break

    return matches

def parse_fixtures_html(html: str, limit: int = 5) -> List[Match]:
    """Parsea la página de fixtures (próximos partidos)."""
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.select("table.Table tbody tr")
    matches: List[Match] = []

    for row in rows:
        cols = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        if len(cols) < 4:
            continue

        # 0: date          -> "Fri, Mar 21"
        # 1: home team
        # 2: vs / v / -
        # 3: away team
        # 4: hora o competición
        # 5: (a veces) competición
        date_txt = cols[0]
        home_team = cols[1]
        away_team = cols[3] if len(cols) > 3 else ""

        # Hora, si existe
        time_txt: Optional[str] = None
        competition_raw: str = ""

        if len(cols) >= 6:
            # 4 suele ser hora, 5 competición
            maybe_time = cols[4]
            if re.match(r"^\d{1,2}:\d{2}$", maybe_time):
                time_txt = maybe_time
                competition_raw = cols[5]
            else:
                # 4 no parece hora, puede ser competición ya
                competition_raw = cols[4]
        elif len(cols) == 5:
            maybe_time = cols[4]
            if re.match(r"^\d{1,2}:\d{2}$", maybe_time):
                time_txt = maybe_time
            else:
                competition_raw = maybe_time

        match_type = map_competition(competition_raw) if competition_raw else None

        date_iso = _parse_espn_date(date_txt, time_txt)

        game_id = extract_game_id_from_row(row)  # 👈 también para futuros partidos

        matches.append(
            Match(
                home_team=home_team,
                away_team=away_team,
                date_iso=date_iso,
                match_type=match_type,
                game_id=game_id,
            )
        )

        if len(matches) >= limit:
            break

    return matches

def extract_game_id_from_row(row) -> Optional[str]:
    """Busca el primer <a> con gameId en el href y devuelve ese id."""
    link = row.find("a", href=True)
    if not link:
        return None

    href = link["href"]
    m = re.search(r"gameId/(\d+)", href)
    if m:
        return m.group(1)
    return None

def parse_match_details_html(html: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")

    # ---------- FORMACIONES ----------
    # Buscar patrones tipo 4-2-3-1 o 4-3-3
    import re
    formations = re.findall(r"\b\d-\d-\d(?:-\d)?\b", html)

    home_formation = formations[0] if len(formations) >= 1 else None
    away_formation = formations[1] if len(formations) >= 2 else None

    # ---------- JUGADORES: titulares y suplentes ----------
    tables = soup.find_all("table")

    # ESPN suele tener:
    # table[0] = titulares local
    # table[1] = titulares visitante
    # table[2] = suplentes local
    # table[3] = suplentes visitante
    starters_home = []
    starters_away = []
    subs_home = []
    subs_away = []

    def parse_players_from_table(table):
        players = []
        rows = table.find_all("tr")

        for r in rows:
            cols = r.find_all("td")
            if len(cols) < 2:
                continue
            number = cols[0].get_text(strip=True)
            name = cols[1].get_text(strip=True)
            players.append({"number": number, "name": name})
        return players

    if len(tables) >= 2:
        starters_home = parse_players_from_table(tables[0])
        starters_away = parse_players_from_table(tables[1])

    if len(tables) >= 4:
        subs_home = parse_players_from_table(tables[2])
        subs_away = parse_players_from_table(tables[3])

    return {
        "home": {
            "formation": home_formation,
            "starters": starters_home,
            "substitutes": subs_home,
        },
        "away": {
            "formation": away_formation,
            "starters": starters_away,
            "substitutes": subs_away,
        }
    }
