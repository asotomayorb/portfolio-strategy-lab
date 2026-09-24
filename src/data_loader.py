"""Load and normalize the project's OHLC workbook without fabricating data."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

REQUIRED = {"Date", "Open", "High", "Low", "Close"}

@dataclass
class AssetData:
    ticker: str
    frame: pd.DataFrame

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.rename(columns={"Vol.": "Volume"})
    missing = REQUIRED - set(out.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    if out["Date"].isna().any():
        raise ValueError("Invalid dates found")
    out = out.sort_values("Date").reset_index(drop=True)
    if out["Date"].duplicated().any():
        raise ValueError("Duplicate dates found")
    out["ohlc_valid"] = (
        out[["Open","High","Low","Close"]].notna().all(axis=1)
        & (out["Open"] > 0) & (out["High"] > 0)
        & (out["Low"] > 0) & (out["Close"] > 0)
        & (out["High"] >= out[["Open","Close","Low"]].max(axis=1))
        & (out["Low"] <= out[["Open","Close","High"]].min(axis=1))
    )
    return out

def load_workbook(path: str | Path) -> dict[str, AssetData]:
    path = Path(path)
    book = pd.ExcelFile(path)
    assets: dict[str, AssetData] = {}
    for sheet in book.sheet_names:
        if sheet == "TICKERS" or sheet.startswith("Copia de"):
            continue
        assets[sheet] = AssetData(sheet, normalize_columns(pd.read_excel(path, sheet_name=sheet)))
    return assets

def close_matrix(assets: dict[str, AssetData]) -> pd.DataFrame:
    """Return raw close prices; missing history stays NaN (never forward-filled pre-inception)."""
    series = {ticker: a.frame.set_index("Date")["Close"].where(a.frame.set_index("Date")["ohlc_valid"]) for ticker, a in assets.items()}
    return pd.concat(series, axis=1).sort_index()
