"""Phase 1 pre-registered transaction-cost/slippage sensitivity.

This is a stress test, not parameter selection. The frozen strategy/config/data
remain unchanged; only commission and slippage assumptions vary symmetrically.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experiment import CONFIG, TICKER_DIR, load_config, load_targets, prepare_price_matrices, _signals
from backtest import simulate
from metrics import summarize
from history import common_history_start

SCENARIOS = [
    ("zero", 0.0, 0.0),
    ("commission_only", 10.0, 0.0),
    ("slippage_only", 0.0, 5.0),
    ("baseline", 10.0, 5.0),
    ("high", 20.0, 10.0),
    ("stress", 30.0, 20.0),
]

STRATEGIES = [
    "B0_buy_hold", "B1_dca", "S1_momentum", "S3_rotation",
    "S4_moving_average", "S5_dynamic_allocation", "S6_risk_parity",
]


def evaluate(prices, execution, cfg, targets, commission_bps, slippage_bps):
    invest_targets = {k: v for k, v in targets.items() if k != "CASH"}
    invest_total = sum(invest_targets.values())
    signals = _signals(prices, targets, cfg)
    rows = []

    for name in STRATEGIES:
        sig = signals[name].copy()
        if name not in {"B0_buy_hold", "B1_dca"} and invest_total < 1.0:
            sig = sig * invest_total

        invest = name != "B0_buy_hold"
        rebalance = name not in {"B0_buy_hold", "B1_dca"}
        eq, turnover, trades = simulate(
            prices,
            sig,
            float(cfg["portfolio"]["initial_capital"]),
            float(cfg["portfolio"]["monthly_contribution"]) if invest else 0.0,
            commission_bps,
            slippage_bps,
            invest_contributions=invest,
            rebalance=rebalance,
            execution_prices=execution,
        )
        if eq.empty:
            continue

        m = summarize(
            eq["equity"],
            turnover=turnover,
            trades=trades,
            external_cashflows=eq["contribution"],
            initial_capital=float(cfg["portfolio"]["initial_capital"]),
            cash=eq["cash"],
        )
        rows.append({"strategy": name, **m})
    return rows


def main():
    cfg = load_config(CONFIG)
    targets = load_targets(cfg)
    prices, execution = prepare_price_matrices(TICKER_DIR)
    rows = []

    for history_mode in ("common", "expanding"):
        p = prices.copy()
        x = execution.copy()
        if history_mode == "common":
            start = common_history_start(p)
            p = p.loc[p.index >= start].copy()
            x = x.reindex(p.index)

        for scenario, commission_bps, slippage_bps in SCENARIOS:
            for r in evaluate(
                p, x, cfg, targets, commission_bps, slippage_bps
            ):
                r.update({
                    "history_mode": history_mode,
                    "scenario": scenario,
                    "commission_bps": commission_bps,
                    "slippage_bps": slippage_bps,
                    "total_one_way_bps": commission_bps + slippage_bps,
                    "is_baseline": scenario == "baseline",
                })
                rows.append(r)

    data = pd.DataFrame(rows)
    data.to_csv(ROOT / "cost_slippage_sensitivity_ci.csv", index=False)

    lines = [
        "PHASE1_COST_SLIPPAGE_SENSITIVITY",
        "pre_registered_scenarios=zero,commission_only,slippage_only,baseline,high,stress",
        "no_parameter_selection=true",
    ]
    for name in STRATEGIES:
        lines.append("\n" + name)
        for mode in ("common", "expanding"):
            z = data[(data.strategy == name) & (data.history_mode == mode)]
            b = z[z.scenario == "baseline"].iloc[0]
            s = z[z.scenario == "stress"].iloc[0]
            lines.append(
                f"{mode}_baseline_CAGR={b.CAGR:.6f}_stress_CAGR={s.CAGR:.6f}"
            )
            lines.append(
                f"{mode}_baseline_Sharpe={b.Sharpe:.6f}_stress_Sharpe={s.Sharpe:.6f}"
            )
            lines.append(
                f"{mode}_baseline_max_drawdown={b.max_drawdown:.6f}_stress_max_drawdown={s.max_drawdown:.6f}"
            )

    (ROOT / "cost_slippage_sensitivity_summary.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
