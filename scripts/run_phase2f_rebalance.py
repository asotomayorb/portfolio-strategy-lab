"""Post-Phase-2 hybrid rebalancing sensitivity.

Separate extension after the frozen Phase 2E gate. The frozen Phase 2 engine and
definitions are not modified.

Modes:
- baseline: no rebalancing overlay.
- hybrid20: use the monthly DCA contribution to correct underweights first;
  sell existing holdings only when weight is >20% above target.
- hybrid30: same with a >30% relative-overweight threshold.

The 50% DCA / remaining dip-or-ATR8 split, D3 deepest-first allocation,
5% cash floor, next-session-open execution and 10 bps + 5 bps costs are kept.
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
MODES = {"baseline": None, "hybrid20": 0.20, "hybrid30": 0.30}

def load_ohlc():
    assets = load_csv_folder(ROOT / "tickers")
    return {t: a.frame.set_index("Date")[["Open","High","Low","Close"]].where(a.frame.set_index("Date")["ohlc_valid"])
            for t,a in assets.items()}

def load_targets():
    f = pd.read_csv(ROOT / "portfolio_allocation.csv")
    out = {}
    for _,r in f.iterrows():
        t = str(r["Ticker"]).strip().upper()
        if t in ("CASH","CASHUSD","CASH USD"): continue
        if t == "BTCUSD": t = "BTC"
        out[t] = float(str(r["Allocation %"]).replace("%","").replace(",","."))/100
    return out

def weekly_indicators(frame):
    w = frame.resample("W-FRI").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna(subset=["High","Low","Close"])
    pc = w["Close"].shift(1)
    tr = pd.concat([(w["High"]-w["Low"]).abs(),(w["High"]-pc).abs(),(w["Low"]-pc).abs()],axis=1).max(axis=1)
    atr = pd.Series(np.nan,index=w.index)
    if len(tr) >= 20:
        atr.iloc[19] = tr.iloc[:20].mean()
        for i in range(20,len(tr)): atr.iloc[i] = (atr.iloc[i-1]*19+tr.iloc[i])/20.0
    swing = pd.Series(False,index=w.index)
    highs = w["High"].values
    for i in range(3,len(w)-3):
        win = highs[i-3:i+4]
        if np.isfinite(win).all() and highs[i] == win.max() and (win == highs[i]).sum() == 1:
            swing.iloc[i] = True
    confirmed=[]
    for i in range(len(w)):
        if i >= 3 and swing.iloc[i-3]:
            confirmed.append((w.index[i],float(w["High"].iloc[i-3])))
    hh=pd.Series(np.nan,index=w.index)
    for dt,_ in confirmed:
        vals=[v for cdt,v in confirmed if cdt<=dt and cdt>=dt-pd.Timedelta(weeks=52)]
        if vals: hh.loc[dt]=max(vals)
    return hh.ffill(),atr.ffill()

def build_features(ohlc):
    out={}
    for t,f in ohlc.items():
        hh,atr=weekly_indicators(f)
        d=pd.DataFrame(index=f.index)
        week=f.index.to_period("W-FRI").to_timestamp(how="end").normalize()
        prior=pd.Series(week,index=f.index).map(lambda x:x-pd.Timedelta(weeks=1))
        d["HH52"]=prior.map(hh); d["ATR20W"]=prior.map(atr)
        d["Low"]=f["Low"]; d["Open"]=f["Open"]; d["Close"]=f["Close"]
        out[t]=d
    return out

def distribute(needs,budget):
    if budget<=0 or not needs: return {}
    needs={k:v for k,v in needs.items() if v["need"]>0}
    out={k:0.0 for k in needs}; left=budget
    for level in sorted({v["level"] for v in needs.values()},reverse=True):
        group={k:v for k,v in needs.items() if v["level"]==level}
        if left<=1e-9: break
        s=sum(v["target"] for v in group.values())
        used=0.0
        for k,v in group.items():
            a=min(v["need"],left*v["target"]/s if s else 0.0)
            out[k]+=a; used+=a
        left-=used
    return out

def metrics(eq,cf,cash_s,strategy,mode,history,contrib,sells,turnover):
    den=eq.shift(1)+cf
    ret=(eq/den-1).where(den>0).replace([np.inf,-np.inf],np.nan).dropna()
    if len(ret)==0: return None
    years=max((eq.index[-1]-eq.index[0]).days/365.25,1/365.25)
    lg=float(np.log1p(ret).sum())
    cagr=float(np.expm1(lg/years))
    lw=np.log1p(ret).cumsum()
    dd=np.expm1(lw-lw.cummax())
    return dict(strategy=strategy,rebalance_mode=mode,history_mode=history,
                start=eq.index[0],end=eq.index[-1],final_equity=float(eq.iloc[-1]),
                CAGR=cagr,max_drawdown=float(dd.min()),Sharpe=float(np.sqrt(252)*ret.mean()/ret.std()) if ret.std()>0 else np.nan,
                cash_utilization=float((1-cash_s/eq.replace(0,np.nan)).mean()),
                contributions=contrib,sell_trades=sells,rebalance_turnover=turnover)

def run(history,mode):
    targets=load_targets(); all_ohlc=load_ohlc()
    assets=[t for t in targets if t in all_ohlc]
    ohlc={t:all_ohlc[t] for t in assets}; feats=build_features(ohlc)
    dates=sorted(set().union(*[set(f.index) for f in feats.values()]))
    if history=="common":
        start=max(next(iter(f.index)) for f in feats.values())
        dates=[d for d in dates if d>=start]
    dates=pd.DatetimeIndex(dates)
    threshold=MODES[mode]; rows=[]

    for strat in STRATS:
        cash=0.0; shares={t:0.0 for t in assets}; pending=[]
        last_close={t:np.nan for t in assets}; contribution_total=0.0
        sell_trades=0; turnover=0.0; daily=[]
        for i,d in enumerate(dates):
            # Previous orders execute at today's open.
            if pending:
                nxt=[]
                for o in pending:
                    t=o["ticker"]; px=ohlc[t]["Open"].get(d,np.nan)
                    if not np.isfinite(px) or px<=0:
                        nxt.append(o); continue
                    if o["side"]=="buy":
                        gross=min(o["amount"],max(0.0,cash)/1.001)
                        if gross>1e-8:
                            cash-=gross*1.001
                            shares[t]+=gross/(px*1.0005)
                    else:
                        gross=min(o["amount"],shares[t]*px*0.9995)
                        if gross>1e-8:
                            shares[t]-=gross/(px*0.9995)
                            cash+=gross*0.999
                            sell_trades+=1
                pending=nxt

            prev=dates[i-1] if i else None
            month_start=prev is None or d.to_period("M")!=prev.to_period("M")
            if month_start:
                cash+=1000.0; contribution_total+=1000.0

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

            # Existing holdings are sold only after a relative overweight threshold.
            if month_start and threshold is not None and equity>0:
                for t in assets:
                    p=prices[t]
                    if not np.isfinite(p) or p<=0 or targets[t]<=0: continue
                    current=shares[t]*p
                    if current/equity > targets[t]*(1+threshold):
                        excess=current-targets[t]*equity
                        if excess>0:
                            pending.append({"ticker":t,"side":"sell","amount":excess})
                            turnover+=excess/equity

            # Contribution-first correction: the frozen 50% DCA budget goes first
            # to the largest current target deficits; residual goes target-weighted.
            dca=500.0 if month_start else 0.0
            if dca>0 and available>0:
                deficits={}
                for t in assets:
                    p=prices[t]
                    if np.isfinite(p) and p>0:
                        need=max(0.0,targets[t]*equity-shares[t]*p-pending_buy.get(t,0.0))
                        if need>0: deficits[t]=need
                alloc={}; left=min(dca,available); total=sum(deficits.values())
                if total>0:
                    for t,n in deficits.items(): alloc[t]=min(n,left*n/total)
                    left-=sum(alloc.values())
                if left>1e-9:
                    eligible=[t for t in assets if targets[t]>0 and np.isfinite(ohlc[t]["Open"].get(d,np.nan))]
                    s=sum(targets[t] for t in eligible)
                    for t in eligible: alloc[t]=alloc.get(t,0.0)+(left*targets[t]/s if s else 0.0)
                for t,a in alloc.items():
                    room=max(0.0,targets[t]*equity-shares[t]*prices[t]-pending_buy.get(t,0.0))
                    if a>1e-9: pending.append({"ticker":t,"side":"buy","amount":min(a,room)})

            pending_buy={}
            for o in pending:
                if o["side"]=="buy": pending_buy[o["ticker"]]=pending_buy.get(o["ticker"],0.0)+o["amount"]

            # Frozen Phase 2 triggers and D3 deepest-first allocation.
            needs={}; active8=[]
            for t in assets:
                if d not in feats[t].index: continue
                hh=feats[t].at[d,"HH52"]; atr=feats[t].at[d,"ATR20W"]; low=feats[t].at[d,"Low"]
                if not(np.isfinite(hh) and np.isfinite(atr) and np.isfinite(low) and hh>0 and atr>0): continue
                trig=next((k for k in (8.0,5.0,3.0,1.5) if low<=hh-k*atr),None)
                if trig is None: continue
                if trig==8.0: active8.append(t)
                if strat=="S2_DCA50_ATR8_50" and trig!=8.0: continue
                if strat in ("S1_DCA50_Dip50","S3_DCA50_Dip25_ATR8_25","S4_ATR8_100_else_S1"):
                    need=max(0.0,targets[t]*equity*LEVELS[trig]-shares[t]*prices[t]-pending_buy.get(t,0.0))
                    if need>0: needs[t]={"need":need,"level":trig,"target":targets[t]}

            pending_buy={}
            for o in pending:
                if o["side"]=="buy": pending_buy[o["ticker"]]=pending_buy.get(o["ticker"],0.0)+o["amount"]
            available_dip=max(0.0,available-sum(o["amount"] for o in pending if o["side"]=="buy"))

            if strat=="S4_ATR8_100_else_S1" and active8:
                n={}
                for t in active8:
                    need=max(0.0,targets[t]*equity-shares[t]*prices[t]-pending_buy.get(t,0.0))
                    if need>0: n[t]={"need":need,"level":8.0,"target":targets[t]}
                buys=distribute(n,available_dip)
            elif strat=="S2_DCA50_ATR8_50":
                n={}
                for t in active8:
                    need=max(0.0,targets[t]*equity-shares[t]*prices[t]-pending_buy.get(t,0.0))
                    if need>0: n[t]={"need":need,"level":8.0,"target":targets[t]}
                buys=distribute(n,available_dip*0.50)
            elif strat=="S3_DCA50_Dip25_ATR8_25":
                a=distribute(needs,available_dip*0.25)
                n={t:v for t,v in needs.items() if v["level"]==8.0}
                b=distribute(n,available_dip*0.25); buys={}
                for t,x in a.items(): buys[t]=buys.get(t,0)+x
                for t,x in b.items(): buys[t]=buys.get(t,0)+x
            else:
                buys=distribute(needs,available_dip*0.50)

            for t,a in buys.items():
                room=max(0.0,targets[t]*equity-shares[t]*prices[t]-pending_buy.get(t,0.0))
                if a>1e-9: pending.append({"ticker":t,"side":"buy","amount":min(a,room)})

            cash_after=max(0.0,cash-sum(o["amount"] for o in pending if o["side"]=="buy"))
            daily.append((d,equity,cash_after,1000.0 if month_start else 0.0))

        eq=pd.Series({d:e for d,e,_,_ in daily}).sort_index()
        cf=pd.Series({d:c for d,_,_,c in daily}).sort_index()
        cs=pd.Series({d:c for d,_,c,_ in daily}).sort_index()
        row=metrics(eq,cf,cs,strat,mode,history,contribution_total,sell_trades,turnover)
        if row: rows.append(row)
    return pd.DataFrame(rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="reports/phase2f_rebalance.csv")
    a=p.parse_args()
    out=ROOT/a.output; out.parent.mkdir(parents=True,exist_ok=True)
    result=pd.concat([run(h,m) for h in ("common","expanding") for m in MODES],ignore_index=True)
    result.to_csv(out,index=False)
    print(result.to_string(index=False))
    print(f"\nWrote {out}")

if __name__=="__main__":
    main()
