"""Lead PAXG rule: exact conditions, when it works (session, weekday, month) and small, train-selected refinements.

Every refinement is chosen on the first 60% of history and then judged on the last 40%. The number of variants tried
is printed, because the more variants you try the more likely one wins by luck. Research only; no orders.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import reverse_eng as re_
from .detail import bh_pct, cond_of
from .engine import run, summarize
from .reverse_eng import clue_masks, fetch_klines, make_null_1h, pnl_curve

LEAD = "er>.4 & 3 up bars"
SESSIONS = [("Asia   (UTC 00-08 = IST 05:30-13:30)", 0, 8), ("Europe (UTC 08-14 = IST 13:30-19:30)", 8, 14),
            ("US     (UTC 14-21 = IST 19:30-02:30)", 14, 21), ("Late   (UTC 21-24 = IST 02:30-05:30)", 21, 24)]
MIN_TRAIN_N = 40


def trades_of(df, cond, a, lo, hi, ep=None, stop_atr=None):
    old = re_.STOP_ATR
    if stop_atr is not None:
        re_.STOP_ATR = stop_atr
    try:
        sd, stop, sid = re_.rule_signal(cond, 1, df, a)
    finally:
        re_.STOP_ATR = old
    return run(df["open"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy(), sd, stop, sid,
               ep or re_.EP, lo, hi)


def line(tr):
    s = summarize(tr)
    pl, dd = pnl_curve(tr)
    return s, pl, dd


def trade_frame(df, tr) -> pd.DataFrame:
    ts = [df.index[t.entry_idx] for t in tr]
    return pd.DataFrame(dict(t=ts, net_r=[t.net_r for t in tr], pl=[t.net_r * t.risk_pct / 100 * 9000 for t in tr],
                             hour=[x.hour for x in ts], wd=[x.weekday() for x in ts],
                             month=[x.strftime("%Y-%m") for x in ts]))


def bucket_table(tf: pd.DataFrame, key, labels) -> list[str]:
    L = ["| bucket | trades | net R | win% | avg R/trade |", "|---|---|---|---|---|"]
    for lab, m in labels:
        x = tf[m(tf)]
        if len(x):
            L.append(f"| {lab} | {len(x)} | {x['net_r'].sum():+.1f} | {(x['net_r']>0).mean()*100:.0f} | {x['net_r'].mean():+.2f} |")
        else:
            L.append(f"| {lab} | 0 | - | - | - |")
    return L


def report(df: pd.DataFrame, label: str) -> list[str]:
    n = len(df)
    cut = int(n * 0.6)
    masks, a = clue_masks(df)
    cond = cond_of(masks, LEAD)
    ep = re_.EP
    L = [f"# {label}: lead rule conditions, timing and refinements", "",
         "## 1. Exact conditions of the +2055 rule", "",
         "All three must be true on a finished 1h candle, and the signal fires only on the first candle where they become true:", "",
         "1. **Trend is clean:** Kaufman efficiency ratio over the last 20 hourly candles is above 0.40 "
         "(price moved mostly in one direction instead of zig-zagging).",
         "2. **Momentum:** the last 3 hourly candles are all green (close above open).",
         "3. **Side:** long only.", "",
         f"- Entry: at the close of that candle. Stop: {re_.STOP_ATR:g} x ATR(14, 1h) below entry; trades with a stop under "
         f"{ep.min_risk_pct}% or over {ep.max_risk_pct}% are skipped (the upper limit keeps the stop inside the 30x liquidation distance).",
         f"- Exit: trailing stop that starts after price has run {ep.trail_start_r} x risk and then follows 1 x risk behind the best price; "
         f"or the stop; or a time exit after {ep.max_hold} hours. No reversing, no re-entry on the same signal, one trade at a time.",
         f"- Costs: fee {ep.fee_pct}% + slippage {ep.slip_pct}% per side (0.16% round trip). Size: margin 300 x 30 = 9000 notional.", ""]
    tr_all = trades_of(df, cond, a, 600, n)
    tf = trade_frame(df, tr_all)
    tf["test"] = [t.entry_idx >= cut for t in tr_all]
    tf["ist_hour"] = (tf["hour"] + 5.5) % 24

    # ---- 2. when does it work
    def ses(lo, hi):
        return lambda x: (x["hour"] >= lo) & (x["hour"] < hi)

    L += ["## 2. When does it work?", "",
          "Train = first 60% of history, test = last 40%. If a bucket is good in BOTH, it is a real pattern; "
          "if it flips, it is noise.", ""]
    for part, flt in (("train", ~tf["test"]), ("test", tf["test"])):
        L += [f"### By session ({part})", ""] + bucket_table(tf[flt], "hour", [(s, ses(lo, hi)) for s, lo, hi in SESSIONS]) + [""]
    wd = [("Mon", lambda x: x["wd"] == 0), ("Tue", lambda x: x["wd"] == 1), ("Wed", lambda x: x["wd"] == 2), ("Thu", lambda x: x["wd"] == 3),
          ("Fri", lambda x: x["wd"] == 4), ("Sat+Sun", lambda x: x["wd"] >= 5)]
    for part, flt in (("train", ~tf["test"]), ("test", tf["test"])):
        L += [f"### By weekday ({part})", ""] + bucket_table(tf[flt], "wd", wd) + [""]
    L += ["### Month by month (whole history)", "", "| month | buy&hold % | trades | net R | P/L (300x30) |", "|---|---|---|---|---|"]
    mo = tf.groupby("month").agg(trades=("net_r", "size"), net_r=("net_r", "sum"), pl=("pl", "sum"))
    cm = df["close"].resample("MS").last()
    bh = (cm / cm.shift(1) - 1) * 100
    pos_m = 0
    for m, r in mo.iterrows():
        b = bh.get(pd.Timestamp(m + "-01", tz="UTC"), np.nan)
        L.append(f"| {m}{' *' if (pd.Timestamp(m+'-01', tz='UTC') >= df.index[cut]) else ''} | {b:+.1f} | {int(r['trades'])} | {r['net_r']:+.1f} | {r['pl']:+.0f} |")
        pos_m += r["net_r"] > 0
    L += ["", f"Profitable months: {pos_m} of {len(mo)} (rows marked * are in the test part). Months with a falling gold price "
          "(negative buy&hold) show how the rule behaves in a down move.", ""]

    # ---- 3. refinements selected on train
    masks_extra = {
        "base": np.ones(n, bool),
        "no weekend": np.array((df.index.weekday < 5)),
        "ema50>ema200": masks["ema50>200"],
        "slope up (ema200 rising)": masks["slope up"],
        "not vol low": ~masks["vol low"],
    }
    # worst session on TRAIN only
    trn = tf[~tf["test"]]
    sess_sc = {s: trn[(trn["hour"] >= lo) & (trn["hour"] < hi)]["net_r"].mean() for s, lo, hi in SESSIONS
               if ((trn["hour"] >= lo) & (trn["hour"] < hi)).sum() >= 8}
    if sess_sc:
        worst = min(sess_sc, key=sess_sc.get)
        lo, hi = [(l, h) for s, l, h in SESSIONS if s == worst][0]
        hrs = df.index.hour
        masks_extra[f"skip worst train session: {worst.split('(')[0].strip()}"] = ~((hrs >= lo) & (hrs < hi))
    variants = []
    for nm, m in masks_extra.items():
        variants.append((nm, cond & m, None, None))
    for sa in (2.0, 4.0):
        variants.append((f"stop {sa:g} ATR", cond, sa, None))
    for tr_r, st in ((0.75, 1.5), (1.5, 1.5), (1.0, 1.0), (1.0, 2.0)):
        variants.append((f"trail {tr_r:g}R after {st:g}R", cond, None, replace(ep, trail_r=tr_r, trail_start_r=st)))
    L += ["## 3. Can it be improved? (variants judged on train first)", "",
          f"{len(variants)} variants tried (including the base). Choosing among many variants can pick luck, "
          "so a variant is only accepted if it also helps in the unseen test part.", "",
          "| variant | train n | train net R | train PF | test n | test net R | test PF | test P/L (300x30) | test max DD |",
          "|---|---|---|---|---|---|---|---|---|"]
    rows = []
    for nm, c, sa, e in variants:
        t1 = trades_of(df, c, a, 600, cut, e, sa)
        t2 = trades_of(df, c, a, cut, n, e, sa)
        s1, _, _ = line(t1)
        s2, p2, d2 = line(t2)
        rows.append((nm, s1, s2, p2, d2))
        L.append(f"| {nm} | {s1['n']} | {s1['net_r']:+.1f} | {re_.fmt(s1['pf'])} | {s2['n']} | {s2['net_r']:+.1f} | "
                 f"{re_.fmt(s2['pf'])} | {p2:+.0f} | {d2:.0f} |")
    L.append("")
    base = rows[0]
    ok = [r for r in rows[1:] if r[1]["n"] >= MIN_TRAIN_N and r[1]["pf"] > base[1]["pf"] and r[1]["net_r"] > 0]
    if ok:
        best = max(ok, key=lambda r: r[1]["pf"])
        better = best[2]["net_r"] > base[2]["net_r"] and best[2]["pf"] > base[2]["pf"]
        L += [f"Best on TRAIN (more profit factor than base, >= {MIN_TRAIN_N} trades): **{best[0]}**. On test it gives "
              f"{best[2]['net_r']:+.1f} R / PF {re_.fmt(best[2]['pf'])} versus base {base[2]['net_r']:+.1f} R / PF {re_.fmt(base[2]['pf'])}: "
              + ("it ALSO improves the unseen part, so it is a reasonable refinement." if better else
                 "it does NOT improve the unseen part, so keep the base rule."), ""]
    else:
        L += ["No variant beat the base rule on train, so the base rule stays unchanged.", ""]
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="PAXGUSDT")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--out", default="refine_out")
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    df = make_null_1h(24 * 800, 11) if a.synthetic else fetch_klines(a.symbol, "1h", a.days, 3_600_000)
    L = report(df, a.symbol)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
