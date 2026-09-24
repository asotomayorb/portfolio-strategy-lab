"""Monthly portfolio simulator with explicit cash and no look-ahead."""
from __future__ import annotations
import pandas as pd

def simulate(prices, target_weights, initial_capital, monthly_contribution=0.0,
             commission_bps=10.0, slippage_bps=5.0,
             invest_contributions=True, rebalance=True):
    """Simulate monthly decisions.

    B0 Buy & Hold: call with invest_contributions=False, rebalance=False.
    DCA/tactical strategies: invest_contributions=True, rebalance=True.
    """
    prices = prices.sort_index()
    cash = float(initial_capital)
    shares = pd.Series(0.0, index=prices.columns)
    rows, turnover, trades = [], 0.0, 0
    months = prices.index.to_period("M").unique()
    cost_rate = (commission_bps + slippage_bps) / 10000.0

    for month_i, month in enumerate(months):
        dates = prices.index[prices.index.to_period("M") == month]
        if len(dates) == 0:
            continue
        decision = dates[-1]
        future = prices.index[prices.index > decision]
        if len(future) == 0:
            break
        execution = future[0]
        cash += float(monthly_contribution)

        p_dec = prices.loc[decision]
        desired = target_weights.loc[decision] if decision in target_weights.index else pd.Series(0.0, index=prices.columns)
        desired = desired.reindex(prices.columns).fillna(0.0).clip(lower=0.0)
        desired[~p_dec.notna()] = 0.0
        if desired.sum() > 1.0:
            desired /= desired.sum()

        p = prices.loc[execution]
        tradable = p.notna()
        current = shares * p.fillna(0.0)
        total = float(cash + current.sum())

        if month_i == 0 or rebalance:
            target = total * desired
        elif invest_contributions and desired.sum() > 0:
            target = current + float(monthly_contribution) * desired
        else:
            target = current.copy()

        delta_value = target - current
        delta_value[~tradable] = 0.0
        gross_buy = float(delta_value.clip(lower=0).sum())
        gross_sell = float((-delta_value.clip(upper=0)).sum())
        costs = (gross_buy + gross_sell) * cost_rate

        if gross_buy + costs > cash + gross_sell:
            available = max(0.0, cash + gross_sell)
            scale = available / max(gross_buy * (1.0 + cost_rate), 1e-12)
            delta_value = delta_value.clip(upper=0) + delta_value.clip(lower=0) * min(1.0, scale)
            gross_buy = float(delta_value.clip(lower=0).sum())
            gross_sell = float((-delta_value.clip(upper=0)).sum())
            costs = (gross_buy + gross_sell) * cost_rate

        shares += delta_value / p.replace(0, pd.NA)
        cash = max(0.0, float(cash - delta_value.sum() - costs))
        turnover += (gross_buy + gross_sell) / max(total, 1e-12)
        trades += int((delta_value.abs() > 1e-10).sum())
        mark = float(cash + (shares * p.fillna(0.0)).sum())
        rows.append((execution, mark, cash))

    return pd.DataFrame(rows, columns=["date","equity","cash"]).set_index("date"), turnover, trades
