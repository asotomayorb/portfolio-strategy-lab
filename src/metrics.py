"""Performance metrics for portfolio equity curves with external cash-flow adjustment."""
from __future__ import annotations
import math
import pandas as pd

def summarize(
    equity: pd.Series,
    returns: pd.Series | None = None,
    turnover: float = 0.0,
    trades: int = 0,
    external_cashflows: pd.Series | None = None,
    initial_capital: float = 0.0,
    cash: pd.Series | None = None,
) -> dict:
    equity = equity.dropna()
    if len(equity) < 2:
        return {}
    if returns is None:
        if external_cashflows is None:
            r = equity.pct_change().dropna()
        else:
            flows = external_cashflows.reindex(equity.index).fillna(0.0)
            prior = equity.shift(1).fillna(float(initial_capital))
            denominator = prior + flows
            r = (equity / denominator.replace(0.0, pd.NA) - 1.0).dropna()
    else:
        r = returns.reindex(equity.index).dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    growth = float((1.0 + r).prod()) if len(r) else float("nan")
    cagr = growth ** (1 / years) - 1 if years > 0 and growth > 0 else float("nan")
    vol = r.std(ddof=1) * math.sqrt(12) if len(r) > 1 else float("nan")
    sharpe = (r.mean() / r.std(ddof=1)) * math.sqrt(12) if len(r) > 1 and r.std(ddof=1) else float("nan")
    downside = r[r < 0].std(ddof=1)
    sortino = (r.mean() / downside) * math.sqrt(12) if pd.notna(downside) and downside > 0 else float("nan")
    peak = equity.cummax()
    dd = equity / peak - 1
    max_dd = float(dd.min())
    recovery = 0
    longest_recovery = 0
    for underwater in dd < 0:
        recovery = recovery + 1 if underwater else 0
        longest_recovery = max(longest_recovery, recovery)
    if external_cashflows is not None:
        annual = (1.0 + r).groupby(r.index.to_period("Y")).prod() - 1.0
        worst_calendar_year = float(annual.min()) if len(annual) else float("nan")
    else:
        annual = equity.resample("YE").last().pct_change()
        worst_calendar_year = float(annual.min()) if len(annual) else float("nan")
    calmar = cagr / abs(max_dd) if max_dd < 0 else float("nan")

    total_contributions = float(external_cashflows.reindex(equity.index).fillna(0.0).sum()) if external_cashflows is not None else 0.0
    base_capital = float(initial_capital) if float(initial_capital) > 0 else float(equity.iloc[0])
    invested_capital = base_capital + total_contributions
    turnover_per_year = float(turnover / years) if years > 0 else float("nan")
    out = {
        "final_value": float(equity.iloc[-1]),
        "total_contributions": total_contributions,
        "invested_capital": invested_capital,
        "terminal_wealth_multiple": float(equity.iloc[-1] / invested_capital) if invested_capital > 0 else float("nan"),
        "CAGR": float(cagr),
        "ann_vol": float(vol),
        "max_drawdown": max_dd,
        "Sharpe": float(sharpe),
        "Sortino": float(sortino),
        "Calmar": float(calmar),
        "worst_calendar_year": worst_calendar_year,
        "turnover": float(turnover),
        "turnover_per_year": turnover_per_year,
        "trades": int(trades),
        "longest_recovery_months": int(longest_recovery),
    }
    if cash is not None:
        cash = cash.reindex(equity.index).dropna()
        if len(cash):
            cash_pct = cash / equity.reindex(cash.index)
            out["average_cash"] = float(cash.mean())
            out["max_cash"] = float(cash.max())
            out["min_cash"] = float(cash.min())
            out["average_cash_pct"] = float(cash_pct.mean())
            out["max_cash_pct"] = float(cash_pct.max())
    return out
