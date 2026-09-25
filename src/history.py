"""History utilities for common-history and expanding-universe analysis."""
from __future__ import annotations

import pandas as pd


def coverage_table(prices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker in prices.columns:
        valid = prices[ticker].dropna()
        rows.append(
            {
                "ticker": ticker,
                "start": valid.index.min() if len(valid) else pd.NaT,
                "end": valid.index.max() if len(valid) else pd.NaT,
                "observations": int(len(valid)),
            }
        )
    return pd.DataFrame(rows).set_index("ticker")


def common_history_start(prices: pd.DataFrame, tickers=None) -> pd.Timestamp:
    selected = list(prices.columns if tickers is None else tickers)
    missing = sorted(set(selected) - set(prices.columns))
    if missing:
        raise ValueError("Unknown tickers: " + ", ".join(missing))
    if not selected:
        raise ValueError("No tickers supplied")
    starts = []
    for ticker in selected:
        valid = prices[ticker].dropna()
        if valid.empty:
            raise ValueError(f"No valid price history for {ticker}")
        starts.append(valid.index.min())
    return max(starts)


def clip_common_history(prices: pd.DataFrame, tickers=None) -> pd.DataFrame:
    start = common_history_start(prices, tickers)
    return prices.loc[prices.index >= start].copy()
