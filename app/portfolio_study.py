"""Multi-coin trend / momentum portfolio (daily, spot-like, NO leverage, NO fixed stop or target; exits come from the trend/rank rules).

Universe: Binance USDT coins listed by 2019. Signals use data up to the close of day t and earn the return of day t+1.
Costs: 0.10% of traded value per side (fee + slippage). Pre-registered split: TRAIN 2018-2021, VALIDATION 2022-2023, SEALED TEST 2024+.
Pass rule: CAGR>0 and Sharpe>0.5 in BOTH train and validation; top 3 by min(Sharpe) are tested once on the sealed test.
Caveat printed in the report: the universe is today's surviving coins (survivorship bias flatters the results). Research only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .reverse_eng import fetch_klines

COINS = "BTC ETH BNB XRP ADA LTC LINK TRX XLM ETC NEO EOS".split()
COST = 0.001
P_TRAIN, P_VAL, P_TEST = ("2018-01-01", "2021-12-31"), ("2022-01-01", "2023-12-31"), ("2024-01-01", "2100-01-01")


def load(days=3300):
    cl = {}
    for c in COINS:
        try:
            d = fetch_klines(f"{c}USDT", "1d", days, 86_400_000)
            cl[c] = d["close"].rename(c)
        except Exception:  # noqa: BLE001
            pass
    px = pd.concat(cl.values(), axis=1).sort_index()
    px.index = px.index.tz_localize(None).normalize() if px.index.tz is not None else px.index.normalize()
    return px.loc["2018-01-01":]


def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def weights(px, name):
    r = px.pct_change()
    avail = px.notna()
    n_av = avail.sum(axis=1).clip(lower=1)
    kind, *a = name.split("|")
    W = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    if kind == "btc_ma":
        W["BTC"] = (px["BTC"] > ema(px["BTC"], int(a[0]))).astype(float)
    elif kind == "trend_ew":
        tr = px > px.apply(lambda s: ema(s, int(a[0])))
        W = tr.astype(float).div(n_av, axis=0)
    elif kind == "trend_vol":
        tr = px > px.apply(lambda s: ema(s, int(a[0])))
        iv = 1 / r.rolling(30).std()
        iv = iv.where(avail)
        W = (tr * iv).div(iv.sum(axis=1), axis=0).fillna(0.0)
    elif kind == "mom":
        lb, k, gate = int(a[0]), int(a[1]), a[2]
        mom = px.pct_change(lb)
        mon = px.index.dayofweek == 0
        rows = []
        gate_ok = (px["BTC"] > ema(px["BTC"], 200)) if gate == "ma200" else pd.Series(True, index=px.index)
        cur = pd.Series(0.0, index=px.columns)
        for i, d in enumerate(px.index):
            if mon[i]:
                m = mom.iloc[i].dropna()
                m = m[m > 0].nlargest(k)
                cur = pd.Series(0.0, index=px.columns)
                if len(m) and bool(gate_ok.iloc[i]):
                    cur[m.index] = 1.0 / k
            elif not bool(gate_ok.iloc[i]):
                cur = pd.Series(0.0, index=px.columns)
            rows.append(cur.values)
        W = pd.DataFrame(rows, index=px.index, columns=px.columns)
    return W.fillna(0.0)


def backtest(px, W):
    r = px.pct_change().fillna(0.0)
    w = W.shift(1).fillna(0.0)                      # decided at close t, earns day t+1
    turn = w.diff().abs().sum(axis=1).fillna(0.0)
    return (w * r).sum(axis=1) - turn * COST


def stats(ret):
    ret = ret.dropna()
    if len(ret) < 30: return dict(cagr=np.nan, vol=np.nan, sharpe=np.nan, dd=np.nan, tot=np.nan)
    eq = (1 + ret).cumprod()
    yrs = len(ret) / 365.0
    return dict(cagr=eq.iloc[-1] ** (1 / yrs) - 1, vol=ret.std() * np.sqrt(365), sharpe=ret.mean() / ret.std() * np.sqrt(365) if ret.std() > 0 else 0.0,
                dd=(eq / eq.cummax() - 1).min(), tot=eq.iloc[-1] - 1)


def cut(s, p):
    return s.loc[p[0]:p[1]]


def configs():
    c = [f"btc_ma|{n}" for n in (100, 200)] + [f"trend_ew|{n}" for n in (50, 100, 200)] + [f"trend_vol|{n}" for n in (50, 100, 200)]
    c += [f"mom|{lb}|{k}|{g}" for lb in (30, 60, 90) for k in (3, 5) for g in ("none", "ma200")]
    return c


def fmt(s):
    return f"{s['cagr'] * 100:+.0f}% / {s['sharpe']:.2f} / {s['dd'] * 100:.0f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3300)
    ap.add_argument("--out", default="port_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(exist_ok=True)
    px = load(a.days)
    L = ["# Multi-coin trend / momentum portfolio (daily, no leverage, no fixed SL/TP)", "",
         f"Coins loaded: {', '.join(px.columns)}; {px.index[0]:%Y-%m-%d} to {px.index[-1]:%Y-%m-%d}. Cost 0.10% per side of traded value. "
         "Each cell: CAGR / Sharpe / max drawdown. **Survivorship bias:** these are coins that still trade today, so results are flattered.", ""]
    rows, rets = [], {}
    bh_btc = px["BTC"].pct_change().fillna(0.0)
    ew = px.pct_change().mean(axis=1).fillna(0.0)
    for nm, r in (("BUY&HOLD BTC", bh_btc), ("BUY&HOLD equal-weight all coins", ew)):
        rets[nm] = r
    for nm in configs():
        rets[nm] = backtest(px, weights(px, nm))
    for nm, r in rets.items():
        rows.append(dict(cfg=nm, **{f"{p}_{k}": v for p, per in (("tr", P_TRAIN), ("va", P_VAL), ("te", P_TEST), ("all", ("2018-01-01", "2100-01-01"))) for k, v in stats(cut(r, per)).items()}))
    R = pd.DataFrame(rows); R.to_csv(out / "results.csv", index=False)
    L += ["| config | train 2018-21 | validation 2022-23 | SEALED TEST 2024+ | all |", "|---|---|---|---|---|"]
    for _, x in R.iterrows():
        L.append(f"| {x.cfg} | {x.tr_cagr * 100:+.0f}% / {x.tr_sharpe:.2f} / {x.tr_dd * 100:.0f}% | {x.va_cagr * 100:+.0f}% / {x.va_sharpe:.2f} / {x.va_dd * 100:.0f}% | "
                 f"{x.te_cagr * 100:+.0f}% / {x.te_sharpe:.2f} / {x.te_dd * 100:.0f}% | {x.all_cagr * 100:+.0f}% / {x.all_sharpe:.2f} / {x.all_dd * 100:.0f}% |")
    cand = R[~R.cfg.str.startswith("BUY")]
    ok = cand[(cand.tr_cagr > 0) & (cand.va_cagr > 0) & (cand.tr_sharpe > 0.5) & (cand.va_sharpe > 0.5)].copy()
    ok["score"] = np.minimum(ok.tr_sharpe, ok.va_sharpe)
    ok = ok.sort_values("score", ascending=False)
    L += ["", f"## Pre-registered selection: {len(ok)} of {len(cand)} configs passed (CAGR>0 and Sharpe>0.5 in train AND validation). Top 3 on the sealed test:", ""]
    for _, x in ok.head(3).iterrows():
        L.append(f"- **{x.cfg}**: train {fmt(dict(cagr=x.tr_cagr, sharpe=x.tr_sharpe, dd=x.tr_dd))}, validation {fmt(dict(cagr=x.va_cagr, sharpe=x.va_sharpe, dd=x.va_dd))}, "
                 f"**TEST {fmt(dict(cagr=x.te_cagr, sharpe=x.te_sharpe, dd=x.te_dd))}**, test total return {x.te_tot * 100:+.0f}%")
    if len(ok):
        best = ok.iloc[0].cfg
        r = rets[best]
        yr = (1 + r).groupby(r.index.year).prod() - 1
        b = (1 + bh_btc).groupby(bh_btc.index.year).prod() - 1
        L += ["", f"Year-by-year, top pick {best} vs BTC buy&hold:", "", "| year | strategy | BTC hold |", "|---|---|---|"] + [f"| {y} | {yr[y] * 100:+.0f}% | {b[y] * 100:+.0f}% |" for y in yr.index]
        eq = (1 + r.loc["2024-01-01":]).cumprod() * 100000
        L += ["", f"1 lakh (no leverage) from 2024-01-01 grows to {eq.iloc[-1]:,.0f} with {best}; BTC buy&hold: {(1 + bh_btc.loc['2024-01-01':]).prod() * 100000:,.0f}."]
        pd.DataFrame(dict(strategy=(1 + r).cumprod(), btc_hold=(1 + bh_btc).cumprod())).to_csv(out / "equity.csv")
    Path(out, "summary.md").write_text("\n".join(L)); print("\n".join(L))


if __name__ == "__main__":
    main()
