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


@dataclass
class Match:
    home_team: str
    away_team: str
    date_iso: str  # ISO 8601
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    @property
    def home_code(self) -> str:
        return team_code(self.home_team)

    @property
    def away_code(self) -> str:
        return team_code(self.away_team)

    def to_dict(self) -> Dict:
        """Formato que espera tu Flutter."""
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
    """Parsea la página de resultados de ESPN y devuelve los últimos partidos."""
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.select("table.Table tbody tr")
    matches: List[Match] = []

    for row in rows:
        cols = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        if len(cols) < 4:
            continue

        # Normalmente:
        # 0: date          -> "Sat, Nov 15"
        # 1: home team     -> "Colombia"
        # 2: result        -> "2 - 1"
        # 3: away team     -> "New Zealand"
        # 4: estado (FT)
        # 5: competición
        date_txt = cols[0]
        home_team = cols[1]
        result_txt = cols[2]
        away_team = cols[3]

        m = re.search(r"(\d+)\s*-\s*(\d+)", result_txt)
        if not m:
            continue

        home_score = int(m.group(1))
        away_score = int(m.group(2))

        date_iso = _parse_espn_date(date_txt)

        matches.append(
            Match(
                home_team=home_team,
                away_team=away_team,
                date_iso=date_iso,
                home_score=home_score,
                away_score=away_score,
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

        # Estructura típica de fixtures:
        # 0: date          -> "Fri, Mar 21"
        # 1: home team
        # 2: vs / v / -
        # 3: away team
        # 4: hora (a veces)
        date_txt = cols[0]
        home_team = cols[1]
        away_team = cols[3] if len(cols) > 3 else ""

        # Hora, si existe
        time_txt: Optional[str] = None
        if len(cols) >= 5:
            # Última col suele ser la hora (o competición).
            # Si parece hora HH:MM la usamos.
            maybe_time = cols[4]
            if re.match(r"^\d{1,2}:\d{2}$", maybe_time):
                time_txt = maybe_time

        date_iso = _parse_espn_date(date_txt, time_txt)

        matches.append(
            Match(
                home_team=home_team,
                away_team=away_team,
                date_iso=date_iso,
            )
        )

        if len(matches) >= limit:
            break

    return matches
