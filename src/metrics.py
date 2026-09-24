"""Performance metrics for portfolio equity curves."""
from __future__ import annotations
import math
import pandas as pd

def summarize(equity: pd.Series, turnover: float = 0.0, trades: int = 0) -> dict:
    equity = equity.dropna()
    if len(equity) < 2:
        return {}
    r = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else float("nan")
    vol = r.std(ddof=1) * math.sqrt(12)
    sharpe = (r.mean() / r.std(ddof=1)) * math.sqrt(12) if r.std(ddof=1) else float("nan")
    downside = r[r < 0].std(ddof=1)
    sortino = (r.mean() / downside) * math.sqrt(12) if downside and not math.isnan(downside) else float("nan")
    peak = equity.cummax()
    dd = equity / peak - 1
    max_dd = dd.min()
    recovery = 0
    longest_recovery = 0
    for v in equity:
        if v >= equity.loc[:equity.index[equity.tolist().index(v)]].max():
            recovery = 0
        else:
            recovery += 1
            longest_recovery = max(longest_recovery, recovery)
    calmar = cagr / abs(max_dd) if max_dd < 0 else float("nan")
    return {
        "final_value": float(equity.iloc[-1]),
        "CAGR": float(cagr),
        "ann_vol": float(vol),
        "max_drawdown": float(max_dd),
        "Sharpe": float(sharpe),
        "Sortino": float(sortino),
        "Calmar": float(calmar),
        "turnover": float(turnover),
        "trades": int(trades),
        "longest_recovery_months": int(longest_recovery),
    }
