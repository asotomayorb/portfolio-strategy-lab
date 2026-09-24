"""Equal-risk-contribution weights using a deterministic covariance solver."""
from __future__ import annotations
import numpy as np
import pandas as pd

def erc_weights(returns: pd.DataFrame, max_iter: int = 500, tol: float = 1e-8) -> pd.Series:
    x = returns.dropna(axis=1, how="all").copy()
    if x.shape[1] == 0:
        return pd.Series(dtype=float)
    cov = x.cov().fillna(0.0).values
    cov = (cov + cov.T) / 2
    cov += np.eye(len(cov)) * 1e-10
    n = len(cov)
    w = np.repeat(1.0 / n, n)
    for _ in range(max_iter):
        sigma_w = cov @ w
        rc = w * sigma_w
        target = rc.sum() / n
        grad = rc - target
        if np.max(np.abs(grad)) < tol:
            break
        step = 0.05 / max(np.max(np.abs(cov)), 1e-8)
        w = np.maximum(w - step * grad, 1e-12)
        w /= w.sum()
    return pd.Series(w, index=x.columns)

def risk_parity(prices: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    ret = prices.pct_change()
    monthly = prices.resample("ME").last()
    out = pd.DataFrame(0.0, index=monthly.index, columns=prices.columns)
    for dt in monthly.index:
        hist = ret.loc[:dt].tail(window)
        valid = hist.dropna(axis=1, thresh=max(2, int(window * 0.8)))
        if valid.shape[1] == 0:
            continue
        w = erc_weights(valid)
        out.loc[dt, w.index] = w
    return out.reindex(prices.index).ffill().fillna(0.0)
