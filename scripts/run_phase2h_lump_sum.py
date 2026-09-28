"""Phase 2H: USD 12,000 lump sum, zero future contributions, ~10-year hold."""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from data_loader import load_csv_folder

LEVELS={1.5:.25,3:.50,5:.75,8:1.0}
STRATS=["S1_DCA50_Dip50","S2_DCA50_ATR8_50","S3_DCA50_Dip25_ATR8_25","S4_ATR8_100_else_S1"]

def load_data():
    assets=load_csv_folder(ROOT/"tickers"); o={}
    for t,a in assets.items():
        f=a.frame.set_index("Date")
        o[t]=f[["Open","High","Low","Close"]].where(f["ohlc_valid"])
    alloc=pd.read_csv(ROOT/"portfolio_allocation.csv")
    targets={}
    for _,r in alloc.iterrows():
        t=str(r["Ticker"]).strip().upper()
        if t in ("CASH","CASHUSD","CASH USD"): continue
        if t=="BTCUSD": t="BTC"
        targets[t]=float(str(r["Allocation %"]).replace("%","").replace(",","."))/100
    return {t:o[t] for t in targets if t in o},targets

def weekly(f):
    w=f.resample("W-FRI").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna()
    pc=w.Close.shift(1)
    tr=pd.concat([(w.High-w.Low).abs(),(w.High-pc).abs(),(w.Low-pc).abs()],axis=1).max(axis=1)
    atr=pd.Series(np.nan,index=w.index)
    if len(tr)>=20:
        atr.iloc[19]=tr.iloc[:20].mean()
        for i in range(20,len(tr)): atr.iloc[i]=(atr.iloc[i-1]*19+tr.iloc[i])/20
    swing=pd.Series(False,index=w.index); h=w.High.values
    for i in range(3,len(w)-3):
        z=h[i-3:i+4]
        if np.isfinite(z).all() and h[i]==z.max() and (z==h[i]).sum()==1: swing.iloc[i]=True
    conf=[]
    for i in range(3,len(w)):
        if swing.iloc[i-3]: conf.append((w.index[i],float(w.High.iloc[i-3])))
    hh=pd.Series(np.nan,index=w.index)
    for dt,_ in conf:
        vals=[v for c,v in conf if c<=dt and c>=dt-pd.Timedelta(weeks=52)]
        if vals: hh.loc[dt]=max(vals)
    return hh.ffill(),atr.ffill()

def features(ohlc):
    out={}
    for t,f in ohlc.items():
        hh,atr=weekly(f); d=pd.DataFrame(index=f.index)
        wk=f.index.to_period("W-FRI").to_timestamp(how="end").normalize()
        prior=pd.Series(wk,index=f.index).map(lambda x:x-pd.Timedelta(weeks=1))
        d["HH52"]=prior.map(hh); d["ATR20W"]=prior.map(atr)
        d["Low"]=f.Low; d["Open"]=f.Open; d["Close"]=f.Close; out[t]=d
    return out

def distribute(needs,budget):
    if budget<=0 or not needs:return {}
    needs={k:v for k,v in needs.items() if v["need"]>0}; out={k:0 for k in needs}; left=budget
    for level in sorted({v["level"] for v in needs.values()},reverse=True):
        g={k:v for k,v in needs.items() if v["level"]==level}
        if left<=1e-9:break
        s=sum(v["target"] for v in g.values()); used=0
        for k,v in g.items():
            a=min(v["need"],left*v["target"]/s if s else 0); out[k]+=a; used+=a
        left-=used
    return out

def starts(dates):
    dates=pd.DatetimeIndex(sorted(dates)); out=[]
    for y in range(int(dates.min().year),int(dates.max().year)-9):
        a=pd.Timestamp(y,1,1); x=dates[dates>=a]
        if len(x) and len(dates[dates>=x[0]+pd.DateOffset(years=10)]): out.append(x[0])
    a=dates.max()-pd.DateOffset(years=10); x=dates[dates>=a]
    if len(x): out.append(x[0])
    return sorted(set(out))

