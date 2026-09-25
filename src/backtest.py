"""Monthly portfolio simulator with explicit cash and no look-ahead."""
from __future__ import annotations
import pandas as pd


def simulate(
    prices, target_weights, initial_capital, monthly_contribution=0.0,
    commission_bps=10.0, slippage_bps=5.0,
    invest_contributions=True, rebalance=True, execution_prices=None,
):
    """Use month-end closes for decisions and next-session opens for execution."""
    prices = prices.sort_index()
    target_weights = target_weights.sort_index()
    execution_prices = prices if execution_prices is None else execution_prices.sort_index()
    execution_prices = execution_prices.reindex(index=prices.index, columns=prices.columns)
    cash = float(initial_capital)
    shares = pd.Series(0.0, index=prices.columns)
    rows, turnover, trades = [], 0.0, 0
    months = prices.index.to_period("M").unique()
    cost_rate = (commission_bps + slippage_bps) / 10000.0

    for month_i, month in enumerate(months):
        month_dates = prices.index[prices.index.to_period("M") == month]
        if len(month_dates) == 0:
            continue

        target = target_weights[target_weights.index.to_period("M") == month]
        desired = (
            target.iloc[-1].reindex(prices.columns).fillna(0.0).clip(lower=0.0)
            if len(target)
            else pd.Series(0.0, index=prices.columns)
        )
        required = desired[desired > 0].index.tolist()
        if required:
            common_dates = prices.index[prices.index.to_period("M") == month]
            common_dates = common_dates[
                prices.loc[common_dates, required].notna().all(axis=1)
            ]
            decision = common_dates[-1] if len(common_dates) else month_dates[-1]
        else:
            decision = month_dates[-1]

        future = execution_prices.index[execution_prices.index > decision]
        execution = None
        for dt in future:
            p_try = execution_prices.loc[dt]
            if p_try.reindex(required).notna().all() if required else True:
                execution = dt
                break
        if execution is None:
            break

        cash += float(monthly_contribution)
        p_dec = prices.loc[decision]
        desired[~p_dec.notna()] = 0.0
        if desired.sum() > 1.0:
            desired /= desired.sum()

        p = execution_prices.loc[execution]
        tradable = p.notna()
        current = shares * p.fillna(0.0)
        total = float(cash + current.sum())

        if month_i == 0 or rebalance:
            target_value = total * desired
        elif invest_contributions and desired.sum() > 0:
            target_value = current + float(monthly_contribution) * desired
        else:
            target_value = current.copy()

        delta_value = target_value - current
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
        rows.append((execution, mark, cash, float(monthly_contribution) if invest_contributions else 0.0))

    equity = pd.DataFrame(rows, columns=["date", "equity", "cash", "contribution"]).set_index("date")
    return equity, turnover, trades
