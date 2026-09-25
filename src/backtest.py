"""Monthly portfolio simulator with explicit cash and no look-ahead."""
from __future__ import annotations
import pandas as pd


def simulate(
    prices, target_weights, initial_capital, monthly_contribution=0.0,
    commission_bps=10.0, slippage_bps=5.0,
    invest_contributions=True, rebalance=True, execution_prices=None,
):
    """Use month-end closes for decisions and next-session opens for execution.

    Non-rebalancing strategies (B0/B1) retain holdings. In an expanding
    universe, cash reserved for assets that did not yet exist is deployed
    when those assets first become tradable, while the configured cash reserve
    remains untouched unless it is the only cash available for an order.
    """
    prices = prices.sort_index()
    target_weights = target_weights.sort_index()
    execution_prices = prices if execution_prices is None else execution_prices.sort_index()
    execution_prices = execution_prices.reindex(index=prices.index, columns=prices.columns)
    cash = float(initial_capital)
    shares = pd.Series(0.0, index=prices.columns)
    mark_prices = pd.Series(float("nan"), index=prices.columns)
    rows, turnover, trades = [], 0.0, 0
    months = prices.index.to_period("M").unique()
    cost_rate = (commission_bps + slippage_bps) / 10000.0

    # For non-rebalancing strategies, each asset's initial target amount is
    # reserved until that asset becomes tradable. This prevents a late-starting
    # ETF from leaving its allocation permanently stranded in cash.
    initial_target_value = (
        target_weights.iloc[0].reindex(prices.columns).fillna(0.0)
        * float(initial_capital)
        if len(target_weights)
        else pd.Series(0.0, index=prices.columns)
    )
    funded_initial = pd.Series(False, index=prices.columns)

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
        if required and rebalance:
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
            # Non-rebalancing strategies must not wait for late-starting
            # assets: they execute on the next session and retain idle cash
            # until each target asset becomes tradable.
            if not rebalance or (p_try.reindex(required).notna().all() if required else True):
                execution = dt
                break
        if execution is None:
            break

        cash += float(monthly_contribution)
        p_dec = prices.loc[decision]
        eligible_target = desired.copy()
        desired[~p_dec.notna()] = 0.0
        if desired.sum() > 1.0:
            desired /= desired.sum()

        p = execution_prices.loc[execution]
        tradable = p.notna()
        mark_prices.loc[tradable] = p.loc[tradable]
        current = shares * mark_prices.fillna(0.0)
        total = float(cash + current.sum())

        if month_i == 0 and not rebalance:
            # Invest the initial capital according to the configured targets,
            # plus this month's contribution for DCA.
            target_value = initial_target_value.copy()
            if invest_contributions:
                target_value += float(monthly_contribution) * desired
        elif rebalance:
            target_value = total * desired
        elif invest_contributions:
            target_value = current + float(monthly_contribution) * desired
        else:
            target_value = current.copy()

        if not rebalance:
            # Deploy the portion of initial capital reserved for assets that
            # were unavailable at the beginning of the expanding history.
            newly_tradable = (
                eligible_target.gt(0)
                & tradable
                & shares.eq(0.0)
                & (~funded_initial)
                & (month_i > 0)
            )
            target_value = target_value + initial_target_value.where(newly_tradable, 0.0)
            funded_initial = funded_initial | (
                eligible_target.gt(0) & tradable & shares.eq(0.0) & (month_i == 0)
            ) | newly_tradable

        delta_value = target_value - current
        if not rebalance:
            # Initial allocation is funded exactly once when each asset first
            # becomes tradable. Keep this explicit at the order level so a
            # late-starting asset cannot leave its reserved capital stranded.
            delta_value.loc[newly_tradable] = initial_target_value.loc[newly_tradable]
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

        shares += (delta_value / p.replace(0, pd.NA)).fillna(0.0)
        cash = max(0.0, float(cash - delta_value.sum() - costs))
        turnover += (gross_buy + gross_sell) / max(total, 1e-12)
        trades += int((delta_value.abs() > 1e-10).sum())
        mark = float(cash + (shares * mark_prices.fillna(0.0)).sum())
        rows.append(
            (
                execution,
                mark,
                cash,
                float(monthly_contribution) if invest_contributions else 0.0,
            )
        )

    equity = pd.DataFrame(
        rows, columns=["date", "equity", "cash", "contribution"]
    ).set_index("date")
    return equity, turnover, trades
