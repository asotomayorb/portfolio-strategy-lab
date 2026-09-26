"""Phase 2E frozen robustness, generalization and uncertainty suite."""
from __future__ import annotations
import importlib.util
import json
import math
import shutil
import tempfile
import urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ENGINE_SOURCE = ROOT / "scripts" / "run_phase2a.py"
STRATS = [
    "S1_DCA50_Dip50",
    "S2_DCA50_ATR8_50",
    "S3_DCA50_Dip25_ATR8_25",
    "S4_ATR8_100_else_S1",
]
COSTS = [
    ("zero", 0.0, 0.0),
    ("commission_only", 10.0, 0.0),
    ("slippage_only", 0.0, 5.0),
    ("baseline", 10.0, 5.0),
    ("high", 20.0, 10.0),
    ("stress", 30.0, 20.0),
]
EXTERNAL = ["SPY","DIA","IWM","VGK","EEM","TLT","VNQ","XLV","XLP","XLU","XLI","HYG"]
HOLDOUT = ["VUG","VTV","VEA","BND","LQD","SHY","DBC","XLF","XLK","VOO"]
START = "2007-01-01"
END = "2026-09-24"
BOOT_BLOCKS = [3, 6, 12]
PRIMARY_BLOCK = 6
N_BOOT = 5000
SEED = 20260926

def load_engine(tag, commission=10.0, slippage=5.0, capture=True):
    src = ENGINE_SOURCE.read_text(encoding="utf-8")
    src = src.replace("0.0005", str(slippage / 10000.0))
    src = src.replace("0.0010", str(commission / 10000.0))
    if capture:
        marker = 'DISTS = ["D1_target_weighted", "D2_equal_weighted", "D3_deepest_first"]'
        src = src.replace(marker, marker + "\nCAPTURE = {}")
        marker2 = "            rows.append(dict(strategy=strat,distribution=distribution,history_mode=mode,"
        inject = '            CAPTURE[(mode, strat, distribution)] = pd.DataFrame({"equity":eq, "contribution":cf, "cash":cash_series})\n' + marker2
        src = src.replace(marker2, inject)
    path = ROOT / "scripts" / ("_phase2e_" + tag + ".py")
    path.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_phase2e_" + tag, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod, path

def metrics_from_series(frame):
    eq = frame["equity"].astype(float)
    cf = frame["contribution"].astype(float)
    denom = eq.shift(1) + cf
    r = (eq / denom - 1.0).where(denom > 0).replace([np.inf,-np.inf],np.nan).dropna()
    if len(r) == 0:
        return {"CAGR": np.nan, "Sharpe": np.nan, "Sortino": np.nan, "max_drawdown": np.nan}
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1/365.25)
    log_growth = np.log1p(r).sum()
    cagr = np.expm1(log_growth / years)
    sharpe = np.sqrt(252) * r.mean() / r.std() if r.std() > 0 else np.nan
    neg = r[r < 0]
    down = neg.std() if len(neg) > 1 else np.nan
    sortino = np.sqrt(252) * r.mean() / down if down and down > 0 else np.nan
    wealth = np.exp(np.log1p(r).cumsum())
    dd = wealth / wealth.cummax() - 1.0
    return {"CAGR": float(cagr), "Sharpe": float(sharpe), "Sortino": float(sortino), "max_drawdown": float(dd.min())}

def monthly_returns(frame):
    x = frame.copy()
    x["month"] = x.index.to_period("M")
    g = x.groupby("month")
    e = g["equity"].last()
    c = g["contribution"].sum()
    r = (e / (e.shift(1) + c) - 1.0).replace([np.inf,-np.inf],np.nan).dropna()
    return r

def circular_indices(n, block_len, rng):
    nblocks = int(math.ceil(n / block_len))
    starts = rng.integers(0, n, size=nblocks)
    idx = np.concatenate([(s + np.arange(block_len)) % n for s in starts])[:n]
    return idx

def bootstrap_metric(sample):
    wealth = np.cumprod(1.0 + sample)
    years = len(sample) / 12.0
    cagr = wealth[-1] ** (1.0 / years) - 1.0 if wealth[-1] > 0 else -1.0
    std = sample.std(ddof=1)
    sharpe = sample.mean() / std * np.sqrt(12.0) if std > 0 else np.nan
    peak = np.maximum.accumulate(wealth)
    dd = wealth / peak - 1.0
    return cagr, sharpe, float(dd.min())

def bootstrap_ci(arr):
    return np.quantile(arr, [0.025, 0.975]).tolist()

def run_engine(mod, mode, strategy="all", dist="D3_deepest_first"):
    return mod.run(mode, strategy=strategy, dist=dist)

