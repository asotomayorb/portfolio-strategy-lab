"""Value strategy interface.

Value is deliberately restricted to comparable assets. Phase 1 does not invent
a common valuation metric for BTC, gold or sector ETFs.
"""
from __future__ import annotations
import pandas as pd

def value(prices, eligible_weights):
    out = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for dt, weights in eligible_weights.items():
        s = pd.Series(weights, dtype=float).reindex(prices.columns).fillna(0).clip(lower=0)
        if s.sum() > 0:
            out.loc[dt] = s / s.sum()
    return out.ffill().fillna(0.0)
