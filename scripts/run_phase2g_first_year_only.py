"""Phase 2G: contribute USD 1,000/month for 12 months, then hold for ~9 years.

This is a post-Phase-2 descriptive extension. Frozen S1-S4 definitions are reused
without modification and no rebalancing overlay is applied.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_loader import load_csv_folder

LEVELS = {1.5: 0.25, 3.0: 0.50, 5.0: 0.75, 8.0: 1.00}
STRATS = ["S1_DCA50_Dip50", "S2_DCA50_ATR8_50",
          "S3_DCA50_Dip25_ATR8_25", "S4_ATR8_100_else_S1"]

def load_ohlc():
    assets = load_csv_folder(ROOT / "tickers")
    out = {}
    for t, a in assets.items():
        f = a.frame.set_index("Date")
        out[t] = f[["Open","High","Low","Close"]].where(f["ohlc_valid"])
    return out

def load_targets():
    f = pd.read_csv(ROOT / "portfolio_allocation.csv")
    out = {}
    for _, r in f.iterrows():
        t = str(r["Ticker"]).strip().upper()
        if t in ("CASH","CASHUSD","CASH USD"): continue
        if t == "BTCUSD": t = "BTC"
        out[t] = float(str(r["Allocation %"]).replace("%","").replace(",","."))/100
    return out

def weekly_indicators(frame):
    w = frame.resample("W-FRI").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna(subset=["High","Low","Close"])
    pc = w["Close"].shift(1)
    tr = pd.concat([(w["High"]-w["Low"]).abs(), (w["High"]-pc).abs(),
                    (w["Low"]-pc).abs()], axis=1).max(axis=1)
    atr = pd.Series(np.nan, index=w.index)
    if len(tr) >= 20:
        atr.iloc[19] = tr.iloc[:20].mean()
        for i in range(20, len(tr)):
            atr.iloc[i] = (atr.iloc[i-1]*19 + tr.iloc[i]) / 20.0
    swing = pd.Series(False, index=w.index)
    highs = w["High"].values
    for i in range(3, len(w)-3):
        win = highs[i-3:i+4]
        if np.isfinite(win).all() and highs[i] == win.max() and (win == highs[i]).sum() == 1:
            swing.iloc[i] = True
    confirmed = []
    for i in range(len(w)):
        if i >= 3 and swing.iloc[i-3]:
            confirmed.append((w.index[i], float(w["High"].iloc[i-3])))
    hh = pd.Series(np.nan, index=w.index)
    for dt,_ in confirmed:
        vals = [v for cdt,v in confirmed if cdt <= dt and cdt >= dt-pd.Timedelta(weeks=52)]
        if vals: hh.loc[dt] = max(vals)
    return hh.ffill(), atr.ffill()

def build_features(ohlc):
    out = {}
    for t,f in ohlc.items():
        hh,atr = weekly_indicators(f)
        d = pd.DataFrame(index=f.index)
        week = f.index.to_period("W-FRI").to_timestamp(how="end").normalize()
        prior = pd.Series(week,index=f.index).map(lambda x:x-pd.Timedelta(weeks=1))
        d["HH52"] = prior.map(hh)
        d["ATR20W"] = prior.map(atr)
        d["Low"] = f["Low"]; d["Open"] = f["Open"]; d["Close"] = f["Close"]
        out[t] = d
    return out

def distribute(needs,budget):
    if budget <= 0 or not needs: return {}
    needs = {k:v for k,v in needs.items() if v["need"] > 0}
    out = {k:0.0 for k in needs}; left = budget
    for level in sorted({v["level"] for v in needs.values()}, reverse=True):
        group = {k:v for k,v in needs.items() if v["level"] == level}
        if left <= 1e-9: break
        s = sum(v["target"] for v in group.values())
        used = 0.0
        for k,v in group.items():
            a = min(v["need"], left*v["target"]/s if s else 0.0)
            out[k] += a; used += a
        left -= used
    return out

def cohort_starts(dates):
    dates = pd.DatetimeIndex(sorted(dates))
    candidates = []
    for year in range(int(dates.min().year), int(dates.max().year)-9):
        anchor = pd.Timestamp(year=year, month=1, day=1)
        starts = dates[dates >= anchor]
        if len(starts):
            start = starts[0]
            end_target = start + pd.DateOffset(years=10)
            ends = dates[dates >= end_target]
            if len(ends): candidates.append(start)
    recent_anchor = dates.max() - pd.DateOffset(years=10)
    recent = dates[dates >= recent_anchor]
    if len(recent):
        candidates.append(recent[0])
    return sorted(set(candidates))

def run_cohort(start, end, strategy, ohlc, feats, targets):
    assets = [t for t in targets if t in ohlc]
    dates = sorted(set().union(*[set(feats[t].index) for t in assets]))
    dates = pd.DatetimeIndex([d for d in dates if start <= d <= end])
    if len(dates) < 200: return None

    cash=0.0; shares={t:0.0 for t in assets}; pending=[]
    last_close={t:np.nan for t in assets}; daily=[]; contribution_total=0.0
    contribution_dates=[]

    # First 12 calendar months beginning with the cohort start month.
    contribution_months = set((start + pd.DateOffset(months=i)).to_period("M") for i in range(12))

    for i,d in enumerate(dates):
        if pending:
            nxt=[]
            for o in pending:
                t=o["ticker"]; px=ohlc[t]["Open"].get(d,np.nan)
                if not np.isfinite(px) or px <= 0:
                    nxt.append(o); continue
                gross=min(o["amount"], max(0.0,cash)/1.001)
                if gross > 1e-8:
                    cash -= gross*1.001
                    shares[t] += gross/(px*1.0005)
            pending=nxt

        prev=dates[i-1] if i else None
        month_start = prev is None or d.to_period("M") != prev.to_period("M")
        contribute = month_start and d.to_period("M") in contribution_months
        if contribute:
            cash += 1000.0
            contribution_total += 1000.0
            contribution_dates.append(d)

        for t in assets:
            px=ohlc[t]["Close"].get(d,np.nan)
            if np.isfinite(px) and px>0: last_close[t]=float(px)
        prices=last_close.copy()
        equity=cash+sum(shares[t]*prices[t] for t in assets if np.isfinite(prices[t]))
        floor=0.05*equity
        available=max(0.0,cash-floor)

        pending_buy={}
        for o in pending:
            if o["side"]=="buy": pending_buy[o["ticker"]]=pending_buy.get(o["ticker"],0.0)+o["amount"]

        # DCA only during the first contribution year.
        if contribute and available > 0:
            dca=500.0
            eligible={t:max(0.0,targets[t]*equity-shares[t]*prices[t]-pending_buy.get(t,0.0))
                      for t in assets if np.isfinite(ohlc[t]["Open"].get(d,np.nan))}
            eligible={t:n for t,n in eligible.items() if n>0}
            total=sum(eligible.values())
            if total>0:
                used=min(dca,available)
                for t,n in eligible.items():
                    a=min(n,used*n/total)
                    if a>1e-9: pending.append({"ticker":t,"side":"buy","amount":a})

        pending_buy={}
        for o in pending:
            if o["side"]=="buy": pending_buy[o["ticker"]]=pending_buy.get(o["ticker"],0.0)+o["amount"]

        # Frozen daily trigger logic.
        needs={}; active8=[]
        for t in assets:
            if d not in feats[t].index: continue
            hh=feats[t].at[d,"HH52"]; atr=feats[t].at[d,"ATR20W"]; low=feats[t].at[d,"Low"]
            if not(np.isfinite(hh) and np.isfinite(atr) and np.isfinite(low) and hh>0 and atr>0): continue
            trig=next((k for k in (8.0,5.0,3.0,1.5) if low <= hh-k*atr),None)
            if trig is None: continue
            if trig==8.0: active8.append(t)
            if strategy=="S2_DCA50_ATR8_50" and trig!=8.0:
                # No ATR8 today; S2 falls back to S1 opportunity behavior.
                pass
            if strategy in ("S1_DCA50_Dip50","S2_DCA50_ATR8_50","S3_DCA50_Dip25_ATR8_25","S4_ATR8_100_else_S1"):
                need=max(0.0,targets[t]*equity*LEVELS[trig]-shares[t]*prices[t]-pending_buy.get(t,0.0))
                if need>0: needs[t]={"need":need,"level":trig,"target":targets[t]}

        pending_buy={}
        for o in pending:
            if o["side"]=="buy": pending_buy[o["ticker"]]=pending_buy.get(o["ticker"],0.0)+o["amount"]
        available_dip=max(0.0,available-sum(o["amount"] for o in pending if o["side"]=="buy"))

        if strategy=="S4_ATR8_100_else_S1" and active8:
            n={}
            for t in active8:
                need=max(0.0,targets[t]*equity-shares[t]*prices[t]-pending_buy.get(t,0.0))
                if need>0: n[t]={"need":need,"level":8.0,"target":targets[t]}
            buys=distribute(n,available_dip)
        elif strategy=="S2_DCA50_ATR8_50" and active8:
            n={}
            for t in active8:
                need=max(0.0,targets[t]*equity-shares[t]*prices[t]-pending_buy.get(t,0.0))
                if need>0: n[t]={"need":need,"level":8.0,"target":targets[t]}
            buys=distribute(n,available_dip*0.50)
        elif strategy=="S3_DCA50_Dip25_ATR8_25":
            if not active8:
                # No ATR8 anywhere today: exact S1 opportunity behavior.
                buys=distribute(needs,available_dip*0.50)
            else:
                a=distribute(needs,available_dip*0.25)
                n={t:v for t,v in needs.items() if v["level"]==8}
                b=distribute(n,available_dip*0.25); buys={}
                for t,x in a.items(): buys[t]=buys.get(t,0)+x
                for t,x in b.items(): buys[t]=buys.get(t,0)+x
        else:
            buys=distribute(needs,available_dip*0.50)

        for t,a in buys.items():
            room=max(0.0,targets[t]*equity-shares[t]*prices[t]-pending_buy.get(t,0.0))
            if a>1e-9: pending.append({"ticker":t,"side":"buy","amount":min(a,room)})

        cash_after=max(0.0,cash-sum(o["amount"] for o in pending if o["side"]=="buy"))
        daily.append((d,equity,cash_after,1000.0 if contribute else 0.0))

    eq=pd.Series({d:e for d,e,_,_ in daily}).sort_index()
    cf=pd.Series({d:c for d,_,_,c in daily}).sort_index()
    cash_s=pd.Series({d:c for d,_,c,_ in daily}).sort_index()
    den=eq.shift(1)+cf
    ret=(eq/den-1.0).where(den>0).replace([np.inf,-np.inf],np.nan).dropna()
    if len(ret)==0 or not contribution_dates: return None

    final_contrib=contribution_dates[-1]
    post_ret=ret[ret.index >= final_contrib]
    years_total=max((eq.index[-1]-eq.index[0]).days/365.25,1/365.25)
    years_post=max((eq.index[-1]-final_contrib).days/365.25,1/365.25)
    total_cagr=float(np.expm1(np.log1p(ret).sum()/years_total))
    post_cagr=float(np.expm1(np.log1p(post_ret).sum()/years_post))
    lw=np.log1p(ret).cumsum()
    dd=np.expm1(lw-lw.cummax())
    sharpe=float(np.sqrt(252)*ret.mean()/ret.std()) if ret.std()>0 else np.nan
    return dict(strategy=strategy,cohort_start=eq.index[0],cohort_end=eq.index[-1],
                contribution_end=final_contrib,hold_years=years_post,
                contributions=contribution_total,contribution_year_end=float(eq.loc[final_contrib]),
                final_equity=float(eq.iloc[-1]),final_multiple=float(eq.iloc[-1]/contribution_total),
                total_TWR_CAGR=total_cagr,post_contribution_CAGR=post_cagr,
                max_drawdown=float(dd.min()),Sharpe=sharpe,
                cash_utilization=float((1-cash_s/eq.replace(0,np.nan)).mean()))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="reports/phase2g_first_year_only.csv")
    a=p.parse_args()
    targets=load_targets(); all_ohlc=load_ohlc()
    assets=[t for t in targets if t in all_ohlc]
    ohlc={t:all_ohlc[t] for t in assets}
    feats=build_features(ohlc)
    all_dates=sorted(set().union(*[set(f.index) for f in feats.values()]))
    starts=cohort_starts(all_dates)
    rows=[]
    for start in starts:
        end_target=start+pd.DateOffset(years=10)
        end_candidates=pd.DatetimeIndex(all_dates)
        end=end_candidates[end_candidates>=end_target]
        if len(end)==0: continue
        end=end[0]
        for strat in STRATS:
            r=run_cohort(start,end,strat,ohlc,feats,targets)
            if r: rows.append(r)
    result=pd.DataFrame(rows).sort_values(["cohort_start","strategy"])
    out=ROOT/a.output; out.parent.mkdir(parents=True,exist_ok=True)
    result.to_csv(out,index=False)

    summary=result.groupby("strategy").agg(
        cohorts=("post_contribution_CAGR","count"),
        median_post_CAGR=("post_contribution_CAGR","median"),
        mean_post_CAGR=("post_contribution_CAGR","mean"),
        min_post_CAGR=("post_contribution_CAGR","min"),
        max_post_CAGR=("post_contribution_CAGR","max"),
        median_final_multiple=("final_multiple","median"),
        median_final_equity=("final_equity","median"),
        median_max_drawdown=("max_drawdown","median"),
        median_total_TWR_CAGR=("total_TWR_CAGR","median"),
    ).reset_index()

    report=ROOT/"reports/PHASE2G_FIRST_YEAR_ONLY_2026-09-27.txt"
    lines=[
        "PHASE 2G — FIRST-YEAR CONTRIBUTIONS / NINE-YEAR HOLD",
        "Generated from the repository workflow; descriptive historical research only.",
        "",
        f"Cohorts tested: {len(starts)}",
        "Contribution schedule: USD 1,000 on the first observed trading day of each of the first 12 calendar months; then zero.",
        "Total contributions per cohort: USD 12,000.",
        "Horizon: approximately 10 years.",
        "",
        "POST-CONTRIBUTION CAGR SUMMARY",
        summary.to_string(index=False),
        "",
        "Interpretation guardrails:",
        "- post_contribution_CAGR measures annualized growth after the final contribution and is not the CAGR of the contribution phase.",
        "- final_multiple is final equity divided by the USD 12,000 nominal contributions.",
        "- Cohort dispersion is historical; it is not a forecast or an expected return.",
        "- A lump-sum-at-day-one scenario remains a separate sensitivity.",
        "",
        "COHORT RESULTS",
        result.to_string(index=False),
    ]
    report.write_text("\n".join(lines),encoding="utf-8")
    print(result.to_string(index=False))
    print("\nSUMMARY")
    print(summary.to_string(index=False))
    print(f"\nWrote {out}")
    print(f"Wrote {report}")

if __name__=="__main__":
    main()
