"""Performance metrics for monthly portfolio equity curves."""
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
    calmar = cagr / abs(max_dd) if max_dd < 0 else float("nan")
    recovery = 0
    last_peak = equity.iloc[0]
    for i, v in enumerate(equity):
        if v >= last_peak:
            last_peak = v
            recovery = 0
        else:
            recovery += 1
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
        "max_cash": float("nan"),
        "recovery_months_last_or_longest": int(recovery),
    }
