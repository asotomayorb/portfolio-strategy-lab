"""Load and normalize one OHLC CSV per ticker."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

REQUIRED = {"Date", "Open", "High", "Low", "Close"}

@dataclass
class AssetData:
    ticker: str
    frame: pd.DataFrame

def _read_csv(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, header=None, dtype=str)
    header_rows = raw.index[raw.apply(lambda r: r.astype(str).str.strip().eq("Date").any(), axis=1)]
    if len(header_rows) == 0:
        raise ValueError(f"Could not locate OHLC header in {path.name}")
    header_row = header_rows[0]
    header = raw.loc[header_row].astype(str).str.strip().tolist()
    out = raw.iloc[header_row + 1:].copy()
    out.columns = header
    return out.reset_index(drop=True)

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Date" not in out.columns:
        out = out.rename(columns={out.columns[0]: "Date"})
    for name, idx in [("Open",1),("High",2),("Low",3),("Close",4)]:
        if name not in out.columns and len(out.columns) > idx:
            out = out.rename(columns={out.columns[idx]: name})
    if "Volume" not in out.columns and "Vol." in out.columns:
        out = out.rename(columns={"Vol.": "Volume"})
    missing = REQUIRED - set(out.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    date_text = out["Date"].astype(str).str.strip()
    has_time = date_text.str.contains(r"\s")
    parsed = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")
    parsed.loc[~has_time] = pd.to_datetime(
        date_text.loc[~has_time], errors="coerce", dayfirst=True, format="mixed"
    )
    parsed.loc[has_time] = pd.to_datetime(
        date_text.loc[has_time], errors="coerce", dayfirst=False, format="mixed"
    )
    out["Date"] = parsed.dt.normalize()
    for c in ["Open", "High", "Low", "Close"]:
        # Some exported feeds quote thousands separators, e.g. "10,843.40".
        # Remove grouping commas before numeric conversion.
        out[c] = pd.to_numeric(
            out[c].astype(str).str.replace(",", "", regex=False).str.strip().str.strip('"'),
            errors="coerce",
        )
    if "Volume" in out.columns:
        out["Volume"] = pd.to_numeric(
            out["Volume"].astype(str).str.replace(",", "", regex=False).str.strip(),
            errors="coerce",
        )
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

def load_csv_folder(folder: str | Path) -> dict[str, AssetData]:
    folder = Path(folder)
    if not folder.exists():
        raise FileNotFoundError(f"Ticker folder not found: {folder}")
    assets = {}
    for path in sorted(folder.glob("*.csv")):
        ticker = path.stem.upper()
        assets[ticker] = AssetData(ticker, normalize_columns(_read_csv(path)))
    if not assets:
        raise ValueError(f"No .csv ticker files found in {folder}")
    return assets

def close_matrix(assets):
    """Build a date-indexed close matrix while preserving OHLC validity masks."""
    series = {}
    for ticker, asset in assets.items():
        frame = asset.frame.set_index("Date")
        series[ticker] = frame["Close"].where(frame["ohlc_valid"])
    return pd.concat(series, axis=1, sort=False).sort_index()