def walkforward(captures):
    rows = []
    for (mode, strategy, dist), frame in captures.items():
        months = list(frame.index.to_period("M").unique())
        for fold in range(4):
            lo = len(months) * fold // 4
            hi = len(months) * (fold + 1) // 4
            if lo >= hi:
                continue
            part = frame[(frame.index.to_period("M") >= months[lo]) & (frame.index.to_period("M") <= months[hi-1])]
            m = metrics_from_series(part)
            rows.append({"history_mode":mode,"strategy":strategy,"distribution":dist,
                         "fold":fold+1,"fold_start":str(months[lo]),"fold_end":str(months[hi-1]),**m})
    return pd.DataFrame(rows)

def universe_test():
    base_mod, base_path = load_engine("universe_base")
    base = run_engine(base_mod, "common")
    targets = base_mod.load_targets()
    rows = []
    for omit in sorted(targets):
        mod, path = load_engine("universe_" + omit.lower())
        original_loader = mod.load_targets
        def loader(omit=omit, targets=targets):
            kept = {k:v for k,v in targets.items() if k != omit}
            scale = sum(kept.values()) / max(sum(targets.values()) - targets.get("CASH",0.0), 1e-12)
            return {k:v/scale for k,v in kept.items()}
        mod.load_targets = loader
        result = run_engine(mod, "common")
        for _, r in result.iterrows():
            b = base[(base.strategy == r.strategy) & (base.distribution == r.distribution)].iloc[0]
            rows.append({"omitted":omit,"strategy":r.strategy,
                         "CAGR":r.CAGR,"max_drawdown":r.max_drawdown,"Sharpe":r.Sharpe,
                         "Sortino":r.Sortino,"cash_utilization":r.cash_utilization,
                         "trades":r.trades,"delta_CAGR":r.CAGR-b.CAGR,
                         "delta_max_drawdown":r.max_drawdown-b.max_drawdown,
                         "delta_Sharpe":r.Sharpe-b.Sharpe})
        path.unlink(missing_ok=True)
    base_path.unlink(missing_ok=True)
    return pd.DataFrame(rows)

def cost_test():
    rows = []
    for name, commission, slippage in COSTS:
        mod, path = load_engine("cost_" + name, commission, slippage, capture=False)
        for mode in ("common","expanding"):
            result = run_engine(mod, mode)
            result["scenario"] = name
            result["commission_bps"] = commission
            result["slippage_bps"] = slippage
            rows.append(result)
        path.unlink(missing_ok=True)
    return pd.concat(rows, ignore_index=True)

