"""Loss-reduction tests on the final BTC setup (Time Frame Combo + volume 1.5x, 3R target).

Tests: skip Monday (IST), stop new trades after 21:00 IST, breakeven (SL -> entry + costs once price reaches 1/1.5/2R).
TRAIN = first 2 years, TEST = last 365 days. Also reports how far losing trades went in profit before the stop (MFE).
Research only: no orders.
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import pandas as pd

from .reverse_eng import fetch_klines
from .tfcombo import M5, build, find_setups, simulate, stats, compound, mdtable
from .tfcombo_ind import features, filt

WINDOWS = {"12:30-23:30": [(750, 1410)], "12:30-21:00": [(750, 1260)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--fee", type=float, default=0.0008)
    ap.add_argument("--out", default="tfloss_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    m5 = fetch_klines(a.symbol, "5m", a.days, M5)
    cut = (m5.index[-1] - pd.Timedelta(days=365)).tz_localize(None)
    D = build(m5)
    F = features(m5, D)
    S = [s for s in find_setups(D, use_bias=True, eql_only=False, win=8) if filt("volume1.5x", F, s)]
    rows, base = [], None
    for (wn, w), mon, be in itertools.product(WINDOWS.items(), [False, True], [None, 1.0, 1.5, 2.0]):
        t = simulate(S, m5, D, entry="mkt", tp="3", fee=a.fee, window=w, be=be, skip_dow={0} if mon else None)
        name = f"{wn} | {'skip Mon' if mon else 'all days'} | BE {be or 'off'}"
        if base is None:
            base = t
        tr, te = t[t.time < cut], t[t.time >= cut]
        s1, s2 = stats(tr), stats(te)
        rows.append(dict(cfg=name, TR_trades=s1["trades"], TR_win=s1["win"], TR_avgR=s1["avgR"], TR_totR=s1["totR"],
                         TR_maxDD_R=s1["maxDD_R"], TE_trades=s2["trades"], TE_win=s2["win"], TE_avgR=s2["avgR"],
                         TE_totR=s2["totR"], TE_maxDD_R=s2["maxDD_R"], lakh_3y_2pct=compound(t, 0.02, 100000),
                         lakh_1y_2pct=compound(te, 0.02, 100000)))
        t.to_csv(out / f"trades_{name.replace(' | ', '_').replace(' ', '').replace(':', '')}.csv", index=False)
    R = pd.DataFrame(rows)
    R.to_csv(out / "grid.csv", index=False)
    los = base[base.result == "SL"]
    bins = pd.cut(los.mfe_R, [-0.01, 0.5, 1.0, 1.5, 2.0, 3.0]).value_counts().sort_index()
    md = ["# Loss-reduction tests (BTC, final setup + volume 1.5x, 3R)", "",
          f"TRAIN < {cut:%Y-%m-%d} <= TEST. Breakeven moves SL to entry+costs from the candle AFTER price reaches the level.", "",
          mdtable(R), "",
          "## How far did stopped-out trades go in profit first? (base setup)", "",
          "| max profit before SL (R) | trades |", "|---|---|"] + [f"| {k} | {v} |" for k, v in bins.items()]
    (out / "summary.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
