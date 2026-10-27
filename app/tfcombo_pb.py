"""Pullback-entry test on the final BTC setup (Time Frame Combo + volume 1.5x, IST 12:30-23:30).

Instead of buying at market after the 15m ChoCH, place a limit order k x (price -> SL distance) closer to the SL.
k = 0.2 / 0.33 / 0.5, valid 1h or 4h (else the trade is skipped). Target either 3R of the NEW (smaller) risk,
or the SAME price a market entry would target. TRAIN = first 2 years, TEST = last 365 days. Research only.
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import pandas as pd

from .reverse_eng import fetch_klines
from .tfcombo import M5, build, find_setups, simulate, stats, compound, mdtable
from .tfcombo_ind import features, filt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--fee", type=float, default=0.0008)
    ap.add_argument("--out", default="tfpb_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    m5 = fetch_klines(a.symbol, "5m", a.days, M5)
    cut = (m5.index[-1] - pd.Timedelta(days=365)).tz_localize(None)
    D = build(m5)
    F = features(m5, D)
    S = [s for s in find_setups(D, use_bias=True, eql_only=False, win=8) if filt("volume1.5x", F, s)]
    combos = [("mkt", 24, "3")] + [(f"pbR{k}", v, tp) for k, v, tp in
                                    itertools.product(["0.2", "0.33", "0.5"], [12, 48], ["3", "m3", "4"])]
    rows = []
    for entry, valid, tp in combos:
        t = simulate(S, m5, D, entry=entry, tp=tp, fee=a.fee, window=[(750, 1410)], pb_valid=valid)
        tr, te = t[t.time < cut], t[t.time >= cut]
        s1, s2 = stats(tr), stats(te)
        name = "market (now)" if entry == "mkt" else \
            f"pullback {entry[3:]} | wait {valid // 12}h | TP {'same price' if tp.startswith('m') else tp + 'R'}"
        rows.append(dict(cfg=name, TR_trades=s1["trades"], TR_win=s1["win"], TR_avgR=s1["avgR"], TR_totR=s1["totR"],
                         TE_trades=s2["trades"], TE_win=s2["win"], TE_avgR=s2["avgR"], TE_totR=s2["totR"],
                         TE_maxDD_R=s2["maxDD_R"], lakh_3y_2pct=compound(t, 0.02, 100000),
                         lakh_1y_2pct=compound(te, 0.02, 100000)))
        t.to_csv(out / f"trades_{entry}_{valid}_{tp}.csv", index=False)
    R = pd.DataFrame(rows)
    R.to_csv(out / "grid.csv", index=False)
    md = ["# Pullback entry test (BTC final setup + volume 1.5x)", "",
          f"Signals available: {len(S)} (before time window). TRAIN < {cut:%Y-%m-%d} <= TEST.", "", mdtable(R), ""]
    (out / "summary.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
