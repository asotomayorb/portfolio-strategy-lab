"""Frozen Phase 1 signal definitions. Signals are evaluated at month-end."""
from __future__ import annotations
import numpy as np
import pandas as pd
from risk import risk_parity as _erc_risk_parity

def _monthly(prices):
    return prices.resample("ME").last()

def buy_and_hold(prices, base_weights):
    return pd.DataFrame({c: base_weights.get(c, 0.0) for c in prices.columns}, index=prices.index)

def dca(prices, base_weights):
    # DCA is represented by the same strategic allocation; the simulator's
    # monthly contributions determine the cash deployment.
    return buy_and_hold(prices, base_weights)

def momentum(prices, lookback_months=12, top_n=3):
    m = _monthly(prices).pct_change(lookback_months)
    out = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    for dt, row in m.iterrows():
        eligible = row.dropna().nlargest(top_n)
        if len(eligible):
            w = pd.Series(0.0, index=prices.columns)
            w.loc[eligible.index] = 1.0 / len(eligible)
            out.loc[dt] = w
    return out.ffill()

def moving_average(prices, window=200):
    ma = prices.rolling(window).mean()
    out = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for c in prices.columns:
        out.loc[prices[c] > ma[c], c] = 1.0
    return out.div(out.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)

def rotation(prices, lookback_months=12, top_n=3):
    return momentum(prices, lookback_months, top_n)

def dynamic_allocation(prices, lookback_months=12, max_weight=0.25):
    scores = _monthly(prices).pct_change(lookback_months).clip(lower=0)
    out = pd.DataFrame(0.0, index=scores.index, columns=scores.columns)
    for dt, row in scores.iterrows():
        s = row.dropna()
        if s.sum() > 0:
            w = s / s.sum()
            # deterministic cap; excess is left as cash rather than redistributed
            out.loc[dt, w.index] = w.clip(upper=max_weight)
    return out.reindex(prices.index).ffill().fillna(0.0)

def risk_parity(prices, window=60):
    return _erc_risk_parity(prices, window=window)
