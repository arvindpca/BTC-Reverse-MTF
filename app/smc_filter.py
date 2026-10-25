"""Filter study: 1h SMC bias + 24h POC side + volume >= 1.5 x 20-day average as FILTERS on VWAP+RSI/MACD and support/resistance entries.

Strategy 1 = 15m entries, Strategy 2 = 5m, Strategy 3 = 1m; S/R trigger = bounce at a 1h support/resistance or previous-day low/high confirmed by the 5m candle.
Filter ladder (cumulative): F0 none, F1 +SMC bias, F2 +POC side, F3 +1h volume>=1.5x, F4 +entry-bar volume>=1.5x. Time windows: IST 18:30-23:30 and 00:00-02:00
(and all-day as reference). Stops not fixed: ATR chandelier trailing / ATR stop + 2R. Costs 0.06%+0.02% per side. Research only; no orders.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import smc_study as s
from .reverse_eng import fetch_klines

FILTERS = ["F0 none", "F1 +SMC bias", "F2 +POC side", "F3 +1h vol>=1.5x", "F4 +bar vol>=1.5x"]


def trigger_sets(A, tf):
    c, o, h, l = A["c"], A["o"], A["h"], A["l"]
    up, dn = s.xup(c, A["vwap"]), s.xup(A["vwap"], c)
    T = {}
    for nm, lc, sc in (("vwap+rsi", A["rsi"] > 50, A["rsi"] < 50), ("vwap+macd", A["mh"] > 0, A["mh"] < 0),
                       ("vwap+rsi+macd", (A["rsi"] > 50) & (A["mh"] > 0), (A["rsi"] < 50) & (A["mh"] < 0))):
        T[nm] = (up & lc, dn & sc)
    if tf in ("5m", "15m"):
        def tl(level): return pd.Series(l <= level * 1.001).rolling(6, min_periods=1).max().to_numpy().astype(bool)
        def th(level): return pd.Series(h >= level * 0.999).rolling(6, min_periods=1).max().to_numpy().astype(bool)
        with np.errstate(invalid="ignore"):
            sl = (tl(A["sup"]) & (c > A["sup"] * 1.0005) & (c > o)) | (tl(A["pdl"]) & (c > A["pdl"] * 1.0005) & (c > o))
            sh = (th(A["res"]) & (c < A["res"] * 0.9995) & (c < o)) | (th(A["pdh"]) & (c < A["pdh"] * 0.9995) & (c < o))
        T["sr_bounce"] = (s.edge(sl), s.edge(sh))
    return T


def apply_filter(A, L, Sh, f):
    c = A["c"]
    with np.errstate(invalid="ignore"):
        mL, mS = np.ones(len(c), bool), np.ones(len(c), bool)
        if f >= 1: mL &= A["bias"] == 1; mS &= A["bias"] == -1
        if f >= 2: mL &= c > A["poc"]; mS &= c < A["poc"]
        if f >= 3: v = A["volr"] >= 1.5; mL &= v; mS &= v
        if f >= 4: v = A["barvolr"] >= 1.5; mL &= v; mS &= v
    a, b = L & mL, Sh & mS
    a[:3000], b[:3000] = False, False
    return a, b


def split_times(tf, idx):
    if tf == "1m":
        return np.datetime64("2026-02-25"), np.datetime64("2026-06-25")
    return s.T_VAL, s.T_TEST


def run_tf(sym, tf, A, idx, rows):
    wm = s.window_masks(idx, tf)
    ent = idx.tz_localize(None).values if idx.tz is not None else idx.values
    tv, tt = split_times(tf, idx)
    for tn, (L0, S0) in trigger_sets(A, tf).items():
        for fi, fn in enumerate(FILTERS):
            L, Sh = apply_filter(A, L0, S0, fi)
            for ex in s.EXITS:
                for wn in ("window", "all_day"):
                    tr = s.eval_cfg(A, L, Sh, "both", ex, tf, wm[wn])
                    r = dict(sym=sym, tf=tf, trigger=tn, filt=fn, exit=ex, win=wn)
                    if tr:
                        et = ent[[t.entry_idx for t in tr]]
                        parts = {"tr": [t for t, e in zip(tr, et) if e < tv], "va": [t for t, e in zip(tr, et) if tv <= e < tt], "te": [t for t, e in zip(tr, et) if e >= tt], "all": tr}
                    else:
                        parts = {k: [] for k in ("tr", "va", "te", "all")}
                    for p, t in parts.items():
                        r.update({f"{p}_{k}": v for k, v in s.pstat(t).items()})
                    rows.append(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="BTCUSDT PAXGUSDT")
    ap.add_argument("--days", type=int, default=1800)
    ap.add_argument("--days1m", type=int, default=365)
    ap.add_argument("--out", default="smcf_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(exist_ok=True)
    L = ["# Filter study: SMC(1h) + POC(24h) + volume 1.5x as filters (time windows IST 18:30-23:30, 00:00-02:00)", "",
         "Strategy 1 = 15m, 2 = 5m, 3 = 1m entries. Triggers: VWAP cross + RSI / MACD / both, and support-resistance bounce confirmed on the 5m candle. "
         "Filter ladder is cumulative F0..F4. Primary exit shown: chandelier 2.5 ATR trailing (other exits in the csv). Split 15m/5m: train <2024, val 2024-01..2025-06, TEST 2025-07+; 1m (1 year): thirds.", ""]
    for sym in a.symbols.split():
        df5 = fetch_klines(sym, "5m", a.days, 300_000)
        ctx, poc = s.make_ctx(df5)
        rows = []
        for tf in ("15m", "5m"):
            d = df5 if tf == "5m" else s.resample(df5, "15m")
            A = s.build(d, tf, ctx, poc, None)
            run_tf(sym, tf, A, d.index, rows)
        d1 = fetch_klines(sym, "1m", a.days1m, 60_000)
        A1 = s.build(d1, "1m", ctx, poc, None)
        run_tf(sym, "1m", A1, d1.index, rows)
        R = pd.DataFrame(rows); R.to_csv(out / f"{sym}_filter_results.csv", index=False)
        L += [f"## {sym}", ""]
        for tf, lab in (("15m", "Strategy 1 (15m)"), ("5m", "Strategy 2 (5m)"), ("1m", "Strategy 3 (1m, last year only)")):
            L += [f"### {lab}", "", "| trigger | filter | trades | win% | net R | PF | avg R/trade | cost R/trade | net R train / val / test | all-day: trades / net R |", "|---|---|---|---|---|---|---|---|---|---|"]
            q = R[(R.tf == tf) & (R.exit == "ch2.5")]
            for (tn, fn), g in q.groupby(["trigger", "filt"], sort=False):
                w = g[g.win == "window"].iloc[0]; al = g[g.win == "all_day"].iloc[0]
                n = w.all_n
                L.append(f"| {tn} | {fn} | {n:.0f} | {w.all_win * 100:.0f} | {w.all_net_r:+.1f} | {w.all_pf:.2f} | {w.all_net_r / max(n, 1):+.2f} | {w.all_cost:.2f} | "
                         f"{w.tr_net_r:+.1f} / {w.va_net_r:+.1f} / {w.te_net_r:+.1f} | {al.all_n:.0f} / {al.all_net_r:+.1f} |")
            L.append("")
        w = R[(R.win == "window") & (R.all_n >= 30)]
        pos = w[(w.all_net_r > 0) & (w.all_pf > 1.2)]
        L += [f"Configs (all exits) in the window with >=30 trades: {len(w)}; profitable overall with PF>1.2: {len(pos)}; "
              f"of those, profitable in the last third / test period too: {int((pos.te_net_r > 0).sum())}.", ""]
        if len(pos):
            L += ["| config | trades | net R | PF | train / val / test net R |", "|---|---|---|---|---|"]
            for _, r in pos.sort_values("all_pf", ascending=False).head(10).iterrows():
                L.append(f"| {r.tf}|{r.trigger}|{r.filt}|{r.exit} | {r.all_n:.0f} | {r.all_net_r:+.1f} | {r.all_pf:.2f} | {r.tr_net_r:+.1f} / {r.va_net_r:+.1f} / {r.te_net_r:+.1f} |")
            L.append("")
    Path(out, "summary.md").write_text("\n".join(L)); print("\n".join(L))


if __name__ == "__main__":
    main()
