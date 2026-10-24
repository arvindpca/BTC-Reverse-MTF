"""Grid search with a strict time split, run on a GitHub Actions runner (or any machine with internet).

  python -m app.research --assets BTCUSDT PAXGUSDT --days 180
  python -m app.research --assets BTCUSDT PAXGUSDT --days 30 --warmup 20 --profile big --min-trades 8
  python -m app.research --assets XAUUSD --csv XAUUSD=xau_1m.csv --days 180
  python -m app.research --synthetic --days 20 --quick      # pipeline smoke test only

Profiles: "small" = 15m sweeps / 1h RSI (tight stops, many trades);
          "big"   = 1h sweeps / 4h RSI (wide stops, few trades, costs matter less).
`--warmup N` fetches N extra days BEFORE the traded window so 4h indicators are warm; nothing trades in them.

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
                   htf=["any", "with", "range"], invert=[False, True], confirm_5m=[False, True])
ENGINE_GRID = dict(rr=[1.5, 2.0, 3.0], be_r=[None, 1.0])
QUICK_SIGNAL = dict(rsi_lo=[40.0], sweep_lookback=[8], setup_valid=[4], htf=["any", "range"], invert=[False, True])
QUICK_ENGINE = dict(rr=[2.0], be_r=[None])

BIG_SIGNAL = dict(rsi_lo=[35.0, 40.0], sweep_lookback=[12, 24], setup_valid=[2, 4], htf=["any", "with"],
                  invert=[False, True], setup_tf=[60], stretch_tf=[240], trig_lookback=[5, 15])
BIG_ENGINE = dict(rr=[2.0, 3.0], be_r=[None, 1.0])
BIG_FIXED = dict(min_risk_pct=0.5, max_risk_pct=6.0, max_hold=2880)  # stops >= 0.5%, hold up to 48h

PROFILES = {"small": (SIGNAL_GRID, ENGINE_GRID, {}), "big": (BIG_SIGNAL, BIG_ENGINE, BIG_FIXED)}


def _product(grid: dict):
    keys = list(grid)
    for vals in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, vals))


def run_asset(name: str, df: pd.DataFrame, split: float, quick: bool, profile: str = "small",
              trade_days: int | None = None) -> tuple[pd.DataFrame, dict]:
    feat = compute_features(df)
    n = len(feat.c)
    start = max(0, n - trade_days * 1440) if trade_days else 0
    cut = start + int((n - start) * split)
    sgrid, egrid, fixed = (QUICK_SIGNAL, QUICK_ENGINE, {}) if quick else PROFILES[profile]
    rows = []
    for sp in _product(sgrid):
        sig = build_signals(feat, SignalParams(**sp))
        for ep in _product(egrid):
            eng = EngineParams(**ep, **fixed)
            tr = run(feat.o, feat.h, feat.l, feat.c, sig.side, sig.stop, sig.setup_id, eng, start, cut)
            te = run(feat.o, feat.h, feat.l, feat.c, sig.side, sig.stop, sig.setup_id, eng, cut, n)
            a, b = summarize(tr), summarize(te)
            rows.append({"asset": name, **sp, **ep,
                         **{f"train_{k}": v for k, v in a.items()}, **{f"test_{k}": v for k, v in b.items()}})
    grid = pd.DataFrame(rows)
    meta = dict(asset=name, bars=n - start, start=str(feat.index[start]), end=str(feat.index[-1]),
                split_time=str(feat.index[cut]), configs=len(grid), profile="quick" if quick else profile)
    return grid, meta


def overall(grid: pd.DataFrame, min_trades: int) -> dict:
    out = {}
    for part in ("train", "test"):
        m = grid[grid[f"{part}_n"] >= min_trades]
        tn = float(m[f"{part}_n"].sum())
        out[part] = dict(configs=len(m), trades=(m[f"{part}_n"].min() if len(m) else 0, m[f"{part}_n"].median() if len(m) else 0,
                                                 m[f"{part}_n"].max() if len(m) else 0),
                         gross=(m[f"{part}_gross_r"].sum() / tn) if tn else 0.0,
                         cost=(m[f"{part}_cost_r"].sum() / tn) if tn else 0.0,
                         net=(m[f"{part}_net_r"].sum() / tn) if tn else 0.0,
                         pos=float((m[f"{part}_net_r"] > 0).mean()) if len(m) else 0.0)
    return out


def verdict(grid: pd.DataFrame, min_trades: int = 30) -> tuple[str, dict]:
    reach = grid[grid.train_n >= min_trades]
    if reach.empty:
        return f"INCONCLUSIVE: no config reached {min_trades} trades on the train part - too little data to judge.", {}
    cand = reach.sort_values("train_net_r", ascending=False)
    cand = cand[cand.train_net_r > 0]
    if cand.empty:
        return "NO EDGE: no config was profitable on the train part (with enough trades).", {}
    top = cand.head(10)
    best = top.iloc[0]
    pos_share = float((top.test_net_r > 0).mean())
    info = dict(best=best, top=top, top10_test_positive_share=pos_share,
                share_all_configs_test_positive=float((grid.test_net_r > 0).mean()))
    if best.test_n < min_trades:
        return f"INCONCLUSIVE: the best train config made only {int(best.test_n)} test trades (< {min_trades}).", info
    ok = best.test_net_r > 0 and best.test_t_stat >= 2.0 and pos_share >= 0.6
    if ok:
        return "CANDIDATE: held-out test is positive, t-stat >= 2 and most of the top-10 agree. Still needs forward/paper testing.", info
    return "NO EDGE PROVEN: the train winner does not hold up on the untouched test part (or weak t-stat).", info


def fmt(x, nd=2):
    return f"{x:.{nd}f}" if isinstance(x, (float, np.floating)) else str(x)


def report(results: list[tuple[str, dict, pd.DataFrame]], out: Path, min_trades: int = 30) -> str:
    lines = ["# BTC / PAXG / XAU multi-timeframe reverse strategy - research report", "",
             "Costs: 0.06% fee + 0.02% slippage per side. R = initial risk. Selection on TRAIN only; TEST is held out.", ""]
    for name, meta, grid in results:
        v, info = verdict(grid, min_trades)
        o = overall(grid, min_trades)
        lines += [f"## {name} (profile: {meta['profile']})",
                  f"- traded window: {meta['bars']} 1m bars, {meta['start']} -> {meta['end']}",
                  f"- train/test split at {meta['split_time']} ({meta['configs']} configs tried, min {min_trades} trades)",
                  f"- **verdict: {v}**"]
        for part in ("train", "test"):
            d = o[part]
            lines.append(f"- all configs, {part}: {d['configs']} configs with enough trades | trades/config min {int(d['trades'][0])} "
                         f"median {int(d['trades'][1])} max {int(d['trades'][2])} | gross {fmt(d['gross'], 3)}R, cost {fmt(d['cost'], 3)}R, "
                         f"net {fmt(d['net'], 3)}R per trade | profitable configs {fmt(d['pos'] * 100, 0)}%")
        if info:
            b = info["best"]
            lines += [f"- top-10 train configs profitable on test: {fmt(info['top10_test_positive_share'] * 100, 0)}%", "",
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
    ap.add_argument("--days", type=int, default=180, help="length of the TRADED window in days")
    ap.add_argument("--warmup", type=int, default=0, help="extra days fetched before the window (indicator warm-up, no trades)")
    ap.add_argument("--profile", choices=sorted(PROFILES), default="small")
    ap.add_argument("--min-trades", type=int, default=30)
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
        total_days = a.days + a.warmup
        df = make_synthetic(n=total_days * 1440) if a.synthetic else get_1m(name, total_days, cache_dir=a.cache, csv_map=csv_map)
        grid, meta = run_asset(name, df, a.split, a.quick, a.profile, trade_days=a.days if a.warmup else None)
        grid.to_csv(out / f"grid_{name}.csv", index=False)
        results.append((name, meta, grid))
    print(report(results, out, a.min_trades))


if __name__ == "__main__":
    main()
