"""Phase 2A daily ATR/pullback engine.

This stage isolates recurring contributions (initial capital = 0) and tests
S1-S4 across three pre-registered simultaneous-trigger allocation rules.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
TICKER_DIR = ROOT / "tickers"
ALLOC = ROOT / "portfolio_allocation.csv"

LEVELS = {1.5: 0.25, 3.0: 0.50, 5.0: 0.75, 8.0: 1.00}
STRATS = ["S1_DCA50_Dip50", "S2_DCA50_ATR8_50",
          "S3_DCA50_Dip25_ATR8_25", "S4_ATR8_100_else_S1"]
DISTS = ["D1_target_weighted", "D2_equal_weighted", "D3_deepest_first"]

def load_ohlc():
    from data_loader import load_csv_folder
    assets = load_csv_folder(TICKER_DIR)
    out = {}
    for t, a in assets.items():
        f = a.frame.set_index("Date")
        out[t] = f[["Open","High","Low","Close"]].where(f["ohlc_valid"])
    return out

def load_targets():
    f = pd.read_csv(ALLOC)
    out = {}
    for _, r in f.iterrows():
        t = str(r["Ticker"]).strip().upper()
        if t in ("CASH","CASHUSD","CASH USD"): continue
        if t == "BTCUSD": t = "BTC"
        out[t] = float(str(r["Allocation %"]).replace("%","").replace(",","."))/100
    return out

def weekly_indicators(frame):
    w = frame.resample("W-FRI").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna(subset=["High","Low","Close"])
    prev_c = w["Close"].shift(1)
    tr = pd.concat([(w["High"]-w["Low"]).abs(),
                    (w["High"]-prev_c).abs(),
                    (w["Low"]-prev_c).abs()], axis=1).max(axis=1)
    atr = pd.Series(np.nan, index=w.index)
    if len(tr) >= 20:
        atr.iloc[19] = tr.iloc[:20].mean()
        for i in range(20, len(tr)):
            atr.iloc[i] = (atr.iloc[i-1]*19 + tr.iloc[i]) / 20.0
    swing = pd.Series(False, index=w.index)
    highs = w["High"].values
    for i in range(3, len(w)-3):
        window = highs[i-3:i+4]
        if np.isfinite(window).all() and highs[i] == window.max() and (window == highs[i]).sum() == 1:
            swing.iloc[i] = True
    # Confirm pivot after three right-side weekly candles.
    confirmed = []
    for i in range(len(w)):
        if i >= 3 and swing.iloc[i-3]:
            confirmed.append((w.index[i], float(w["High"].iloc[i-3])))
    hh = pd.Series(np.nan, index=w.index)
    for dt, pivot_high in confirmed:
        mask = (w.index <= dt) & (w.index >= dt - pd.Timedelta(weeks=52))
        prior = [v for cdt,v in confirmed if cdt <= dt and cdt >= dt-pd.Timedelta(weeks=52)]
        if prior:
            hh.loc[dt] = max(prior)
    # Carry the latest confirmed HH/ATR forward; daily engine uses only the last completed week.
    hh = hh.ffill()
    atr = atr.ffill()
    return w, hh, atr

def build_daily_features(ohlc):
    feats = {}
    for t, f in ohlc.items():
        w, hh, atr = weekly_indicators(f)
        daily = pd.DataFrame(index=f.index)
        # Only completed weekly information is available to a daily decision.
        week_dates = f.index.to_period("W-FRI").to_timestamp(how="end").normalize()
        prior_week = pd.Series(week_dates, index=f.index).map(
            lambda x: x - pd.Timedelta(weeks=1)
        )
        daily["HH52"] = prior_week.map(hh)
        daily["ATR20W"] = prior_week.map(atr)
        daily["Low"] = f["Low"]
        daily["Open"] = f["Open"]
        daily["Close"] = f["Close"]
        feats[t] = daily
    return feats

def distribute(needs, budget, dist):
    if budget <= 0 or not needs:
        return {}
    needs = {k:v for k,v in needs.items() if v.get("need", 0.0) > 0}
    if not needs:
        return {}
    if dist == "D1_target_weighted":
        remaining = {k:v["need"] for k,v in needs.items()}
        out = {k:0.0 for k in needs}
        left = budget
        while left > 1e-9 and remaining:
            s = sum(needs[k]["target"] for k in remaining)
            if s <= 0: break
            alloc = {k:left*needs[k]["target"]/s for k in remaining}
            used = 0.0
            capped = []
            for k,a in alloc.items():
                x=min(remaining[k],a)
                out[k]+=x; remaining[k]-=x; used+=x
                if remaining[k] <= 1e-9: capped.append(k)
            left-=used
            for k in capped: remaining.pop(k)
            if used <= 1e-9: break
        return out
    if dist == "D2_equal_weighted":
        remaining = dict((k,v["need"]) for k,v in needs.items())
        out = {k:0.0 for k in needs}
        left = budget
        while left > 1e-9 and remaining:
            share = left / len(remaining)
            used = []
            for k,n in remaining.items():
                a=min(n,share)
                out[k]+=a; left-=a
                if n-a <= 1e-9: used.append(k)
            for k in used: remaining.pop(k)
            if not used and share <= 1e-9: break
        return out
    # D3: deepest trigger first, then preserve target-weighted allocation within a level.
    out = {k:0.0 for k in needs}
    left = budget
    for level in sorted(set(v["level"] for v in needs.values()), reverse=True):
        group={k:v for k,v in needs.items() if v["level"]==level}
        if left <= 1e-9: break
        s=sum(v["target"] for v in group.values())
        for k,v in group.items():
            a=min(v["need"], left*v["target"]/s if s else 0)
            out[k]+=a
        used=sum(out[k] for k in group)
        left-=used
    return out

def run(mode="expanding", strategy="all", dist="all"):
    targets=load_targets()
    ohlc=load_ohlc()
    assets=[t for t in targets if t in ohlc]
    feats=build_daily_features({t:ohlc[t] for t in assets})
    dates=sorted(set().union(*[set(f.index) for f in feats.values()]))
    if mode=="common":
        start=max(next(iter(f.index)) for f in feats.values())
        dates=[d for d in dates if d>=start]
    dates=pd.DatetimeIndex(dates)
    rows=[]
    strategies=STRATS if strategy=="all" else [strategy]
    dists=DISTS if dist=="all" else [dist]
    for strat in strategies:
      for distribution in dists:
        cash=0.0
        shares={t:0.0 for t in assets}
        pending=[]
        contribution_total=0.0
        peak=0.0
        daily=[]
        trades=0
        triggers=0
        for i,d in enumerate(dates):
            # Execute previous-day orders at today's open.
            if pending:
                pending_next=[]
                for order in pending:
                    t=order["ticker"]; px=ohlc[t]["Open"].get(d, np.nan)
                    if not np.isfinite(px) or px<=0:
                        # Preserve the order until a valid next-session open is available.
                        pending_next.append(order)
                        continue
                    gross=min(order["amount"], max(0.0,cash))
                    # Phase 1 baseline trading costs: 10 bps commission + 5 bps slippage.
                    if gross > 1e-8:
                        exec_px=px*(1.0+0.0005)
                        commission=gross*0.0010
                        total_cash=gross+commission
                        if total_cash > cash:
                            gross=max(0.0,cash/1.0010)
                            commission=gross*0.0010
                            total_cash=gross+commission
                        cash-=total_cash
                        shares[t]+=gross/exec_px
                        trades+=1
                pending=pending_next
            # Monthly contribution enters cash on first observed trading day of month.
            prev=dates[i-1] if i else None
            if prev is None or d.to_period("M") != prev.to_period("M"):
                cash += 1000.0
                contribution_total += 1000.0
                dca_budget=500.0
            else:
                dca_budget=0.0

            # Mark every held position with the latest valid close. Asset calendars
            # can have isolated missing observations; dropping a held position from
            # equity on such a day creates artificial drawdowns and corrupts TWR.
            if i == 0:
                last_close={t:np.nan for t in assets}
            for t in assets:
                px=ohlc[t]["Close"].get(d,np.nan)
                if np.isfinite(px) and px>0:
                    last_close[t]=float(px)
            prices=dict(last_close)
            equity=cash+sum(shares[t]*prices[t] for t in assets if np.isfinite(prices[t]))
            floor=0.05*equity
            available=max(0.0,cash-floor)

            # Current position and room.
            pending_by_t={}
            for o in pending:
                pending_by_t[o["ticker"]]=pending_by_t.get(o["ticker"],0.0)+o["amount"]
            room={}
            for t in assets:
                p=prices[t]
                cur=shares[t]*p if np.isfinite(p) else 0.0
                room[t]=max(0.0,targets[t]*equity-cur-pending_by_t.get(t,0.0))

            # DCA portion on contribution day, respecting room and 5% cash floor.
            if dca_budget>0 and available>0:
                eligible={t:room[t] for t in assets if room[t]>0 and np.isfinite(ohlc[t]["Open"].get(d,np.nan))}
                if eligible:
                    s=sum(targets[t] for t in eligible)
                    alloc={t:min(need,dca_budget*targets[t]/s) for t,need in eligible.items()}
                    total=min(available,sum(alloc.values()))
                    if total>0:
                        # proportional rescale if floor/cap binds
                        scale=total/max(sum(alloc.values()),1e-12)
                        for t,a in alloc.items():
                            if a*scale>1e-9: pending.append({"ticker":t,"amount":a*scale})
                        available-=total

            # Recompute pending after DCA so ATR8/other orders also respect room.
            pending_by_t={}
            for o in pending:
                pending_by_t[o["ticker"]]=pending_by_t.get(o["ticker"],0.0)+o["amount"]

            # Determine deepest trigger from today's intraday low.
            needs={}
            active8=[]
            for t in assets:
                f=feats[t]
                if d not in f.index: continue
                hh,atr=f.at[d,"HH52"],f.at[d,"ATR20W"]
                low=f.at[d,"Low"]
                if not (np.isfinite(hh) and np.isfinite(atr) and np.isfinite(low) and hh>0 and atr>0): continue
                trig=None
                for k in (8.0,5.0,3.0,1.5):
                    level_price=hh-k*atr
                    if low<=level_price:
                        trig=k; break
                if trig is None: continue
                triggers+=1
                if trig==8.0: active8.append(t)
                if strat=="S2_DCA50_ATR8_50" and trig!=8.0:
                    # No ATR8 today; S2 falls back to S1 opportunity behavior.
                    pass
                if strat=="S3_DCA50_Dip25_ATR8_25" and trig<8.0: pass
                if strat=="S4_ATR8_100_else_S1" and trig<8.0:
                    # fallback S1 handled below
                    pass
                if strat in ("S1_DCA50_Dip50","S2_DCA50_ATR8_50","S3_DCA50_Dip25_ATR8_25","S4_ATR8_100_else_S1"):
                    cum=LEVELS[trig]
                    cur=shares[t]*prices[t] if np.isfinite(prices[t]) else 0
                    desired=targets[t]*equity*cum
                    need=max(0.0,desired-cur)
                    if need>0:
                        needs[t]={"need":need,"level":trig,"target":targets[t]}
            # Allocate dip/ATR8 budgets from cash remaining after DCA reservations.
            # Unused cash carries indefinitely; no monthly expiry.
            available_for_dip=max(0.0,available-sum(o["amount"] for o in pending))
            active_strategy=strat
            if strat=="S4_ATR8_100_else_S1" and active8:
                atr_needs={}
                for t in active8:
                    cur=shares[t]*prices[t]
                    need=max(0.0,targets[t]*equity-cur-pending_by_t.get(t,0.0))
                    if need>0: atr_needs[t]={"need":need,"level":8.0,"target":targets[t]}
                buys=distribute(atr_needs,available_for_dip,distribution)
            elif strat=="S2_DCA50_ATR8_50" and active8:
                atr_needs={}
                for t in active8:
                    cur=shares[t]*prices[t]
                    need=max(0.0,targets[t]*equity-cur-pending_by_t.get(t,0.0))
                    if need>0: atr_needs[t]={"need":need,"level":8.0,"target":targets[t]}
                buys=distribute(atr_needs,available_for_dip*0.50,distribution)
            elif strat=="S2_DCA50_ATR8_50":
                # No ATR8 anywhere today: exact S1 opportunity behavior.
                buys=distribute(needs,available_for_dip*0.50,distribution)
            elif strat=="S3_DCA50_Dip25_ATR8_25":
                dip_buys=distribute(needs,available_for_dip*0.25,distribution)
                atr_needs={t:v for t,v in needs.items() if v["level"]==8.0}
                atr_buys=distribute(atr_needs,available_for_dip*0.25,distribution)
                buys={}
                for t,a in dip_buys.items(): buys[t]=buys.get(t,0)+a
                for t,a in atr_buys.items(): buys[t]=buys.get(t,0)+a
            else:
                buys=distribute(needs,available_for_dip*0.50,distribution)
            # Enforce the frozen allocation-room rule after combining DCA and dip/ATR8 orders.
            for t,a in buys.items():
                if a>1e-9:
                    room_after_pending=max(0.0,room.get(t,0.0)-pending_by_t.get(t,0.0))
                    pending.append({"ticker":t,"amount":min(a,room_after_pending)})
            total_pending=sum(o["amount"] for o in pending)
            cash_after=max(0.0,cash-total_pending)
            contribution = 1000.0 if (prev is None or d.to_period("M") != prev.to_period("M")) else 0.0
            daily.append((d,equity,cash_after,contribution))
        eq=pd.Series({d:e for d,e,ca,cf in daily}).sort_index()
        cf=pd.Series({d:cf for d,e,ca,cf in daily}).sort_index()
        cash_series=pd.Series({d:ca for d,e,ca,cf in daily}).sort_index()
        if len(eq):
            # Contributions enter at the beginning of the day. Use prior equity
            # plus contribution as the TWR denominator.
            # Log wealth avoids overflow on long expanding histories.
            prev_eq=eq.shift(1)
            denominator=prev_eq+cf
            ret=(eq/denominator-1.0).where(denominator>0)
            ret=ret.replace([np.inf,-np.inf],np.nan).dropna()
            years=max((eq.index[-1]-eq.index[0]).days/365.25,1/365.25)
            log_growth=float(np.log1p(ret).sum()) if len(ret) else np.nan
            twr=float(np.expm1(log_growth/years)) if np.isfinite(log_growth) else np.nan
            log_wealth=np.log1p(ret).cumsum()
            peak_log=log_wealth.cummax()
            dd=np.expm1(log_wealth-peak_log)
            maxdd=float(dd.min()) if len(dd) else np.nan
            sharpe=float(np.sqrt(252)*ret.mean()/ret.std()) if ret.std()>0 else np.nan
            negative=ret[ret<0]
            downside=float(negative.std()) if len(negative)>1 else np.nan
            sortino=float(np.sqrt(252)*ret.mean()/downside) if downside and downside>0 else np.nan
            utilization=float((1.0-cash_series/eq.replace(0,np.nan)).mean())
            rows.append(dict(strategy=strat,distribution=distribution,history_mode=mode,
                             start=eq.index[0],end=eq.index[-1],final_equity=eq.iloc[-1],
                             CAGR=twr,max_drawdown=maxdd,Sharpe=sharpe,Sortino=sortino,
                             cash_utilization=utilization,contributions=contribution_total,
                             trades=trades,trigger_events=triggers))
    return pd.DataFrame(rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="reports/phase2a_results.csv")
    a=p.parse_args()
    result=pd.concat([run("common"),run("expanding")],ignore_index=True)
    out=ROOT/a.output
    out.parent.mkdir(parents=True,exist_ok=True)
    result.to_csv(out,index=False)
    print(result.to_string(index=False))
    print(f"\nWrote {out}")

if __name__=="__main__":
    main()

# Trigger Phase 2A CI after workflow installation.
