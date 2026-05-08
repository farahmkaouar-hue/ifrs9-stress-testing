"""
fred_client.py - Telechargement optionnel de series FRED.

La cle API ne doit pas etre codee en dur. Utiliser une variable d'environnement :

PowerShell:
    $env:FRED_API_KEY = "..."

Le module est volontairement petit : il complete les CSV locaux dans data/varmacro
sans rendre le projet dependant d'un acces reseau pendant la soutenance.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
MACRO_DIR = ROOT / "data" / "varmacro"
FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


DEFAULT_FRED_SERIES = {
    "UNRATE": "UNRATE",
    "FEDFUNDS": "FEDFUNDS",
    "CPIAUCSL": "CPIAUCSL",
    "GDPC1": "GDPC1",
    "GDP": "GDP",
    "DRCCLACBS": "DRCCLACBS",
    "BAMLH0A0HYM2": "BAMLH0A0HYM2",
}


def get_fred_api_key(api_key: str | None = None) -> str:
    """Retourne la cle FRED depuis l'argument ou l'environnement."""
    key = api_key or os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError(
            "FRED_API_KEY absent. Definir la variable d'environnement avant le telechargement."
        )
    return key


def fetch_fred_series(
    series_id: str,
    api_key: str | None = None,
    observation_start: str = "2000-01-01",
    observation_end: str | None = None,
) -> pd.DataFrame:
    """Telecharge une serie FRED et retourne un DataFrame date/value."""
    params = {
        "series_id": series_id,
        "api_key": get_fred_api_key(api_key),
        "file_type": "json",
        "observation_start": observation_start,
    }
    if observation_end:
        params["observation_end"] = observation_end

    response = requests.get(FRED_OBSERVATIONS_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    observations = payload.get("observations", [])
    df = pd.DataFrame(observations)
    if df.empty:
        raise RuntimeError(f"Aucune observation FRED retournee pour {series_id}")

    df = df[["date", "value"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"].replace(".", pd.NA), errors="coerce")
    df = df.dropna(subset=["value"]).rename(columns={"value": series_id})
    return df


def refresh_macro_csvs(
    series_map: dict[str, str] | None = None,
    api_key: str | None = None,
    output_dir: str | Path = MACRO_DIR,
    observation_start: str = "2000-01-01",
    observation_end: str | None = None,
) -> list[Path]:
    """
    Telecharge les series FRED et ecrit des CSV compatibles avec data_prep.load_macro_data().
    """
    series_map = series_map or DEFAULT_FRED_SERIES
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for filename_stem, series_id in series_map.items():
        df = fetch_fred_series(
            series_id,
            api_key=api_key,
            observation_start=observation_start,
            observation_end=observation_end,
        )
        out = output_dir / f"{filename_stem}.csv"
        df.to_csv(out, index=False)
        written.append(out)
    return written
