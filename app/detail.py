"""Detailed PAXG check of the rules that survived the reverse-engineering test.

Questions answered: is the PAXG result just a gold bull run (long bias)?  Does it hold in every half year?
Do the same rules work mirrored short?  Do they beat random long entries with the same exit engine?
How much comes from a few lucky trades?  What if costs double?   Research only; no orders.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import reverse_eng as re_
from .engine import EngineParams, run, summarize
from .reverse_eng import clue_masks, fetch_klines, make_null_1h, pnl_curve

RULES = ["er>.4 & 3 up bars", "dist>3 & 3 up bars", "dist>3 & range high>.9", "rsi>70 & 3 up bars", "er>.4 & dist>3"]
MIRROR = {"er>.4 & 3 up bars": "er>.4 & 3 down bars", "dist>3 & 3 up bars": "dist<-3 & 3 down bars",
          "dist>3 & range high>.9": "dist<-3 & range low<.1", "rsi>70 & 3 up bars": "rsi<30 & 3 down bars",
          "er>.4 & dist>3": "er>.4 & dist<-3"}
BLOCKS = 6


def cond_of(masks: dict, name: str) -> np.ndarray:
    parts = [p.strip() for p in name.split("&")]
    m = np.ones(len(next(iter(masks.values()))), dtype=bool)
    for p in parts:
        m &= masks[p]
    return m


def bt(df, cond, side, a, lo, hi, ep=None):
    sd, stop, sid = re_.rule_signal(cond, side, df, a)
    ep = ep or re_.EP
    tr = run(df["open"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy(), sd, stop, sid, ep, lo, hi)
    return tr, summarize(tr)


def bh_pct(df, lo, hi) -> float:
    c = df["close"].to_numpy()
    return (c[hi - 1] / c[lo] - 1) * 100


def streak(vals) -> int:
    best = cur = 0
    for v in vals:
        cur = cur + 1 if v < 0 else 0
        best = max(best, cur)
    return best


def block_table(df, masks, a, name, side) -> tuple[list[str], list[float]]:
    n = len(df)
    edges = [int(n * i / BLOCKS) for i in range(BLOCKS + 1)]
    edges[0] = 600
    cond = cond_of(masks, name)
    L = ["| period | buy&hold % | trades | net R | win% | PF | P/L (300x30) |", "|---|---|---|---|---|---|---|"]
    pls = []
    for i in range(BLOCKS):
        lo, hi = edges[i], edges[i + 1]
        tr, s = bt(df, cond, side, a, lo, hi)
        pl, _ = pnl_curve(tr)
        pls.append(pl)
        L.append(f"| {df.index[lo]:%Y-%m} to {df.index[hi-1]:%Y-%m} | {bh_pct(df, lo, hi):+.0f} | {s['n']} | {s['net_r']:+.1f} | "
                 f"{s['win_rate']*100:.0f} | {re_.fmt(s['pf'])} | {pl:+.0f} |")
    return L, pls


def report(df: pd.DataFrame, label: str) -> list[str]:
    n = len(df)
    cut = int(n * 0.6)
    masks, a = clue_masks(df)
    c = df["close"].to_numpy()
    L = [f"# {label} detailed analysis", "",
         f"{n} 1h bars, {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}. Price {c[0]:.0f} -> {c[-1]:.0f} "
         f"(buy&hold {bh_pct(df, 0, n):+.0f}% overall, train part {bh_pct(df, 600, cut):+.0f}%, test part {bh_pct(df, cut, n):+.0f}%).", ""]
    # A. rule by rule, test part, long vs mirrored short
    L += ["## A. Test part: each rule long, and its mirror short", "",
          "| rule | side | trades | net R | win% | PF | avg hold h | avg win R | avg loss R | time in market | P/L (300x30) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in RULES:
        for side, nm in ((1, r), (-1, MIRROR[r])):
            tr, s = bt(df, cond_of(masks, nm), side, a, cut, n)
            if not tr:
                L.append(f"| {nm} | {'long' if side>0 else 'short'} | 0 | - | - | - | - | - | - | - | - |")
                continue
            net = np.array([t.net_r for t in tr])
            hold = np.array([t.exit_idx - t.entry_idx for t in tr])
            pl, _ = pnl_curve(tr)
            L.append(f"| {nm} | {'long' if side>0 else 'short'} | {s['n']} | {s['net_r']:+.1f} | {s['win_rate']*100:.0f} | {re_.fmt(s['pf'])} | "
                     f"{hold.mean():.0f} | {net[net>0].mean() if (net>0).any() else 0:.2f} | {net[net<0].mean() if (net<0).any() else 0:.2f} | "
                     f"{hold.sum()/(n-cut)*100:.0f}% | {pl:+.0f} |")
    L.append("")
    # B. six blocks for the lead rule
    lead = RULES[0]
    L += [f"## B. Lead rule `{lead}` in six equal time blocks (whole history, long)", ""]
    t, pls = block_table(df, masks, a, lead, 1)
    L += t + ["", f"Profitable blocks: {sum(p > 0 for p in pls)} of {BLOCKS}.", ""]
    # C. random long baseline with same exit engine
    cond = cond_of(masks, lead)
    tr, s = bt(df, cond, 1, a, cut, n)
    edges = int((cond & ~np.concatenate([[False], cond[:-1]]))[cut:n].sum())
    rng = np.random.default_rng(0)
    p = edges / (n - cut)
    res = []
    for _ in range(200):
        rc = rng.random(n) < p
        res.append(bt(df, rc, 1, a, cut, n)[1]["net_r"])
    res = np.array(res)
    pct = (res < s["net_r"]).mean() * 100
    L += ["## C. Does the rule beat random long entries? (test part, same stop/trailing exit)", "",
          f"- Rule: net {s['net_r']:+.1f} R over {s['n']} trades.",
          f"- 200 random long-entry runs: median {np.median(res):+.1f} R, 90th percentile {np.percentile(res, 90):+.1f} R, "
          f"best {res.max():+.1f} R, positive in {(res>0).mean()*100:.0f}% of runs.",
          f"- The rule beats {pct:.0f}% of random long runs. "
          + ("Random longs also make money here, so a big part of the result is the gold uptrend itself."
             if np.median(res) > 0 else "Random longs do not make money here, so the rule adds something beyond the uptrend."), ""]
    # D. concentration, streaks, exits, months
    if tr:
        net = np.array([t.net_r for t in tr])
        srt = np.sort(net)[::-1]
        top5 = srt[:5].sum()
        reasons = pd.Series([t.reason for t in tr]).value_counts()
        L += ["## D. How the profit is made (lead rule, test part)", "",
              f"- Total {net.sum():+.1f} R; the best 5 trades alone = {top5:+.1f} R ({top5/net.sum()*100:.0f}% of total)." if net.sum() > 0 else f"- Total {net.sum():+.1f} R.",
              f"- Without the best 5 trades: {net.sum()-top5:+.1f} R.",
              f"- Longest losing streak: {streak(net)} trades. Worst single trade {net.min():+.2f} R.",
              "- Exit reasons: " + ", ".join(f"{k} {v}" for k, v in reasons.items()),
              f"- Median stop distance {np.median([t.risk_pct for t in tr]):.2f}% (liquidation at 30x is about 2.8%).", ""]
        months = pd.Series([t.net_r for t in tr], index=[df.index[t.exit_idx] for t in tr]).groupby(lambda d: d.strftime("%Y-%m")).sum()
        L += ["Month by month (net R): " + ", ".join(f"{k} {v:+.1f}" for k, v in months.items()), ""]
    # E. cost stress
    L += ["## E. Cost stress (lead rule, test part)", "", "| fee+slippage per side (x1 = real assumption, 0.16% round trip) | net R | P/L (300x30) |", "|---|---|---|"]
    for mult in (1, 2, 3):
        ep = replace(re_.EP, fee_pct=re_.EP.fee_pct * mult, slip_pct=re_.EP.slip_pct * mult)
        t2, s2 = bt(df, cond, 1, a, cut, n, ep)
        pl, _ = pnl_curve(t2)
        L.append(f"| {(re_.EP.fee_pct+re_.EP.slip_pct)*mult:.2f}% | {s2['net_r']:+.1f} | {pl:+.0f} |")
    L.append("")
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="PAXGUSDT")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--out", default="detail_out")
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    df = make_null_1h(24 * 600, 9) if a.synthetic else fetch_klines(a.symbol, "1h", a.days, 3_600_000)
    L = report(df, a.symbol)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
