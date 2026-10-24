"""Grid search with a strict time split, run on a GitHub Actions runner (or any machine with internet).

  python -m app.research --assets BTCUSDT PAXGUSDT --days 180
  python -m app.research --assets XAUUSD --csv XAUUSD=xau_1m.csv --days 180
  python -m app.research --synthetic --days 20 --quick      # pipeline smoke test only

Configs are RANKED ON THE TRAIN PART ONLY. The held-out test part is never used for selection; it is the
honest number. With many configs tried, the best train config usually looks good by luck - so the verdict
also checks the whole top-10 on test, not just the winner.
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from .data import get_1m
from .engine import EngineParams, run, summarize
from .signals import SignalParams, build_signals, compute_features
from .synthetic import make_synthetic

SIGNAL_GRID = dict(rsi_lo=[30.0, 35.0, 40.0], sweep_lookback=[8, 16], setup_valid=[2, 4],
                   htf=["any", "with", "range"], invert=[False, True])
ENGINE_GRID = dict(rr=[1.5, 2.0, 3.0], be_r=[None, 1.0])
QUICK_SIGNAL = dict(rsi_lo=[40.0], sweep_lookback=[8], setup_valid=[4], htf=["any", "range"], invert=[False, True])
QUICK_ENGINE = dict(rr=[2.0], be_r=[None])

MIN_TRAIN_TRADES = 30
MIN_TEST_TRADES = 30


def _product(grid: dict):
    keys = list(grid)
    for vals in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, vals))


def run_asset(name: str, df: pd.DataFrame, split: float, quick: bool) -> tuple[pd.DataFrame, dict]:
    feat = compute_features(df)
    n = len(feat.c)
    cut = int(n * split)
    sgrid, egrid = (QUICK_SIGNAL, QUICK_ENGINE) if quick else (SIGNAL_GRID, ENGINE_GRID)
    rows = []
    for sp in _product(sgrid):
        sig = build_signals(feat, SignalParams(**sp))
        for ep in _product(egrid):
            eng = EngineParams(**ep)
            tr = run(feat.o, feat.h, feat.l, feat.c, sig.side, sig.stop, sig.setup_id, eng, 0, cut)
            te = run(feat.o, feat.h, feat.l, feat.c, sig.side, sig.stop, sig.setup_id, eng, cut, n)
            a, b = summarize(tr), summarize(te)
            rows.append({"asset": name, **sp, **{k: v for k, v in ep.items()},
                         **{f"train_{k}": v for k, v in a.items()}, **{f"test_{k}": v for k, v in b.items()}})
    grid = pd.DataFrame(rows)
    meta = dict(asset=name, bars=n, start=str(feat.index[0]), end=str(feat.index[-1]),
                split_time=str(feat.index[cut]), configs=len(grid))
    return grid, meta


def verdict(grid: pd.DataFrame) -> tuple[str, dict]:
    cand = grid[grid.train_n >= MIN_TRAIN_TRADES].sort_values("train_net_r", ascending=False)
    cand = cand[cand.train_net_r > 0]
    if cand.empty:
        return "NO EDGE: no config was profitable on the train part with enough trades.", {}
    top = cand.head(10)
    best = top.iloc[0]
    pos_share = float((top.test_net_r > 0).mean())
    info = dict(best=best, top=top, top10_test_positive_share=pos_share,
                share_all_configs_test_positive=float((grid.test_net_r > 0).mean()))
    ok = (best.test_net_r > 0 and best.test_n >= MIN_TEST_TRADES and best.test_t_stat >= 2.0 and pos_share >= 0.6)
    if ok:
        return "CANDIDATE: held-out test is positive, t-stat >= 2 and most of the top-10 agree. Still needs forward/paper testing.", info
    return "NO EDGE PROVEN: the train winner does not hold up on the untouched test part (or too few trades / weak t-stat).", info


def fmt(x, nd=2):
    return f"{x:.{nd}f}" if isinstance(x, (float, np.floating)) else str(x)


def report(results: list[tuple[str, dict, pd.DataFrame]], out: Path) -> str:
    lines = ["# BTC / PAXG / XAU multi-timeframe reverse strategy - research report", "",
             "Costs: 0.06% fee + 0.02% slippage per side. R = initial risk. Selection on TRAIN only; TEST is held out.", ""]
    for name, meta, grid in results:
        v, info = verdict(grid)
        lines += [f"## {name}", f"- data: {meta['bars']} 1m bars, {meta['start']} -> {meta['end']}",
                  f"- train/test split at {meta['split_time']} ({meta['configs']} configs tried)",
                  f"- **verdict: {v}**"]
        if info:
            b = info["best"]
            lines += [f"- share of ALL configs profitable on test: {fmt(info['share_all_configs_test_positive'] * 100, 0)}%",
                      f"- top-10 train configs profitable on test: {fmt(info['top10_test_positive_share'] * 100, 0)}%", "",
                      "Best train config:", "",
                      f"`rsi_lo={b.rsi_lo} sweep_lookback={b.sweep_lookback} setup_valid={b.setup_valid} htf={b.htf} "
                      f"invert={b.invert} rr={b.rr} be_r={b.be_r}`", "",
                      "| part | trades | win% | net R | avg net R | gross R | cost R | PF | maxDD R | t-stat |",
                      "|---|---|---|---|---|---|---|---|---|---|"]
            for part in ("train", "test"):
                g = lambda k: b[f"{part}_{k}"]
                lines.append(f"| {part} | {int(g('n'))} | {fmt(g('win_rate') * 100, 1)} | {fmt(g('net_r'))} | "
                             f"{fmt(g('avg_net_r'), 3)} | {fmt(g('gross_r'))} | {fmt(g('cost_r'))} | {fmt(g('pf'))} | "
                             f"{fmt(g('max_dd_r'))} | {fmt(g('t_stat'))} |")
        lines.append("")
    text = "\n".join(lines)
    (out / "summary.md").write_text(text)
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", nargs="*", default=["BTCUSDT", "PAXGUSDT"])
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--split", type=float, default=0.6)
    ap.add_argument("--csv", nargs="*", default=[], help="SYMBOL=path.csv (e.g. XAUUSD=xau_1m.csv)")
    ap.add_argument("--out", default="results")
    ap.add_argument("--cache", default="data_cache")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--synthetic", action="store_true", help="smoke test on fake data; results are meaningless")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    csv_map = dict(kv.split("=", 1) for kv in a.csv)

    results = []
    names = ["SYNTHETIC"] if a.synthetic else a.assets
    for name in names:
        df = make_synthetic(n=a.days * 1440) if a.synthetic else get_1m(name, a.days, cache_dir=a.cache, csv_map=csv_map)
        grid, meta = run_asset(name, df, a.split, a.quick)
        grid.to_csv(out / f"grid_{name}.csv", index=False)
        results.append((name, meta, grid))
    print(report(results, out))


if __name__ == "__main__":
    main()
