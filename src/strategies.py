"""Phase 1 strategy signal definitions.

This module intentionally keeps definitions simple and frozen. It returns
target weights at decision dates; the simulator handles execution/costs.
"""
from __future__ import annotations
import pandas as pd
import numpy as np

def buy_and_hold(prices, base_weights):
    return pd.DataFrame(index=prices.index, data={c: base_weights.get(c,0) for c in prices.columns})

def dca(prices, base_weights):
    # Same target allocation, implemented by the simulator with monthly cash.
    return buy_and_hold(prices, base_weights)

def momentum(prices, lookback_months=12, top_n=3):
    m = prices.resample("ME").last().pct_change(lookback_months)
    out = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for dt, row in m.iterrows():
        eligible = row.dropna().sort_values(ascending=False).head(top_n)
        if len(eligible):
            out.loc[out.index <= dt, eligible.index] = 1.0 / len(eligible)
    return out
