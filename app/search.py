"""Broad strategy search on BTC + PAXG with a held-out test and cross-asset pooling.

  python -m app.search --assets BTCUSDT PAXGUSDT --days 180 --warmup 20

Families: sweep (small/big, from research.py) + donchian + bollinger + ema_sar (families.py).
Every config is ranked on TRAIN only. A config counts as ROBUST only if, on the untouched TEST part, it is
positive on BOTH assets pooled and on each asset, with enough trades and a pooled t-stat >= 2, and most of the
top-10 pooled train configs also hold up. Trying hundreds of configs always finds something that looks good on
past data, so nothing is called robust without passing that gate.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import get_1m
from .engine import EngineParams, run, summarize
from .families import bollinger, donchian, ema_sar
from .research import BIG_ENGINE, BIG_FIXED, BIG_SIGNAL, ENGINE_GRID, SIGNAL_GRID
from .signals import SignalParams, build_signals, compute_features
from .synthetic import make_synthetic

TREND_FIXED = dict(min_risk_pct=0.5, max_risk_pct=8.0, max_hold=10080)  # up to 7 days
FADE_FIXED = dict(min_risk_pct=0.5, max_risk_pct=8.0, max_hold=2880)
SWEEP_BUILD = lambda f, **kw: build_signals(f, SignalParams(**kw))  # noqa: E731

FAMILIES = {
    "donchian": (donchian, dict(N=[20, 40, 80], atr_mult=[1.5, 2.5], htf=["any", "with"], confirm15=[False, True],
                                invert=[False, True]), dict(trail_r=[2.0, 3.0], rr=[50.0]), TREND_FIXED),
    "bollinger": (bollinger, dict(k=[2.0, 2.5], atr_mult=[1.5, 2.5], htf=["any", "range"], invert=[False, True]),
                  dict(rr=[1.0, 1.5, 2.0]), FADE_FIXED),
    "ema_sar": (ema_sar, dict(fast=[12, 24], slow=[48, 96], atr_mult=[1.5, 2.5], htf=["any", "with"],
                              invert=[False, True]), dict(trail_r=[2.0, 3.0], rr=[50.0]), TREND_FIXED),
    "sweep_small": (SWEEP_BUILD, SIGNAL_GRID, ENGINE_GRID, {}),
    "sweep_big": (SWEEP_BUILD, BIG_SIGNAL, BIG_ENGINE, BIG_FIXED),
}
QUICK = ("donchian", "bollinger")


def _product(grid: dict):
    keys = list(grid)
    for vals in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, vals))


def search_asset(name: str, df: pd.DataFrame, trade_days: int, split: float, families=None) -> tuple[pd.DataFrame, dict]:
    feat = compute_features(df)
    n = len(feat.c)
    start = max(0, n - trade_days * 1440)
    cut = start + int((n - start) * split)
    rows = []
    for fam in families or FAMILIES:
        fn, sgrid, egrid, fixed = FAMILIES[fam]
        for sp in _product(sgrid):
            sig = fn(feat, **sp)
            for ep in _product(egrid):
                eng = EngineParams(**ep, **fixed)
                a = summarize(run(feat.o, feat.h, feat.l, feat.c, sig.side, sig.stop, sig.setup_id, eng, start, cut))
                b = summarize(run(feat.o, feat.h, feat.l, feat.c, sig.side, sig.stop, sig.setup_id, eng, cut, n))
                cfg = json.dumps({**sp, **ep}, sort_keys=True, default=str)
                rows.append({"asset": name, "family": fam, "cfg": cfg,
                             **{f"train_{k}": v for k, v in a.items()}, **{f"test_{k}": v for k, v in b.items()}})
    meta = dict(asset=name, start=str(feat.index[start]), end=str(feat.index[-1]), split_time=str(feat.index[cut]))
    return pd.DataFrame(rows), meta


def _t(net: float, ss: float, n: float) -> float:
    if n < 2:
        return 0.0
    mean = net / n
    var = (ss - n * mean * mean) / (n - 1)
    return float(mean / (np.sqrt(var) / np.sqrt(n))) if var > 0 else 0.0


def pool(grids: list[pd.DataFrame]) -> pd.DataFrame:
    """Same config across assets -> one pooled row (+ per-asset train/test net R columns)."""
    allg = pd.concat(grids, ignore_index=True)
    out = []
    for (fam, cfg), g in allg.groupby(["family", "cfg"], sort=False):
        if g.asset.nunique() < len(grids):
            continue
        row = {"family": fam, "cfg": cfg}
        for part in ("train", "test"):
            n, net, ss = g[f"{part}_n"].sum(), g[f"{part}_net_r"].sum(), g[f"{part}_ss"].sum()
            row.update({f"{part}_n": n, f"{part}_net_r": net, f"{part}_gross_r": g[f"{part}_gross_r"].sum(),
                        f"{part}_cost_r": g[f"{part}_cost_r"].sum(), f"{part}_net_half_r": g[f"{part}_net_half_r"].sum(),
                        f"{part}_avg_net_r": net / n if n else 0.0, f"{part}_t_stat": _t(net, ss, n)})
            for _, r in g.iterrows():
                row[f"{part}_net_{r.asset}"] = r[f"{part}_net_r"]
                row[f"{part}_n_{r.asset}"] = r[f"{part}_n"]
        out.append(row)
    return pd.DataFrame(out)


def judge(pooled: pd.DataFrame, assets: list[str], min_trades: int = 40) -> tuple[str, pd.DataFrame, dict]:
    reach = pooled[pooled.train_n >= min_trades]
    cand = reach[reach.train_net_r > 0].sort_values("train_net_r", ascending=False)
    if cand.empty:
        return "NO EDGE: no config was profitable on the pooled train part.", cand, {}
    top = cand.head(10)
    best = top.iloc[0]
    each_pos = all(best[f"test_net_{a}"] > 0 for a in assets)
    share = float((top.test_net_r > 0).mean())
    info = dict(best=best, each_asset_positive=each_pos, top10_share=share,
                all_test_positive=float((pooled.test_net_r > 0).mean()))
    if best.test_n < min_trades:
        return f"INCONCLUSIVE: best train config made only {int(best.test_n)} pooled test trades.", top, info
    if best.test_net_r > 0 and best.test_t_stat >= 2.0 and each_pos and share >= 0.6:
        return "ROBUST CANDIDATE: positive on held-out test (pooled and per asset), t-stat >= 2, top-10 agree. Needs paper testing.", top, info
    return "NO EDGE PROVEN: the pooled train winner does not hold up on the untouched test part.", top, info


def _row(r, assets) -> str:
    per = " / ".join(f"{a[:3]} {r[f'test_net_{a}']:+.1f}R({int(r[f'test_n_{a}'])})" for a in assets)
    return (f"| {r.family} | `{r.cfg}` | {int(r.train_n)} | {r.train_net_r:+.1f} | {int(r.test_n)} | {r.test_net_r:+.1f} | "
            f"{r.test_avg_net_r:+.3f} | {r.test_t_stat:+.2f} | {r.test_net_half_r:+.1f} | {per} |")


def report(pooled: pd.DataFrame, metas: list[dict], assets: list[str], out: Path, min_trades: int) -> str:
    v, top, info = judge(pooled, assets, min_trades)
    L = ["# BTC + PAXG strategy search (4h / 1h / 15m / 1m)", "",
         f"Window {metas[0]['start']} -> {metas[0]['end']}; train/test split {metas[0]['split_time']}. "
         f"Costs 0.06% fee + 0.02% slippage per side. {len(pooled)} configs x {len(assets)} assets, ranked on TRAIN only.", "",
         f"## Verdict: {v}", ""]
    if info:
        L += [f"- configs profitable on pooled test (all): {info['all_test_positive'] * 100:.0f}%",
              f"- top-10 pooled train configs profitable on test: {info['top10_share'] * 100:.0f}%",
              f"- best config positive on every asset's test: {info['each_asset_positive']}", ""]
    L += ["## Top-10 by pooled TRAIN net R (test columns = untouched data)", "",
          "| family | config | train n | train R | test n | test R | test R/trade | test t | test R @half cost | test per asset |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    L += [_row(r, assets) for _, r in top.iterrows()] if len(top) else []
    reach = pooled[pooled.test_n >= min_trades]
    L += ["", "## By family (configs with enough test trades)", "", "| family | configs | mean test R/trade | profitable on test |", "|---|---|---|---|"]
    for fam, g in reach.groupby("family"):
        L.append(f"| {fam} | {len(g)} | {g.test_net_r.sum() / g.test_n.sum():+.3f} | {(g.test_net_r > 0).mean() * 100:.0f}% |")
    text = "\n".join(L) + "\n"
    (out / "summary.md").write_text(text)
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", nargs="*", default=["BTCUSDT", "PAXGUSDT"])
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--split", type=float, default=0.6)
    ap.add_argument("--min-trades", type=int, default=40)
    ap.add_argument("--families", nargs="*", default=None)
    ap.add_argument("--out", default="results")
    ap.add_argument("--cache", default="data_cache")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fams = a.families or (list(QUICK) if a.quick else None)
    grids, metas = [], []
    for k, name in enumerate(["SYN_A", "SYN_B"] if a.synthetic else a.assets):
        df = make_synthetic(n=(a.days + a.warmup) * 1440, seed=7 + k) if a.synthetic else get_1m(name, a.days + a.warmup, cache_dir=a.cache)
        g, m = search_asset(name, df, a.days, a.split, fams)
        g.to_csv(out / f"grid_{name}.csv", index=False)
        grids.append(g)
        metas.append(m)
    assets = [g.asset.iloc[0] for g in grids]
    pooled = pool(grids)
    pooled.to_csv(out / "pooled.csv", index=False)
    print(report(pooled, metas, assets, out, a.min_trades))


if __name__ == "__main__":
    main()
