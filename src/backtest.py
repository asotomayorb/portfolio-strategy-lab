"""Deterministic monthly portfolio simulator.

Signals are weights decided using data through month-end and executed at the
next available session. Cash is explicit. No leverage and no shorting.
"""
from __future__ import annotations
import pandas as pd

def monthly_calendar(asset_prices: dict[str, pd.Series]) -> pd.DatetimeIndex:
    idx = sorted(set().union(*[set(s.index) for s in asset_prices.values()]))
    return pd.DatetimeIndex(idx).to_period("M").to_timestamp("M").drop_duplicates()

def next_session_on_or_after(series: pd.Series, date: pd.Timestamp) -> pd.Timestamp | None:
    x = series.index[series.index >= date]
    return x[0] if len(x) else None

def simulate(prices: pd.DataFrame, target_weights: pd.DataFrame,
             initial_capital: float, monthly_contribution: float = 0.0,
             commission_bps: float = 10.0, slippage_bps: float = 5.0):
    prices = prices.sort_index().ffill()
    common = prices.index
    equity = initial_capital
    cash = initial_capital
    shares = pd.Series(0.0, index=prices.columns)
    rows = []
    turnover = 0.0
    trades = 0

    months = common.to_period("M").unique()
    for m in months:
        month_end_dates = common[common.to_period("M") == m]
        if len(month_end_dates) == 0:
            continue
        decision = month_end_dates[-1]
        next_dates = common[common > decision]
        if len(next_dates) == 0:
            break
        exec_date = next_dates[0]

        cash += monthly_contribution
        mark = float(cash + (shares * prices.loc[decision]).sum())
        desired = target_weights.loc[decision] if decision in target_weights.index else pd.Series(0.0, index=prices.columns)
        desired = desired.reindex(prices.columns).fillna(0.0).clip(lower=0.0)
        if desired.sum() > 1:
            desired = desired / desired.sum()

        exec_prices = prices.loc[exec_date]
        current_values = shares * exec_prices
        total = float(cash + current_values.sum())
        target_values = total * desired
        delta = target_values - current_values
        costs = float(delta.abs().sum()) * (commission_bps + slippage_bps) / 10000
        cash_after = cash - float(delta.sum()) - costs
        if cash_after < -1e-8:
            scale = max(0.0, (cash - costs) / max(float(delta[delta > 0].sum()), 1e-12))
            buys = delta.clip(lower=0) * scale
            sells = (-delta.clip(upper=0))
            delta = buys - sells
            costs = float(delta.abs().sum()) * (commission_bps + slippage_bps) / 10000
            cash_after = cash - float(delta.sum()) - costs

        shares += delta / exec_prices
        cash = cash_after
        turnover += float(delta.abs().sum()) / max(total, 1e-12)
        trades += int((delta.abs() > 0).sum())
        mark_exec = float(cash + (shares * exec_prices).sum())
        rows.append((exec_date, mark_exec, cash))

    out = pd.DataFrame(rows, columns=["date", "equity", "cash"]).set_index("date")
    return out, turnover, trades
