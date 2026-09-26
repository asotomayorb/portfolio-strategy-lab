"""Phase 1 reserved holdout.

The ticker set below has not been used in the prior Phase 1 evaluations.
It is frozen before execution and must not be used to change any strategy
definition, parameter, cadence, cost assumption or selection rule.
"""
from __future__ import annotations
import json, tempfile, urllib.request
from pathlib import Path
import sys
import pandas as pd, yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from experiment import run_phase1

TICKERS=["VTI","MDY","EFA","IAU","AGG","IEF","TIP","EMB","XLB","XLY"]
START="2007-01-01"; END="2026-09-24"; CASH=0.05

def fetch(symbol,out):
    url=(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
         f"?period1={int(pd.Timestamp(START,tz='UTC').timestamp())}"
         f"&period2={int((pd.Timestamp(END,tz='UTC')+pd.Timedelta(days=1)).timestamp())}"
         "&interval=1d&events=div%7Csplit&includeAdjustedClose=true")
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 portfolio-strategy-lab"})
    with urllib.request.urlopen(req,timeout=30) as resp:
        result=json.load(resp)["chart"]["result"][0]
    q=result["indicators"]["quote"][0]
    frame=pd.DataFrame({"Date":pd.to_datetime(result["timestamp"],unit="s",utc=True).date,
                        "Open":q["open"],"High":q["high"],"Low":q["low"],
                        "Close":q["close"],"Volume":q["volume"]}).dropna(subset=["Open","High","Low","Close"])
    frame["Date"]=frame["Date"].astype(str)
    frame=frame[(frame.Date>=START)&(frame.Date<=END)]
    if frame.empty: raise RuntimeError(f"{symbol}: no data")
    frame.to_csv(out,index=False)
    return frame.Date.iloc[0],frame.Date.iloc[-1],len(frame)

def main():
    alloc=ROOT/"reserved_holdout_allocation_ci.csv"
    try:
        with tempfile.TemporaryDirectory() as td:
            data=Path(td)/"tickers"; data.mkdir()
            coverage=[]
            for t in TICKERS:
                a,b,n=fetch(t,data/f"{t}.csv"); coverage.append({"ticker":t,"first":a,"last":b,"rows":n})
            w=(1-CASH)/len(TICKERS)
            pd.DataFrame({"Ticker":TICKERS+["cash"],
                          "Allocation %":[f"{w*100:.10f}%"]*len(TICKERS)+[f"{CASH*100:.10f}%"]}).to_csv(alloc,index=False)
            cfg=yaml.safe_load((ROOT/"config/phase1.yaml").read_text())
            cfg["portfolio"]["allocation_file"]=str(alloc)
            cfg["dataset_version"]="reserved-holdout-yahoo-v1"
            cfg["config_version"]="v3-reserved-holdout-frozen"
            cp=Path(td)/"phase1_holdout.yaml"; cp.write_text(yaml.safe_dump(cfg,sort_keys=False))
            result=run_phase1(ticker_dir=data,cfg_path=cp,history_mode="expanding")
            result.to_csv(ROOT/"reserved_holdout_results_ci.csv",index=False)
            pd.DataFrame(coverage).to_csv(ROOT/"reserved_holdout_data_coverage_ci.csv",index=False)
            with open(ROOT/"reserved_holdout_summary.txt","w") as f:
                f.write("PHASE 1 RESERVED HOLDOUT\n========================\n")
                f.write(f"Window: {START} to {END}\nUniverse: {', '.join(TICKERS)}\n")
                f.write("Allocation: 95% invested equal-weight; 5% cash\n")
                f.write("Source: Yahoo Finance daily chart OHLCV at CI runtime\n")
                f.write("Status: reserved ticker-universe holdout; results must not alter frozen strategy definitions.\n\n")
                f.write(result[["strategy","CAGR","max_drawdown","Sharpe","Sortino"]].to_string(index=False))
                f.write("\n\nCoverage:\n"+pd.DataFrame(coverage).to_string(index=False)+"\n")
            print(result[["strategy","CAGR","max_drawdown","Sharpe","Sortino"]].to_string(index=False))
    finally:
        if alloc.exists(): alloc.unlink()

if __name__=="__main__": main()
