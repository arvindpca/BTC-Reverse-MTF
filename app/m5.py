"""5-minute candle study for the PAXG v2 idea (1-minute ignored). Research only; no orders.

Variants, all long-only, stop = 4 x ATR(14, 1h-equivalent, completed hours only), trailing exit 1.5R/1R, 480 h time exit:
  base1h      v2 on real 1h bars (reference, resampled from the same 5m data)
  lit5m       the SAME rule applied literally on 5m bars (ER20, 3 green 5m bars) - expected to be noise
  scaled5m    same idea at 5m resolution: hourly-stride ER over 20h > thr and price up for `steps` consecutive hours
              (c > c[-12] > c[-24] ...), checked on every 5m bar, first-true edge, UTC 08-14 skipped
  hyb_k       1h v2 signal arms a 1h window; entry on first GREEN 5m bar after price dipped k x ATR below the signal close
              (better entry price, stop stays at signal close - 4 ATR)
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import reverse_eng as re_
from .detail import cond_of
from .engine import run, summarize
from .mtf import atr, efficiency_ratio
from .refine import LEAD
from .reverse_eng import clue_masks, fetch_klines

M5 = 300_000
BARS_H = 12
EP5 = replace(re_.EP, max_hold=480 * BARS_H)
HARSH = dict(fee_pct=0.10, slip_pct=0.05)


def to_1h(df5):
    return df5.resample("1h", label="left", closed="left").agg(
        dict(open="first", high="max", low="min", close="last", volume="sum")).dropna()


def v2_1h(df1):
    masks, a = clue_masks(df1)
    h = df1.index.hour
    cond = cond_of(masks, LEAD) & ~((h >= 8) & (h < 14))
    edge = cond & ~np.concatenate([[False], cond[:-1]])
    return edge, a


def arr(df):
    return [df[k].to_numpy(float) for k in ("open", "high", "low", "close")]


def go(df, sd, stop, ep, warm=3000):
    o, h, l, c = arr(df)
    return run(o, h, l, c, sd.astype(np.int8), stop, np.arange(len(c)), ep, warm, len(c))


def atr1h_on_5m(df5, df1):
    a1 = pd.Series(atr(df1["high"], df1["low"], df1["close"], 14), index=df1.index)
    a1 = a1.shift(1)                                  # value known only after the hour closed
    avail = a1.copy()
    avail.index = avail.index + pd.Timedelta(hours=1) - pd.Timedelta(hours=1)  # bar t value usable from open of t+1h
    return a1.reindex(df5.index, method="ffill").to_numpy(float)


def sig_lit5m(df5):
    masks, a = clue_masks(df5)
    h = df5.index.hour
    cond = cond_of(masks, LEAD) & ~((h >= 8) & (h < 14))
    edge = cond & ~np.concatenate([[False], cond[:-1]])
    c = df5["close"].to_numpy(float)
    return edge, np.where(edge, c - 4.0 * a, np.nan)


def sig_scaled(df5, a1, thr, steps):
    c = df5["close"].to_numpy(float)
    d = np.abs(c - np.roll(c, BARS_H))
    path = sum(np.roll(d, BARS_H * k) for k in range(20))     # hourly-stride path over 20 h (same as ER(20) on 1h bars)
    with np.errstate(invalid="ignore", divide="ignore"):
        er = np.abs(c - np.roll(c, 20 * BARS_H)) / path
    ok = np.ones(len(c), bool)
    for k in range(steps):
        prev = np.roll(c, BARS_H * (k + 1)); cur = np.roll(c, BARS_H * k) if k else c
        ok &= cur > prev
    h = df5.index.hour
    cond = (er > thr) & ok & ~((h >= 8) & (h < 14))
    cond[: 20 * BARS_H + steps * BARS_H] = False
    edge = cond & ~np.concatenate([[False], cond[:-1]])
    return edge, np.where(edge, c - 4.0 * a1, np.nan)


def sig_hybrid(df5, df1, a1_5, k):
    edge1, a1 = v2_1h(df1)
    o5, h5, l5, c5 = arr(df5)
    n5 = len(c5)
    idx = df5.index
    sd = np.zeros(n5, bool)
    stop = np.full(n5, np.nan)
    sig_pos = np.flatnonzero(edge1)
    for p in sig_pos:
        t_open = df1.index[p] + pd.Timedelta(hours=1)          # first 5m bar after the signal hour closed
        s = idx.searchsorted(t_open)
        if s >= n5 - BARS_H:
            continue
        sigc = df1["close"].iloc[p]
        st = sigc - 4.0 * a1[p]
        dipped = False
        for j in range(s, min(s + BARS_H, n5)):
            if l5[j] <= sigc - k * a1[p]:
                dipped = True
            if dipped and c5[j] > o5[j]:
                sd[j] = True
                stop[j] = st
                break
    return sd, stop


def stats(tr, label, ep_note=""):
    s = summarize(tr)
    net = np.array([t.net_r for t in tr]) if tr else np.array([])
    eq, peak, dd = 1.0, 1.0, 0.0
    for r in net:
        eq *= 1 + 0.02 * r
        peak = max(peak, eq); dd = max(dd, (peak - eq) / peak)
    return dict(label=label, n=s["n"], win=s["win_rate"] * 100, net_r=s["net_r"], avg_r=s["avg_net_r"], pf=s["pf"],
                dd_r=s["max_dd_r"], t=s["t_stat"], eq2=eq, dd2=dd * 100, cost_r=s["cost_r"])


def thirds(tr, df, n_parts=3):
    if not tr:
        return [0.0] * n_parts
    ts = np.array([df.index[t.entry_idx].value for t in tr])
    edges = np.linspace(df.index[0].value, df.index[-1].value, n_parts + 1)
    return [float(sum(t.net_r for t, x in zip(tr, ts) if edges[i] <= x < edges[i + 1] + 1)) for i in range(n_parts)]


def report(df5, label):
    df1 = to_1h(df5)
    a1_5 = atr1h_on_5m(df5, df1)
    ep_h = replace(EP5, **HARSH)
    out, rows, trades = [], [], {}

    # reference on real 1h bars
    e1, a1 = v2_1h(df1)
    c1 = df1["close"].to_numpy(float)
    st1 = np.where(e1, c1 - 4.0 * a1, np.nan)
    tr = go(df1, e1, st1, re_.EP, 700)
    rows.append((stats(tr, "base1h (v2 on 1h)"), thirds(tr, df1), stats(go(df1, e1, st1, replace(re_.EP, **HARSH), 700), "")))
    trades["base1h"] = (df1, tr)

    def add(name, sd, stop):
        t = go(df5, sd, stop, EP5)
        th = go(df5, sd, stop, ep_h)
        rows.append((stats(t, name), thirds(t, df5), stats(th, "")))
        trades[name] = (df5, t)

    sd, st = sig_lit5m(df5); add("lit5m (same rule on 5m)", sd, st)
    for thr in (0.35, 0.40, 0.50):
        for steps in (2, 3):
            sd, st = sig_scaled(df5, a1_5, thr, steps); add(f"scaled5m er>{thr:.2f} {steps}h up", sd, st)
    for k in (0.0, 0.3, 0.6, 1.0):
        sd, st = sig_hybrid(df5, df1, a1_5, k); add(f"hyb dip {k:.1f} ATR", sd, st)

    out += [f"# {label}: {60 // BARS_H}-minute candle study", "",
            f"{len(df5)} {60 // BARS_H}m bars, {df5.index[0]:%Y-%m-%d} to {df5.index[-1]:%Y-%m-%d}. Costs: 0.06% fee + 0.02% slip per side; "
            f"harsh = 0.10% + 0.05%. R-based, 2% risk equity (x start).", "",
            "| variant | trades | win% | net R | avg R | PF | max DD R | t-stat | 2% equity (x) | DD% | net R third 1 / 2 / 3 | harsh-fee net R | harsh PF |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s, th, hs in rows:
        out.append(f"| {s['label']} | {s['n']} | {s['win']:.0f} | {s['net_r']:+.1f} | {s['avg_r']:+.3f} | {s['pf']:.2f} | {s['dd_r']:.1f} | "
                   f"{s['t']:.1f} | {s['eq2']:.2f} | {s['dd2']:.0f} | {th[0]:+.1f} / {th[1]:+.1f} / {th[2]:+.1f} | {hs['net_r']:+.1f} | {hs['pf']:.2f} |")
    out += ["", "How to read: base1h is the current plan. A 5m variant is only 'better' if net R AND all three thirds AND the harsh-fee column "
            "hold up with enough trades (>=100). Many variants were tried, so the best-looking row is partly luck.", ""]
    return out, trades


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="PAXGUSDT")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--out", default="m5_out")
    ap.add_argument("--tf", type=int, default=5, help="candle minutes: 5 or 15")
    a = ap.parse_args()
    global BARS_H, EP5
    BARS_H = 60 // a.tf
    EP5 = replace(re_.EP, max_hold=480 * BARS_H)
    Path(a.out).mkdir(exist_ok=True)
    df5 = fetch_klines(a.symbol, f"{a.tf}m", a.days, a.tf * 60_000)
    L, trades = report(df5, a.symbol)
    Path(a.out, "summary.md").write_text("\n".join(L))
    for k, (d, tr) in trades.items():
        if tr:
            pd.DataFrame([dict(t=str(d.index[x.entry_idx]), exit=str(d.index[x.exit_idx]), entry=x.entry, stop=x.stop, reason=x.reason,
                               risk_pct=x.risk_pct, net_r=x.net_r) for x in tr]).to_csv(Path(a.out, f"trades_{k.split()[0]}_{abs(hash(k))%1000}.csv"), index=False)
    print("\n".join(L))


if __name__ == "__main__":
    main()