def fetch_yahoo(symbol, outdir):
    p1 = int(pd.Timestamp(START, tz="UTC").timestamp())
    p2 = int((pd.Timestamp(END, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol +
        "?period1=" + str(p1) + "&period2=" + str(p2) +
        "&interval=1d&events=div%7Csplit&includeAdjustedClose=true"
    )
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 portfolio-strategy-lab"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)["chart"]["result"][0]
    q = result["indicators"]["quote"][0]
    frame = pd.DataFrame({
        "Date": pd.to_datetime(result["timestamp"], unit="s").date,
        "Open": q["open"], "High": q["high"], "Low": q["low"], "Close": q["close"],
    }).dropna(subset=["Open","High","Low","Close"])
    frame["Date"] = frame["Date"].astype(str)
    frame = frame[(frame["Date"] >= START) & (frame["Date"] <= END)]
    frame.to_csv(outdir / (symbol + ".csv"), index=False)
    return {"ticker":symbol,"first":frame["Date"].iloc[0] if len(frame) else None,
            "last":frame["Date"].iloc[-1] if len(frame) else None,"rows":len(frame)}

def external_test(name, tickers):
    root = Path(tempfile.mkdtemp(prefix="phase2e_" + name + "_"))
    data_dir = root / "tickers"
    data_dir.mkdir()
    coverage = []
    try:
        for t in tickers:
            coverage.append(fetch_yahoo(t, data_dir))
        alloc = root / "allocation.csv"
        w = 0.95 / len(tickers)
        pd.DataFrame({"Ticker":tickers,"Allocation %":[f"{w*100:.10f}%"]*len(tickers)}).to_csv(alloc,index=False)
        mod, path = load_engine("external_" + name, capture=False)
        mod.TICKER_DIR = data_dir
        mod.ALLOC = alloc
        result = run_engine(mod, "expanding")
        result["validation_type"] = name
        result["universe"] = ",".join(tickers)
        return result, pd.DataFrame(coverage)
    finally:
        shutil.rmtree(root, ignore_errors=True)

def statistical_test():
    mod, path = load_engine("bootstrap")
    rng = np.random.default_rng(SEED)
    rows = []
    pairs = []
    for mode in ("common","expanding"):
        run_engine(mod, mode)
        for block in BOOT_BLOCKS:
            samples = {}
            metrics_by = {}
            for strategy in STRATS:
                frame = mod.CAPTURE[(mode,strategy,"D3_deepest_first")]
                r = monthly_returns(frame).to_numpy(dtype=float)
                arr = np.empty((N_BOOT,len(r)))
                for i in range(N_BOOT):
                    arr[i] = r[circular_indices(len(r),block,rng)]
                samples[strategy] = arr
                vals = np.array([bootstrap_metric(x) for x in arr])
                metrics_by[strategy] = vals
                point = np.array(bootstrap_metric(r))
                for j,name in enumerate(["CAGR","Sharpe","max_drawdown"]):
                    lo,hi=bootstrap_ci(vals[:,j])
                    rows.append({"history_mode":mode,"block_months":block,"strategy":strategy,
                                 "metric":name,"point_estimate":point[j],
                                 "ci95_low":lo,"ci95_high":hi,"n_boot":N_BOOT,"seed":SEED})
            base = samples[STRATS[0]]
            for strategy in STRATS[1:]:
                a=samples[strategy]
                diff=np.array([bootstrap_metric(x)[0] for x in a])-np.array([bootstrap_metric(x)[0] for x in base])
                lo,hi=bootstrap_ci(diff)
                pairs.append({"history_mode":mode,"block_months":block,
                              "strategy_a":strategy,"strategy_b":STRATS[0],
                              "point_estimate":bootstrap_metric(monthly_returns(mod.CAPTURE[(mode,strategy,"D3_deepest_first")]).to_numpy())[0]-bootstrap_metric(monthly_returns(mod.CAPTURE[(mode,STRATS[0],"D3_deepest_first")]).to_numpy())[0],
                              "ci95_low":lo,"ci95_high":hi,
                              "bootstrap_prob_a_gt_b":float(np.mean(diff>0)),
                              "n_boot":N_BOOT,"seed":SEED})
    path.unlink(missing_ok=True)
    return pd.DataFrame(rows), pd.DataFrame(pairs)

def main():
    out = ROOT / "reports" / "phase2e"
    out.mkdir(parents=True, exist_ok=True)

    # A: temporal robustness and F: uncertainty use one captured baseline engine.
    mod, path = load_engine("baseline")
    captures = {}
    for mode in ("common","expanding"):
        run_engine(mod, mode)
    captures = dict(mod.CAPTURE)
    wf = walkforward(captures)
    wf.to_csv(out / "walkforward.csv", index=False)

    # B: leave-one-asset-out.
    univ = universe_test()
    univ.to_csv(out / "universe_leave_one_out.csv", index=False)

    # C: friction sensitivity.
    costs = cost_test()
    costs.to_csv(out / "cost_sensitivity.csv", index=False)

    # D/E: external and newly reserved holdout.
    ext, ext_cov = external_test("external_generalization", EXTERNAL)
    ext.to_csv(out / "external_generalization.csv", index=False)
    ext_cov.to_csv(out / "external_coverage.csv", index=False)
    hold, hold_cov = external_test("reserved_holdout", HOLDOUT)
    hold.to_csv(out / "reserved_holdout.csv", index=False)
    hold_cov.to_csv(out / "reserved_holdout_coverage.csv", index=False)

    # F: bootstrap uncertainty.
    boot, pairs = statistical_test()
    boot.to_csv(out / "bootstrap_uncertainty.csv", index=False)
    pairs.to_csv(out / "bootstrap_pairwise_cagr.csv", index=False)

    summary = [
        "PHASE 2E ROBUSTNESS SUITE",
        "protocol=docs/PHASE2E_PROTOCOL.txt",
        "candidate_set=S1-S4; D3; 5% cash floor; zero initial capital; USD 1000 monthly",
        "walk_forward=4 chronological folds; common and expanding",
        "universe=leave-one-asset-out with proportional target renormalization",
        "costs=0/0,10/0,0/5,10/5,20/10,30/20 bps",
        "external=12-ETF generalization",
        "reserved_holdout=10-ETF newly frozen universe",
        "bootstrap=3/6/12 months; primary 6; 5000 replicates; seed 20260926",
        "No selection or definition changes are performed by this script.",
    ]
    (out / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    path.unlink(missing_ok=True)
    print("\n".join(summary))

if __name__ == "__main__":
    main()