def run(start,end,strategy,ohlc,feat,targets):
    assets=list(targets); dates=pd.DatetimeIndex(sorted(set().union(*[set(feat[t].index) for t in assets])))
    dates=dates[(dates>=start)&(dates<=end)]
    if len(dates)<200:return None
    cash=12000.; shares={t:0. for t in assets}; pending=[]; last={t:np.nan for t in assets}; daily=[]
    first=True
    for i,d in enumerate(dates):
        if pending:
            nxt=[]
            for o in pending:
                px=ohlc[o["ticker"]].Open.get(d,np.nan)
                if not np.isfinite(px) or px<=0:nxt.append(o);continue
                gross=min(o["amount"],max(0,cash)/1.001)
                if gross>1e-9:
                    cash-=gross*1.001; shares[o["ticker"]]+=gross/(px*1.0005)
            pending=nxt
        for t in assets:
            px=ohlc[t].Close.get(d,np.nan)
            if np.isfinite(px) and px>0:last[t]=float(px)
        equity=cash+sum(shares[t]*last[t] for t in assets if np.isfinite(last[t]))
        floor=.05*equity; available=max(0,cash-floor)
        pb={}
        for o in pending:
            if o["side"]=="buy":pb[o["ticker"]]=pb.get(o["ticker"],0)+o["amount"]

        # Initial 50% DCA sleeve: target-weighted on the first valid execution day.
        if first:
            first=False
            base=min(6000,available)
            valid=[t for t in assets if np.isfinite(ohlc[t].Open.get(d,np.nan))]
            for t in valid:
                a=base*targets[t]/sum(targets[x] for x in valid)
                if a>1e-9: pending.append({"ticker":t,"side":"buy","amount":a})
            pb={o["ticker"]:pb.get(o["ticker"],0)+o["amount"] for o in pending if o["side"]=="buy"}

        needs={}; active8=[]
        for t in assets:
            if d not in feat[t].index:continue
            hh,atr,low=feat[t].loc[d,["HH52","ATR20W","Low"]]
            if not(np.isfinite(hh) and np.isfinite(atr) and np.isfinite(low) and hh>0 and atr>0):continue
            trig=next((k for k in (8.,5.,3.,1.5) if low<=hh-k*atr),None)
            if trig is None:continue
            if trig==8:active8.append(t)
            if strategy=="S2_DCA50_ATR8_50" and trig!=8:
                # No ATR8 today; S2 falls back to S1 opportunity behavior.
                pass
            if strategy in ("S1_DCA50_Dip50","S2_DCA50_ATR8_50","S3_DCA50_Dip25_ATR8_25","S4_ATR8_100_else_S1"):
                need=max(0,targets[t]*equity*LEVELS[trig]-shares[t]*last[t]-pb.get(t,0))
                if need>0:needs[t]={"need":need,"level":trig,"target":targets[t]}
        pb={}
        for o in pending:
            if o["side"]=="buy":pb[o["ticker"]]=pb.get(o["ticker"],0)+o["amount"]
        reserved=sum(o["amount"] for o in pending if o["side"]=="buy")
        avail=max(0,available-reserved)

        if strategy=="S4_ATR8_100_else_S1" and active8:
            n={t:{"need":max(0,targets[t]*equity-shares[t]*last[t]-pb.get(t,0)),"level":8,"target":targets[t]} for t in active8}
            n={t:v for t,v in n.items() if v["need"]>0}; buys=distribute(n,avail)
        elif strategy=="S2_DCA50_ATR8_50" and active8:
            n={t:{"need":max(0,targets[t]*equity-shares[t]*last[t]-pb.get(t,0)),"level":8,"target":targets[t]} for t in active8}
            n={t:v for t,v in n.items() if v["need"]>0}; buys=distribute(n,avail*.50)
        elif strategy=="S3_DCA50_Dip25_ATR8_25":
            if not active8:
                # No ATR8 anywhere today: exact S1 opportunity behavior.
                b=dist(needs,budget*0.50)
            else:
                a=dist(needs,budget*0.25)
                n={t:v for t,v in needs.items() if v["level"]==8}
                b8=dist(n,budget*0.25); b={}
                for t,x in a.items(): b[t]=b.get(t,0)+x
                for t,x in b8.items(): b[t]=b.get(t,0)+x
        else: buys=distribute(needs,available_dip*.50)
        for t,a in buys.items():
            if t in active8:
                room=max(0,targets[t]*equity-shares[t]*last[t]-pb.get(t,0))
            elif t in needs:
                room=max(0,targets[t]*equity*LEVELS[needs[t]["level"]]-shares[t]*last[t]-pb.get(t,0))
            else:
                room=0.0
            if a>1e-9:pending.append({"ticker":t,"side":"buy","amount":min(a,room)})
        cash_after=max(0,cash-sum(o["amount"] for o in pending if o["side"]=="buy"))
        daily.append((d,equity,cash_after))
    eq=pd.Series({d:e for d,e,_ in daily}).sort_index()
    cs=pd.Series({d:c for d,_,c in daily}).sort_index()
    ret=eq.pct_change().dropna()
    years=max((eq.index[-1]-eq.index[0]).days/365.25,1/365.25)
    cagr=float(np.expm1(np.log1p(ret).sum()/years))
    lw=np.log1p(ret).cumsum(); dd=np.expm1(lw-lw.cummax())
    sharpe=float(np.sqrt(252)*ret.mean()/ret.std()) if ret.std()>0 else np.nan
    return dict(strategy=strategy,cohort_start=eq.index[0],cohort_end=eq.index[-1],
                years=years,initial=12000,final_equity=float(eq.iloc[-1]),
                final_multiple=float(eq.iloc[-1]/12000),CAGR=cagr,max_drawdown=float(dd.min()),
                Sharpe=sharpe,cash_utilization=float((1-cs/eq.replace(0,np.nan)).mean()))

def main():
    ohlc,targets=load_data(); feat=features(ohlc)
    all_dates=sorted(set().union(*[set(x.index) for x in feat.values()])); ss=starts(all_dates)
    rows=[]
    for s in ss:
        ends=pd.DatetimeIndex(all_dates); e=ends[ends>=s+pd.DateOffset(years=10)]
        if not len(e):continue
        for st in STRATS:
            r=run(s,e[0],st,ohlc,feat,targets)
            if r:rows.append(r)
    r=pd.DataFrame(rows).sort_values(["cohort_start","strategy"])
    r.to_csv(ROOT/"reports/phase2h_lump_sum.csv",index=False)
    sm=r.groupby("strategy").agg(cohorts=("CAGR","count"),median_CAGR=("CAGR","median"),min_CAGR=("CAGR","min"),max_CAGR=("CAGR","max"),median_final_multiple=("final_multiple","median"),median_final_equity=("final_equity","median"),median_max_drawdown=("max_drawdown","median")).reset_index()
    report=ROOT/"reports/PHASE2H_LUMP_SUM_2026-09-27.txt"
    report.write_text("PHASE 2H — LUMP SUM / TEN-YEAR HOLD\nHistorical descriptive research only.\n\n"+sm.to_string(index=False)+"\n\nCOHORT RESULTS\n"+r.to_string(index=False)+"\n",encoding="utf-8")
    print(sm.to_string(index=False)); print(r.to_string(index=False))
if __name__=="__main__":main()
