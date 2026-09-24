"""Run one deterministic Phase 1 experiment from the source workbook."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from data_loader import load_workbook, close_matrix

def load_targets(path: str | Path) -> dict[str, float]:
    df = pd.read_excel(path, sheet_name="TICKERS", header=None)
    # Locate ticker/weight rows without assuming an exact header row.
    result = {}
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.tolist()]
        if len(vals) >= 2:
            ticker = vals[0]
            try:
                weight = float(vals[1])
            except (TypeError, ValueError):
                continue
            if ticker in {"VT","SMH","BTC","INDA","MSFT","NVDA","AVGO","GLD","URA","XLE","VHT","PLTR","QQQ"}:
                result[ticker] = weight
    return result

def prepare_prices(source: str | Path) -> pd.DataFrame:
    assets = load_workbook(source)
    return close_matrix(assets)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("source")
    args = p.parse_args()
    prices = prepare_prices(args.source)
    print("assets:", list(prices.columns))
    print("rows:", len(prices), "from", prices.index.min(), "to", prices.index.max())
    print("missing_by_asset:")
    print(prices.isna().sum().to_string())
