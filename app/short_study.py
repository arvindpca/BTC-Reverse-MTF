"""Short-hold, cost-aware study: trade only volatility events where the stop is big relative to fees (floor 0.6% or 1.0%), hold <= 8-12h.

Signals on 15m and 1h: range breakout with volume, volatility-expansion momentum, spike fade. Assets BTC, ETH, SOL (PAXG moves too little).
Exits not fixed: ATR chandelier trailing. Costs 0.06%+0.02% per side. TRAIN <2024, VALIDATION 2024-01..2025-06, SEALED TEST 2025-07+.
Same configs are run inside the user's IST windows and all-day. A random-walk null shows luck-only passers. Research only.
"""
from __future__ import annotations

import argparse
import itertools
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import reverse_eng as re_
from . import smc_study as s
from .engine import run
from .mtf import atr
from .reverse_eng import fetch_klines

HOLD = {"15m": 32, "1h": 12}
EXITS = {"ch1.5": 1.5, "ch2.5": 2.5}
FLOORS = (0.006, 0.010)
s.MIN["1h"] = 60


def feats(d, tf):
    o, h, l, c, v = (d[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    per_day = 96 if tf == "15m" else 24
    A = dict(o=o, h=h, l=l, c=c, atr=atr(h, l, c, 14))
    A["volr"] = v / pd.Series(v).rolling(20 * per_day).mean().shift(1).to_numpy()
    n = 32 if tf == "15m" else 24
    A["dh"] = pd.Series(h).rolling(n).max().shift(1).to_numpy(); A["dl"] = pd.Series(l).rolling(n).min().shift(1).to_numpy()
    return A


def sigs(A):
    c, o, h, l, a, v = A["c"], A["o"], A["h"], A["l"], A["atr"], A["volr"]
    rng = h - l
    with np.errstate(invalid="ignore", divide="ignore"):
        pos = (c - l) / np.where(rng > 0, rng, np.nan)
        S = {"break_vol": (s.edge((c > A["dh"]) & (v >= 1.5)), s.edge((c < A["dl"]) & (v >= 1.5))),
             "break_novol": (s.edge(c > A["dh"]), s.edge(c < A["dl"])),
             "expand": (s.edge((rng >= 2 * a) & (pos >= 0.75) & (v >= 2)), s.edge((rng >= 2 * a) & (pos <= 0.25) & (v >= 2)))}
        pr, pa, pv, pc, po = np.roll(rng, 1), np.roll(a, 1), np.roll(v, 1), np.roll(c, 1), np.roll(o, 1)
        mid = (np.roll(h, 1) + np.roll(l, 1)) / 2
        S["fade"] = (s.edge((pr >= 3 * pa) & (pc < po) & (pv >= 2) & (c > o) & (c > mid)), s.edge((pr >= 3 * pa) & (pc > po) & (pv >= 2) & (c < o) & (c < mid)))
    for x, y in S.values():
        x[:3000], y[:3000] = False, False
    return S


def evalc(A, L, Sh, k, floor, tf, wmask):
    c = A["c"]
    sd = np.zeros(len(c), np.int8); sd[L & wmask] = 1; sd[Sh & wmask & (sd == 0)] = -1
    dist = np.maximum(k * A["atr"], floor * c)
    stop = np.where(sd != 0, c - sd * dist, np.nan)
    ep = replace(re_.EP, rr=50.0, be_r=None, max_hold=HOLD[tf], min_risk_pct=0.2, max_risk_pct=8.0, reverse=False, trail_r=1.0, trail_start_r=0.0)
    return run(A["o"], A["h"], A["l"], c, sd, stop, np.arange(len(c)), ep, 3000, len(c))


def zoo(df15):
    rows = []
    for tf in ("15m", "1h"):
        d = df15 if tf == "15m" else s.resample(df15, "1h")
        A = feats(d, tf); S = sigs(A); wm = s.window_masks(d.index, tf)
        ent = d.index.tz_localize(None).values if d.index.tz is not None else d.index.values
        for (nm, (L, Sh)), (en, k), fl, wn in itertools.product(S.items(), EXITS.items(), FLOORS, wm):
            tr = evalc(A, L, Sh, k, fl, tf, wm[wn])
            if not tr: continue
            et = ent[[t.entry_idx for t in tr]]
            parts = {"tr": [t for t, e in zip(tr, et) if e < s.T_VAL], "va": [t for t, e in zip(tr, et) if s.T_VAL <= e < s.T_TEST], "te": [t for t, e in zip(tr, et) if e >= s.T_TEST], "all": tr}
            r = dict(cfg=f"{tf}|{nm}|{en}|floor{fl * 100:.1f}%|{wn}", tf=tf, sig=nm, win=wn, floor=fl)
            for p, t in parts.items():
                r.update({f"{p}_{kk}": v for kk, v in s.pstat(t).items()})
            rows.append(r)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="BTCUSDT ETHUSDT SOLUSDT")
    ap.add_argument("--days", type=int, default=1800)
    ap.add_argument("--out", default="short_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(exist_ok=True)
    L = ["# Short-hold, cost-aware study (volatility events, stop floor 0.6% / 1.0%)", "",
         "Hold <= 8h (15m) / 12h (1h). Pass rule: n>=40 train & >=25 validation, net R>0 and PF>1.15 in both. Test = 2025-07 onwards (sealed).", ""]
    first = True
    for sym in a.symbols.split():
        df = fetch_klines(sym, "15m", a.days, 900_000)
        R = zoo(df); R["pass"] = s.passes(R) if False else ((R.tr_n >= 40) & (R.va_n >= 25) & (R.tr_net_r > 0) & (R.va_net_r > 0) & (R.tr_pf > 1.15) & (R.va_pf > 1.15))
        R.to_csv(out / f"{sym}_results.csv", index=False)
        top = R[R["pass"]].copy(); top["score"] = np.minimum(top.tr_pf, top.va_pf)
        L += [f"## {sym} ({len(df)} 15m bars, {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d})", "",
              f"Configs {len(R)}; positive net R: train {(R.tr_net_r > 0).mean() * 100:.0f}%, validation {(R.va_net_r > 0).mean() * 100:.0f}%, test {(R.te_net_r > 0).mean() * 100:.0f}%. "
              f"Average fee cost per trade {R.all_cost.mean():.2f} R. Passed train+validation: **{len(top)}**.", ""]
        g = R.groupby(["floor"]).agg(cost=("all_cost", "mean"), avg=("all_avg_r", "mean") if "all_avg_r" in R else ("all_net_r", "mean"))
        by = R.groupby("sig").agg(n=("cfg", "size"), tr=("tr_net_r", "mean"), va=("va_net_r", "mean"), te=("te_net_r", "mean"))
        L += ["| signal | configs | train avg R | validation avg R | test avg R |", "|---|---|---|---|---|"] + [f"| {k} | {int(r.n)} | {r.tr:+.1f} | {r.va:+.1f} | {r.te:+.1f} |" for k, r in by.iterrows()] + [""]
        if len(top):
            L += ["| config | trades (all) | win% | net R | PF | train / val / TEST net R | TEST n | TEST PF |", "|---|---|---|---|---|---|---|---|"]
            for _, r in top.sort_values("score", ascending=False).head(8).iterrows():
                L.append(f"| {r.cfg} | {r.all_n:.0f} | {r.all_win * 100:.0f} | {r.all_net_r:+.1f} | {r.all_pf:.2f} | {r.tr_net_r:+.1f} / {r.va_net_r:+.1f} / {r.te_net_r:+.1f} | {r.te_n:.0f} | {r.te_pf:.2f} |")
            L += ["", f"Passers also profitable on TEST: {int((top.te_net_r > 0).sum())}; with test n>=20 and PF>1.15: {int(((top.te_n >= 20) & (top.te_pf > 1.15) & (top.te_net_r > 0)).sum())}.", ""]
        if first:
            first = False
            nd = s.null5(len(df), 21, float(df["close"].iloc[0]) , df.index)
            nd["volume"] = np.random.default_rng(3).lognormal(0, .6, len(df))
            nd[["open", "high", "low", "close"]] = nd[["open", "high", "low", "close"]] * 1.0
            N = zoo(nd)
            npass = ((N.tr_n >= 40) & (N.va_n >= 25) & (N.tr_net_r > 0) & (N.va_net_r > 0) & (N.tr_pf > 1.15) & (N.va_pf > 1.15)).sum()
            L += [f"Random-walk null (same bars): passers by pure luck = **{int(npass)}** of {len(N)}; positive on test {(N.te_net_r > 0).mean() * 100:.0f}%.", ""]
    Path(out, "summary.md").write_text("\n".join(L)); print("\n".join(L))


if __name__ == "__main__":
    main()
