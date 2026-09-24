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

def _read_sheet(path: Path, sheet: str) -> pd.DataFrame:
    # Source workbook has the field names in the first spreadsheet row.
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    header_rows = raw.index[raw.apply(lambda r: r.astype(str).str.strip().eq("Date").any(), axis=1)]
    if len(header_rows) == 0:
        raise ValueError(f"Could not locate OHLC header in sheet {sheet}")
    header_row = header_rows[0]
    header = raw.loc[header_row].astype(str).str.strip().tolist()
    out = raw.iloc[header_row + 1:].copy()
    out.columns = header
    return out.reset_index(drop=True)

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Normalize the source's first-column ticker/date layout.
    if "Date" not in out.columns:
        first = out.columns[0]
        out = out.rename(columns={first: "Date"})
    if "Open" not in out.columns and len(out.columns) >= 2:
        out = out.rename(columns={out.columns[1]: "Open"})
    if "High" not in out.columns and len(out.columns) >= 3:
        out = out.rename(columns={out.columns[2]: "High"})
    if "Low" not in out.columns and len(out.columns) >= 4:
        out = out.rename(columns={out.columns[3]: "Low"})
    if "Close" not in out.columns and len(out.columns) >= 5:
        out = out.rename(columns={out.columns[4]: "Close"})
    if "Volume" not in out.columns and "Vol." in out.columns:
        out = out.rename(columns={"Vol.": "Volume"})
    missing = REQUIRED - set(out.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.normalize()
    for c in ["Open", "High", "Low", "Close"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if "Volume" in out.columns:
        out["Volume"] = pd.to_numeric(out["Volume"], errors="coerce")
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
        assets[sheet] = AssetData(sheet, normalize_columns(_read_sheet(path, sheet)))
    return assets

def close_matrix(assets: dict[str, AssetData]) -> pd.DataFrame:
    return pd.concat(
        {ticker: a.frame.set_index("Date")["Close"].where(a.frame.set_index("Date")["ohlc_valid"])
         for ticker, a in assets.items()},
        axis=1
    ).sort_index()
