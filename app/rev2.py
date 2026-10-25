"""Reverse engineering v2: hindsight swings on 4h and 1d for BTC and PAXG, rules mined on TRAIN, filtered on VALIDATION, tested ONCE on TEST.

Split (chronological, per asset): TRAIN first 50%, VALIDATION next 25%, SEALED TEST last 25%.
Candidates: every single clue and every cross-group pair (causal, from reverse_eng.clue_masks) x long/short x 2 non-fixed exits
(stop 3 ATR with delayed trail 1.5R/1R, and ATR chandelier trail). Pass train+validation, top 5 by min(PF train, PF validation) go to the test.
A random-walk null with the same bar counts shows how many rules pass by luck. Research only; no orders.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import reverse_eng as re_
from .engine import run, summarize
from .reverse_eng import candidates, clue_masks, fetch_klines, lifts, make_null_1h, swings, zigzag

TFS = {"4h": 4, "1d": 24}
MINN = {"4h": (30, 15), "1d": (15, 8)}
HOLD = {"4h": 180, "1d": 45}
MAXR = {"4h": 15.0, "1d": 30.0}
EXITS = {"delay": (1.5, 1.0), "chand": (0.0, 1.0)}


def to_tf(df1, tf):
    if tf == "1h": return df1
    r = {"4h": "4h", "1d": "1D"}[tf]
    return df1.resample(r, label="left", closed="left").agg(dict(open="first", high="max", low="min", close="last", volume="sum")).dropna()


def trades(df, cond, a, side, lo, hi, tf, ex):
    edge = cond & ~np.concatenate([[False], cond[:-1]])
    c = df["close"].to_numpy(float)
    sd = np.where(edge, side, 0).astype(np.int8)
    stop = np.where(edge, c - side * 3.0 * a, np.nan)
    ts, tr = EXITS[ex]
    ep = replace(re_.EP, rr=50.0, be_r=None, max_hold=HOLD[tf], min_risk_pct=0.3, max_risk_pct=MAXR[tf], reverse=False, trail_r=tr, trail_start_r=ts)
    return run(df["open"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy(), c, sd, stop, np.arange(len(c)), ep, lo, hi)


def st(tr):
    s = summarize(tr)
    return dict(n=s["n"], win=s["win_rate"], net_r=s["net_r"], pf=min(s["pf"], 99.0), dd=s["max_dd_r"], t=s["t_stat"])


def mine(df, tf, warm=250):
    n = len(df); c1, c2 = int(n * 0.5), int(n * 0.75)
    masks, a = clue_masks(df)
    cands = candidates(masks)
    rows = []
    mt, mv = MINN[tf]
    for name, m in cands:
        for side in (1, -1):
            for ex in EXITS:
                t1 = trades(df, m, a, side, warm, c1, tf, ex)
                if len(t1) < mt: continue
                s1 = st(t1)
                if s1["net_r"] <= 0 or s1["pf"] <= 1.15: continue
                s2 = st(trades(df, m, a, side, c1, c2, tf, ex))
                rows.append(dict(rule=name, side=side, exit=ex, tr_n=s1["n"], tr_r=s1["net_r"], tr_pf=s1["pf"], va_n=s2["n"], va_r=s2["net_r"], va_pf=s2["pf"],
                                 passed=bool(s2["n"] >= mv and s2["net_r"] > 0 and s2["pf"] > 1.15)))
    R = pd.DataFrame(rows)
    out = dict(cands=len(cands) * 2 * len(EXITS), train_ok=len(R), passed=int(R["passed"].sum()) if len(R) else 0, top=pd.DataFrame())
    if out["passed"]:
        P = R[R.passed].copy(); P["score"] = np.minimum(P.tr_pf, P.va_pf)
        P = P.sort_values("score", ascending=False).head(5)
        cm = dict(cands)
        te = []
        for _, r in P.iterrows():
            tr = trades(df, cm[r.rule], a, int(r.side), c2, n, tf, r.exit)
            s = st(tr); te.append(dict(te_n=s["n"], te_win=s["win"], te_r=s["net_r"], te_pf=s["pf"], te_dd=s["dd"]))
        out["top"] = pd.concat([P.reset_index(drop=True), pd.DataFrame(te)], axis=1)
    return out, masks, a


def explain(df, masks, tf):
    n = len(df); c1 = int(n * 0.5)
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    a = re_.atr(h, l, c, 14)
    piv = zigzag(h, l, a / c, 6.0)
    sw = swings(df, piv)
    L = []
    for d, lab in ((1, "UP-moves (long entries in hindsight)"), (-1, "DOWN-moves")):
        t = lifts(masks, sw, 250, c1, d)
        t = t[t.n_swings > 0].head(4)
        n_sw = int(t.n_swings.iloc[0]) if len(t) else 0
        L.append(f"  - {lab}, {n_sw} swings on train; clues most common at the start: " + ", ".join(f"{r.clue} (x{r.lift:.1f})" for r in t.itertuples()))
    return L


def null_df(n_bars, tf, seed):
    k = TFS[tf]
    d = make_null_1h(n_bars * k, seed)
    return to_tf(d, tf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="rev2_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(exist_ok=True)
    L = ["# Reverse engineering v2: BTC and PAXG on 4h and 1d (train 50% / validation 25% / sealed test 25%)", ""]
    allrows = []
    for sym, days in (("BTCUSDT", 3350), ("PAXGUSDT", 2700)):
        df1 = fetch_klines(sym, "1h", days, 3_600_000)
        for tf in ("4h", "1d"):
            df = to_tf(df1, tf)
            n = len(df)
            res, masks, atr_ = mine(df, tf)
            t0, t1, t2 = df.index[0], df.index[int(n * 0.5)], df.index[int(n * 0.75)]
            L += [f"## {sym} {tf}: {n} bars, train {t0:%Y-%m} to {t1:%Y-%m}, validation to {t2:%Y-%m}, test to {df.index[-1]:%Y-%m}", "",
                  f"Candidate rules tried: {res['cands']}. Profitable on train (PF>1.15, enough trades): {res['train_ok']}. Also pass validation: **{res['passed']}**.", ""]
            L += explain(df, masks, tf) + [""]
            nr = [mine(null_df(n, tf, 500 + i), tf)[0] for i in range(8)]
            hit = sum(1 for x in nr if len(x["top"]) and bool(((x["top"].te_n >= 10) & (x["top"].te_pf > 1.15) & (x["top"].te_r > 0)).any()))
            L += [f"Luck check, 8 random-walk series of the same length (no edge by construction): rules passing train+validation per series: "
                  f"{', '.join(str(x['passed']) for x in nr)}. In **{hit} of 8** series the process still produced at least one top-5 rule that looks profitable on the test "
                  f"(n>=10, PF>1.15). So a profitable-looking test result is only meaningful if it beats this luck rate.", ""]
            if len(res["top"]):
                T = res["top"]
                L += ["| rule | side | exit | train n/PF/R | val n/PF/R | TEST n | TEST win% | TEST net R | TEST PF | TEST max DD R |", "|---|---|---|---|---|---|---|---|---|---|"]
                for r in T.itertuples():
                    L.append(f"| {r.rule} | {'long' if r.side == 1 else 'short'} | {r.exit} | {r.tr_n:.0f}/{r.tr_pf:.2f}/{r.tr_r:+.1f} | {r.va_n:.0f}/{r.va_pf:.2f}/{r.va_r:+.1f} | {r.te_n:.0f} | {r.te_win * 100:.0f} | {r.te_r:+.1f} | {r.te_pf:.2f} | {r.te_dd:.1f} |")
                L.append("")
                T = T.assign(sym=sym, tf=tf); allrows.append(T)
    if allrows:
        pd.concat(allrows).to_csv(out / "finalists.csv", index=False)
    Path(out, "summary.md").write_text("\n".join(L)); print("\n".join(L))


if __name__ == "__main__":
    main()
