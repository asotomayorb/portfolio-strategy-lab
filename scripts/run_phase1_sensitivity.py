"""Phase 1 frozen robustness extensions: parameter-neighbor and universe sensitivity.

These are sensitivity tests, not optimization. The baseline configuration remains
the reference; neighboring configurations are evaluated symmetrically around it.
No parameter is selected from results.
"""
from __future__ import annotations
import sys
from pathlib import Path
import itertools
import pandas as pd
import numpy as np

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/"src"))

from experiment import (
    CONFIG, TICKER_DIR, load_config, load_targets, prepare_price_matrices,
    _signals, allocation_metadata
)
from backtest import simulate
from metrics import summarize

BASELINES={
    "S1_momentum": {"lookback_months":[6,9,12,18,24], "top_n":[2,3,4]},
    "S3_rotation": {"lookback_months":[6,9,12,18,24], "top_n":[2,3,4]},
    "S4_moving_average": {"window_days":[150,200,250]},
    "S5_dynamic_allocation": {"lookback_months":[6,9,12,18,24], "max_weight":[0.20,0.25,0.30]},
    "S6_risk_parity": {"volatility_window_days":[40,60,80]},
}
BASE={
    "S1_momentum": {"lookback_months":12,"top_n":3},
    "S3_rotation": {"lookback_months":12,"top_n":3},
    "S4_moving_average": {"window_days":200},
    "S5_dynamic_allocation": {"lookback_months":12,"max_weight":0.25},
    "S6_risk_parity": {"volatility_window_days":60},
}

def evaluate(prices, execution, cfg, targets, signals):
    invest_targets={k:v for k,v in targets.items() if k!="CASH"}
    invest_total=sum(invest_targets.values())
    rows=[]
    for name,sig in signals.items():
        if name not in BASE: continue
        sig=sig.copy()
        if invest_total<1:
            sig=sig*invest_total
        eq,turn,trades=simulate(
            prices,sig,float(cfg["portfolio"]["initial_capital"]),
            float(cfg["portfolio"]["monthly_contribution"]),
            cfg["costs"]["commission_bps"],cfg["costs"]["slippage_bps"],
            invest_contributions=True,rebalance=True,execution_prices=execution)
        if eq.empty: continue
        m=summarize(eq["equity"],turnover=turn,trades=trades,
                    external_cashflows=eq["contribution"],
                    initial_capital=float(cfg["portfolio"]["initial_capital"]),
                    cash=eq["cash"])
        rows.append({"strategy":name,**m})
    return rows

def signal_variant(prices,cfg,name,params):
    c={**cfg}
    c["strategies"]={k:dict(v) for k,v in cfg["strategies"].items()}
    if name=="S1_momentum":
        c["strategies"]["momentum"].update(params)
    elif name=="S3_rotation":
        c["strategies"]["rotation"].update(params)
    elif name=="S4_moving_average":
        c["strategies"]["moving_average"].update({"window_days":params["window_days"]})
    elif name=="S5_dynamic_allocation":
        c["strategies"]["dynamic_allocation"].update(params)
    elif name=="S6_risk_parity":
        c["strategies"]["risk_parity"].update({"volatility_window_days":params["volatility_window_days"]})
    return _signals(prices,load_targets(cfg),c)[name]

def main():
    cfg=load_config(CONFIG)
    prices,execution=prepare_price_matrices(TICKER_DIR)
    targets=load_targets(cfg)

    # Evaluate both histories. Parameter neighbors are Cartesian combinations
    # of pre-registered symmetric neighborhoods, not post-result selections.
    param_rows=[]
    for history_mode in ("common","expanding"):
        from history import common_history_start
        p=prices.copy(); x=execution.copy()
        if history_mode=="common":
            start=common_history_start(p)
            p=p.loc[p.index>=start]; x=x.reindex(p.index)
        for name,grid in BASELINES.items():
            keys=list(grid)
            for vals in itertools.product(*(grid[k] for k in keys)):
                params=dict(zip(keys,vals))
                sig=signal_variant(p,cfg,name,params)
                rows=evaluate(p,x,cfg,targets,{name:sig})
                if rows:
                    r=rows[0]
                    r.update({"history_mode":history_mode,**params,
                              "is_baseline":params==BASE[name]})
                    param_rows.append(r)
    pd.DataFrame(param_rows).to_csv(ROOT/"parameter_neighbor_sensitivity_ci.csv",index=False)

    # Universe sensitivity: leave one investable asset out at a time, while
    # preserving the same cash reserve and proportionally renormalizing the
    # remaining target weights. This measures dependence on individual assets.
    uni_rows=[]
    assets=[a for a in targets if a!="CASH"]
    for history_mode in ("common","expanding"):
        from history import common_history_start
        p=prices.copy(); x=execution.copy()
        if history_mode=="common":
            start=common_history_start(p)
            p=p.loc[p.index>=start]; x=x.reindex(p.index)
        for omitted in [None]+assets:
            t=dict(targets)
            p_test=p.copy()
            x_test=x.copy()
            if omitted is not None:
                t.pop(omitted,None)
                # True leave-one-asset-out: the omitted asset must be absent
                # from both the signal universe and the execution matrix.
                p_test=p_test.drop(columns=[omitted], errors="ignore")
                x_test=x_test.drop(columns=[omitted], errors="ignore")
            invest=[k for k in t if k!="CASH"]
            invest_sum=sum(t[k] for k in invest)
            target_invest=sum(targets[k] for k in assets)
            if invest_sum<=0: continue
            # Keep original 5% cash; rescale only remaining investable weights
            # to the original 95% investable budget.
            scale=target_invest/invest_sum
            for k in invest: t[k]*=scale
            sigs=_signals(p_test,t,cfg)
            rows=evaluate(p_test,x_test,cfg,t,sigs)
            for r in rows:
                r.update({"history_mode":history_mode,
                          "omitted_asset":"NONE" if omitted is None else omitted})
                uni_rows.append(r)
    pd.DataFrame(uni_rows).to_csv(ROOT/"universe_sensitivity_ci.csv",index=False)

    # Compact summaries: dispersion around the frozen baseline, not a ranking.
    ps=pd.DataFrame(param_rows)
    us=pd.DataFrame(uni_rows)
    lines=["PHASE1_SENSITIVITY","parameter_neighbor_test=PRE_REGISTERED_NO_TUNING",
           "universe_test=LEAVE_ONE_ASSET_OUT_NO_TUNING"]
    for name in BASE:
        z=ps[ps.strategy==name]
        b=z[z.is_baseline]
        lines.append(f"\n{name}")
        for mode in ("common","expanding"):
            a=z[z.history_mode==mode]
            bb=b[b.history_mode==mode]
            if len(a) and len(bb):
                for metric in ("CAGR","Sharpe","max_drawdown"):
                    lines.append(f"{mode}_{metric}_baseline={float(bb[metric].iloc[0]):.6f}_neighbor_min={float(a[metric].min()):.6f}_neighbor_max={float(a[metric].max()):.6f}")
    (ROOT/"phase1_sensitivity_summary.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    main()
