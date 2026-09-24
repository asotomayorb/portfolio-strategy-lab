"""Load and normalize the project OHLC workbook.

Phase 1 policy:
- normalize column names (including INDA's Vol.)
- reject duplicate dates
- preserve raw OHLC values
- mark invalid OHLC rows instead of silently repairing them
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pandas as pd

REQUIRED = {"Date", "Open", "High", "Low", "Close"}

@dataclass
class AssetData:
    ticker: str
    frame: pd.DataFrame

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    aliases = {"Vol.": "Volume", "Adj Close": "Close"}
    out = out.rename(columns=aliases)
    missing = REQUIRED - set(out.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in out:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.sort_values("Date").reset_index(drop=True)
    if out["Date"].isna().any():
        raise ValueError("Invalid dates found")
    if out["Date"].duplicated().any():
        raise ValueError("Duplicate dates found")
    out["ohlc_valid"] = (
        (out["Open"] > 0) & (out["High"] > 0) & (out["Low"] > 0) &
        (out["Close"] > 0) &
        (out["High"] >= out[["Open","Close","Low"]].max(axis=1)) &
        (out["Low"] <= out[["Open","Close","High"]].min(axis=1))
    )
    return out

def load_workbook(path: str | Path) -> dict[str, AssetData]:
    path = Path(path)
    book = pd.ExcelFile(path)
    assets = {}
    for sheet in book.sheet_names:
        if sheet == "TICKERS" or sheet.startswith("Copia de"):
            continue
        assets[sheet] = AssetData(sheet, _normalize_columns(pd.read_excel(path, sheet_name=sheet)))
    return assets
