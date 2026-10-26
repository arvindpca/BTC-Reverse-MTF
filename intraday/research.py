"""PAXG / BTC CoinDCX futures intraday research pipeline (5m + 15m).

python -m intraday.research --out intraday_out                 # fetch from CoinDCX, then research
python -m intraday.research --out x --source synthetic         # offline smoke run (fake data, pipeline check only)
python -m intraday.research --out x --source csv --csv-dir d   # use saved raw CSVs (<PAIR>_<tf>_raw.csv.gz)

Discipline: configs are ranked on DEV (first 50%) and VAL (next 25%) only. The last 25% (TEST) is evaluated
once, for the finalists and the baselines. Nothing is tuned after looking at TEST.
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from .clean import clean, quality_verdict
from .data import TF_MIN, DataError, check_instrument, fetch_candles, load_csv, save_raw
from .engine import Bars, candidates, net_returns, select
from .features import build
from .metrics import equity_curve, stats
from .signals import families, filters

SEGS = ("dev", "val", "test")


class Log:
    def __init__(self, path: Path):
        self.f = open(path, "a")

    def __call__(self, *a):
        msg = " ".join(str(x) for x in a)
        print(msg, flush=True)
        self.f.write(msg + "\n")
        self.f.flush()


# ----------------------------------------------------------------------------------------------- core study
class Study:
    def __init__(self, f: pd.DataFrame, tf: str, cfg: dict, log):
        self.f, self.tf, self.cfg, self.log = f, tf, cfg, log
        self.bars = Bars.from_frame(f, TF_MIN[tf])
        n = len(f)
        s = cfg["split"]
        self.cuts = [cfg["warmup_bars"], int(n * s[0]), int(n * (s[0] + s[1])), n]
        self.fams = families(f, cfg["seed"], 0)
        self.flts = filters(f)
        self.holds = {h: max(1, int(h * 60 / TF_MIN[tf])) for h in cfg["max_hold_hours"]}
        self.cost = C.cost_per_side_pct(cfg)
        self.fund = cfg["funding_pct_per_8h"]
        self.cache: dict = {}

    def cand(self, fam, side, sl, rr, hold_h, masks=None):
        key = (fam, side, sl, rr, hold_h)
        if key not in self.cache:
            m = (masks or self.fams)[fam][0 if side > 0 else 1]
            self.cache[key] = candidates(self.bars, m, side, sl, rr, self.holds[hold_h], self.cfg["warmup_bars"],
                                          self.cfg.get("min_stop_pct", 0.0))
        return self.cache[key]

    def keep_mask(self, cand, side, flt_names):
        if not flt_names:
            return None
        k = np.ones(len(cand.sig), bool)
        for name in flt_names:
            k &= self.flts[name][0 if side > 0 else 1][cand.sig]
        return k

    def trades(self, cand, keep=None, cost_mult=1.0):
        taken = select(cand, keep)
        net, R, gR = net_returns(cand, taken, C.cost_per_side_pct(self.cfg, cost_mult), self.fund * (cost_mult > 0))
        seg = np.digitize(cand.sig[taken], self.cuts[1:3])
        ok = cand.exit_bar[taken] < np.array(self.cuts[1:])[seg]   # trade must finish inside its own segment
        return taken[ok], net[ok], R[ok], gR[ok], seg[ok]

    def seg_stats(self, R, gR, seg, segs=("dev", "val")):
        out = {}
        for i, name in enumerate(SEGS):
            if name not in segs:
                continue
            m = seg == i
            st = stats(R[m], risk=self.cfg["risk_per_trade"])
            for k in ("n", "exp_R", "t_stat", "pf", "win_rate", "max_dd_pct"):
                out[f"{name}_{k}"] = st.get(k, 0)
            out[f"{name}_gross_exp_R"] = round(float(gR[m].mean()), 4) if m.any() else 0.0
        return out

    def run_config(self, fam, side, sl, rr, hold_h, flt=(), segs=("dev", "val"), masks=None):
        cand = self.cand(fam, side, sl, rr, hold_h, masks)
        _, _, R, gR, seg = self.trades(cand, self.keep_mask(cand, side, flt))
        row = {"family": fam, "side": "LONG" if side > 0 else "SHORT", "sl_atr": sl, "rr": rr,
               "hold_h": hold_h, "filters": "+".join(flt) or "-"}
        row.update(self.seg_stats(R, gR, seg, segs))
        return row

    def exits(self):
        return list(itertools.product(self.cfg["sl_atr"], self.cfg["rr"], self.cfg["max_hold_hours"]))


def _score(row, seg, min_n):
    return row.get(f"{seg}_t_stat", -99) if row.get(f"{seg}_n", 0) >= min_n else -99


def run_study(f: pd.DataFrame, tf: str, cfg: dict, out: Path, log, label: str) -> dict:
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    st = Study(f, tf, cfg, log)
    real_fams = [k for k in st.fams if not k.startswith("BASE")]
    rows = []
    # Stage A: every family x side x exit, no filters
    for fam in list(st.fams):
        for side in (1, -1):
            for sl, rr, hh in st.exits():
                r = st.run_config(fam, side, sl, rr, hh)
                r["stage"] = "A_base" if fam in real_fams else "A_baseline"
                rows.append(r)
    log(f"  [{label}] stage A: {len(rows)} configs ({time.time() - t0:.0f}s)")
    A = pd.DataFrame(rows)
    mdev, mval = cfg["min_trades_dev"], cfg["min_trades_val"]
    # Stage B / C: filters on the best base configs, per side
    for side_name, side in (("LONG", 1), ("SHORT", -1)):
        a = A[(A.side == side_name) & (A.stage == "A_base")].copy()
        a["score"] = a.apply(lambda r: _score(r, "dev", mdev), axis=1)
        top = a[a.score > -99].sort_values("score", ascending=False).head(cfg["top_base_per_dir"])
        for _, b in top.iterrows():
            single = []
            for fl in st.flts:
                r = st.run_config(b.family, side, b.sl_atr, b.rr, b.hold_h, (fl,))
                r["stage"] = "B_filter"
                rows.append(r)
                if _score(r, "dev", mdev) > b.score:
                    single.append((_score(r, "dev", mdev), fl))
            best = [fl for _, fl in sorted(single, reverse=True)[: cfg["pair_filters_per_base"]]]
            for f1, f2 in itertools.combinations(best, 2):
                r = st.run_config(b.family, side, b.sl_atr, b.rr, b.hold_h, (f1, f2))
                r["stage"] = "C_pair"
                rows.append(r)
    log(f"  [{label}] stages B/C done: {len(rows)} configs total ({time.time() - t0:.0f}s)")
    E = pd.DataFrame(rows)
    E["sel_score"] = np.minimum(E.apply(lambda r: _score(r, "dev", mdev), axis=1),
                                E.apply(lambda r: _score(r, "val", mval), axis=1))

    # Null control: random entries, same number of families x same exit grid, best DEV t-stat per replicate
    rng = np.random.default_rng(cfg["seed"] + 1)
    null_best = []
    n = len(f)
    for rep in range(cfg["null_seeds"]):
        best = -99
        masks = {f"N{j}": (rng.random(n) < 0.02, rng.random(n) < 0.02) for j in range(len(real_fams))}
        for fam in masks:
            for side in (1, -1):
                for sl, rr, hh in st.exits():
                    cand = candidates(st.bars, masks[fam][0 if side > 0 else 1], side, sl, rr, st.holds[hh],
                                      cfg["warmup_bars"], cfg.get("min_stop_pct", 0.0))
                    _, _, R, gR, seg = st.trades(cand)
                    m = seg == 0
                    if m.sum() >= mdev:
                        best = max(best, stats(R[m])["t_stat"])
        null_best.append(best)
    null_best = np.array(null_best)
    log(f"  [{label}] null control done ({time.time() - t0:.0f}s)")

    # Finalists: ranked by min(dev t, val t); distinct families per side; TEST evaluated only here
    finals, results = [], []
    pool = E[(E.stage != "A_baseline") & (E.sel_score > -99)].sort_values("sel_score", ascending=False)
    for side_name in ("LONG", "SHORT"):
        seen = set()
        for _, r in pool[pool.side == side_name].iterrows():
            if r.family in seen:
                continue
            seen.add(r.family)
            finals.append(r)
            if len(seen) >= cfg["finalists_per_dir"]:
                break
    a_best = E[E.stage == "A_base"].apply(lambda r: _score(r, "dev", mdev), axis=1).max()
    null_pct = float((null_best < a_best).mean()) if len(null_best) else np.nan
    bh = {}
    for i, name in enumerate(SEGS):
        lo, hi = st.cuts[i], st.cuts[i + 1] - 1
        bh[name] = round(100 * (f["close"].iloc[hi] / f["open"].iloc[lo] - 1), 2)
    for k, r in enumerate(finals):
        results.append(finalize(st, r, k, out, label, null_pct))
    # Baseline: every-bar entries, exit chosen on DEV, evaluated on TEST
    base_rows = []
    for side_name in ("LONG", "SHORT"):
        b = E[(E.family == "BASE_every_bar") & (E.side == side_name)].copy()
        b["s"] = b.apply(lambda r: _score(r, "dev", mdev), axis=1)
        if len(b):
            bb = b.sort_values("s", ascending=False).iloc[0]
            row = st.run_config(bb.family, 1 if side_name == "LONG" else -1, bb.sl_atr, bb.rr, bb.hold_h,
                                segs=SEGS)
            base_rows.append(row)
    E.to_csv(out / "experiments.csv", index=False)
    pool.head(50).to_csv(out / "ranked_top50.csv", index=False)
    pd.DataFrame(base_rows).to_csv(out / "baseline_every_bar.csv", index=False)
    res = {"label": label, "tf": tf, "bars": len(f), "first": str(f.index[0]), "last": str(f.index[-1]),
           "segments": {name: [str(f.index[st.cuts[i]]), str(f.index[st.cuts[i + 1] - 1])] for i, name in enumerate(SEGS)},
           "buy_hold_pct": bh, "configs_tested": int(len(E)), "null_best_dev_t": null_best.round(2).tolist(),
           "real_best_stageA_dev_t": round(float(a_best), 2), "real_beats_null_pct": null_pct,
           "cost_per_side_pct": round(st.cost, 4), "min_stop_pct": cfg.get("min_stop_pct", 0.0), "finalists": results, "baseline_every_bar": base_rows,
           "runtime_s": round(time.time() - t0, 1)}
    (out / "result.json").write_text(json.dumps(res, indent=2, default=_json))
    (out / "summary.md").write_text(summary_md(res))
    log(f"  [{label}] done in {time.time() - t0:.0f}s")
    return res


def _json(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return None if not np.isfinite(x) else float(x)
    return str(x)


def finalize(st: Study, r, k: int, out: Path, label: str, null_pct: float) -> dict:
    cfg, f = st.cfg, st.f
    side = 1 if r.side == "LONG" else -1
    flt = tuple(x for x in r.filters.split("+") if x != "-")
    cid = f"{r.side}_{r.family}_{r.filters}_sl{r.sl_atr}_rr{r.rr}_h{r.hold_h}"
    cand = st.cand(r.family, side, r.sl_atr, r.rr, r.hold_h)
    keep = st.keep_mask(cand, side, flt)
    taken, net, R, gR, seg = st.trades(cand, keep)
    full = {name: stats(R[seg == i], net[seg == i], risk=cfg["risk_per_trade"], start=cfg["start_equity"],
                        bars_in_trade=int((cand.exit_bar[taken][seg == i] - cand.sig[taken][seg == i]).sum()),
                        total_bars=st.cuts[i + 1] - st.cuts[i]) for i, name in enumerate(SEGS)}
    for name in SEGS:
        full[name]["gross_exp_R"] = round(float(gR[seg == SEGS.index(name)].mean()), 4) if (seg == SEGS.index(name)).any() else 0
    # cost sensitivity on TEST
    cost_sens = {}
    for m in cfg["cost_multipliers"]:
        _, _, Rm, _, sm = st.trades(cand, keep, cost_mult=m)
        s = stats(Rm[sm == 2])
        cost_sens[str(m)] = {"n": s["n"], "exp_R": s.get("exp_R", 0), "pf": s.get("pf", 0), "sum_R": s.get("sum_R", 0)}
    # parameter stability: same family + filters, every other exit
    neigh = []
    for sl, rr, hh in st.exits():
        rw = st.run_config(r.family, side, sl, rr, hh, flt)
        neigh.append(rw)
    nb = pd.DataFrame(neigh)
    stab = {"exit_variants": len(nb), "dev_positive": float((nb.dev_exp_R > 0).mean()),
            "val_positive": float((nb.val_exp_R > 0).mean()),
            "both_positive": float(((nb.dev_exp_R > 0) & (nb.val_exp_R > 0)).mean())}
    wf = walk_forward(st, r.family, side, flt)
    # trade log
    tl = pd.DataFrame({
        "signal_time": f.index[cand.sig[taken]], "entry_time": f.index[cand.sig[taken] + 1],
        "exit_time": f.index[cand.exit_bar[taken]] + pd.Timedelta(minutes=TF_MIN[st.tf]),
        "side": r.side, "entry": cand.entry[taken], "exit": cand.exit[taken],
        "reason": np.array(["SL", "TP", "TIME"])[cand.reason[taken]], "stop_pct": cand.risk_frac[taken] * 100,
        "gross_R": gR, "net_R": R, "net_ret_pct": net * 100, "segment": np.array(SEGS)[seg]})
    eq, dd = equity_curve(R, cfg["risk_per_trade"], cfg["start_equity"])
    tl["equity"], tl["drawdown_pct"] = eq, dd * 100
    tl.to_csv(out / f"trades_{k}_{r.side}.csv", index=False)
    tl["month"] = pd.to_datetime(tl["entry_time"]).dt.strftime("%Y-%m")
    monthly = tl.groupby("month").agg(n=("net_R", "size"), sum_R=("net_R", "sum"), win=("net_R", lambda x: (x > 0).mean())).round(3)
    monthly.to_csv(out / f"monthly_{k}_{r.side}.csv")
    sig = cand.sig[taken]
    reg = pd.DataFrame({"R": R, "trend": np.where(f["adx"].values[sig] > 25, "trend", "range"),
                        "vol": np.where(f["vol_regime"].values[sig] > 1, "high_vol", "low_vol")})
    regime = {f"{a}/{b}": {"n": int(len(g)), "exp_R": round(float(g.R.mean()), 3)}
              for (a, b), g in reg.groupby(["trend", "vol"])}
    v = cfg["verdict"]
    t = full["test"]
    checks = {
        "test_trades_enough": t["n"] >= cfg["min_trades_test"],
        "test_net_positive": t.get("exp_R", -1) > 0,
        "test_pf_ok": (t.get("pf") or 0) >= v["test_pf_min"],
        "val_net_positive": full["val"].get("exp_R", -1) > 0,
        "test_survives_1.5x_costs": cost_sens.get("1.5", {}).get("exp_R", -1) > 0,
        "walk_forward_ok": wf["oos_sum_R"] > 0 and wf["pos_fold_share"] >= v["wf_pos_folds_min"],
        "neighbours_stable": stab["both_positive"] >= 0.5,
        "beats_null_search": (null_pct if null_pct == null_pct else 0) >= v["null_pct_min"],
    }
    if t["n"] < cfg["min_trades_test"]:
        verdict = "INCONCLUSIVE (too few test trades)"
    elif all(checks.values()):
        verdict = "CANDIDATE (paper trade only)"
    else:
        verdict = "NO EDGE PROVEN"
    return {"id": cid, "side": r.side, "family": r.family, "filters": r.filters, "sl_atr": r.sl_atr, "rr": r.rr,
            "hold_h": r.hold_h, "sel_score": round(float(r.sel_score), 3), "segments": full,
            "test_cost_sensitivity": cost_sens, "param_stability": stab, "walk_forward": wf, "regime": regime,
            "checks": checks, "verdict": verdict, "files": [f"trades_{k}_{r.side}.csv", f"monthly_{k}_{r.side}.csv"]}


def walk_forward(st: Study, fam, side, flt) -> dict:
    """Rolling: on each train window pick the exit (from the grid) with the best t-stat, trade it on the next window."""
    cfg, f = st.cfg, st.f
    per_day = int(1440 / TF_MIN[st.tf])
    tr, te = cfg["wf_train_days"] * per_day, cfg["wf_test_days"] * per_day
    n = len(f)
    folds, start = [], cfg["warmup_bars"]
    packs = []
    for sl, rr, hh in st.exits():
        cand = st.cand(fam, side, sl, rr, hh)
        taken = select(cand, st.keep_mask(cand, side, flt))
        _, R, _ = net_returns(cand, taken, st.cost, st.fund)
        packs.append(((sl, rr, hh), cand.sig[taken], cand.exit_bar[taken], R))
    oos = []
    while start + tr + te <= n:
        a, b, c = start, start + tr, start + tr + te
        best, bk = -99, None
        for key, sg, xb, R in packs:
            m = (sg >= a) & (xb < b)
            if m.sum() >= 15:
                s = stats(R[m])["t_stat"]
                if s > best:
                    best, bk = s, (key, sg, xb, R)
        if bk:
            key, sg, xb, R = bk
            m = (sg >= b) & (xb < c)
            folds.append({"test_from": str(f.index[b]), "chosen": "sl%s_rr%s_h%s" % key, "train_t": round(best, 2),
                          "oos_n": int(m.sum()), "oos_sum_R": round(float(R[m].sum()), 2)})
            oos.extend(R[m].tolist())
        start += te
    pos = [x["oos_sum_R"] > 0 for x in folds if x["oos_n"] > 0]
    return {"folds": folds, "oos_n": len(oos), "oos_sum_R": round(float(np.sum(oos)), 2) if oos else 0.0,
            "oos_exp_R": round(float(np.mean(oos)), 4) if oos else 0.0,
            "pos_fold_share": round(float(np.mean(pos)), 2) if pos else 0.0}


def summary_md(res: dict) -> str:
    L = [f"## {res['label']}", "",
         f"{res['bars']} bars, {res['first'][:16]} to {res['last'][:16]} UTC. Costs {res['cost_per_side_pct']}% per side "
         f"(+funding). {res['configs_tested']} configs searched. Min stop {res.get('min_stop_pct', 0)}%.", "",
         "| segment | from | to | buy & hold |", "|---|---|---|---|"]
    for s, (a, b) in res["segments"].items():
        L.append(f"| {s} | {a[:16]} | {b[:16]} | {res['buy_hold_pct'][s]}% |")
    L += ["", f"Search vs luck: best DEV t-stat (no filters) = {res['real_best_stageA_dev_t']}; it beats "
          f"{100 * (res['real_beats_null_pct'] or 0):.0f}% of {len(res['null_best_dev_t'])} random-entry searches of the same size.", "",
          "| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in res["finalists"]:
        d, v, t = x["segments"]["dev"], x["segments"]["val"], x["segments"]["test"]
        cfgs = f"{x['family']} [{x['filters']}] sl {x['sl_atr']}ATR rr {x['rr']} {x['hold_h']}h"
        L.append(f"| {x['side']} | {cfgs} | {d['n']} / {d.get('exp_R', 0)} | {v['n']} / {v.get('exp_R', 0)} | {t['n']} | "
                 f"{100 * t.get('win_rate', 0):.0f} | {t.get('exp_R', 0)} | {t.get('pf', 0)} | {t.get('sum_R', 0)} | "
                 f"{t.get('max_dd_pct', 0)}% | {t.get('gross_exp_R', 0)} | {x['test_cost_sensitivity']['1.5']['exp_R']} | "
                 f"{x['walk_forward']['oos_sum_R']} ({100 * x['walk_forward']['pos_fold_share']:.0f}%) | **{x['verdict']}** |")
    if res["baseline_every_bar"]:
        L += ["", "Baseline (enter every bar, exit picked on DEV): " + "; ".join(
            f"{b['side']} TEST n={b.get('test_n', 0)} exp R={b.get('test_exp_R', 0)}" for b in res["baseline_every_bar"])]
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------------------------- data stage
def prepare(asset, pair, tf, cfg, args, out: Path, log):
    raw_dir, clean_dir = out / "data" / "raw", out / "data" / "clean"
    derived, raw = False, None
    if args.source == "coindcx":
        try:
            raw, meta = fetch_candles(pair, tf, cfg["days"], log=log)
            save_raw(raw, meta, raw_dir)
            _, chk = clean(raw, tf)
            bad = chk["off_grid_timestamps"] > 0.2 * max(chk["rows_raw"], 1) or chk["missing_pct"] > 5
        except DataError as exc:
            log(f"  direct {tf} fetch failed: {exc}")
            bad = True
        f5 = raw_dir / f"{pair}_5m_raw.csv.gz"
        if bad and tf != "5m" and f5.exists():
            # Same pair, same exchange: aggregate CoinDCX 5m candles into the larger bar. Logged, not silent.
            from .clean import resample
            log(f"  {tf}: direct candles unusable -> built from CoinDCX {pair} 5m candles")
            raw = resample(clean(load_csv(f5), "5m")[0], f"{TF_MIN[tf]}min")
            derived = True
        if raw is None:
            raise DataError(f"{pair} {tf}: no usable candles")
    elif args.source == "csv":
        raw = load_csv(Path(args.csv_dir) / f"{pair}_{tf}_raw.csv.gz")
    else:
        from .synthetic import make
        raw = make(cfg["days"], TF_MIN[tf], seed=hash((asset, tf)) % 1000, start_price=4000 if asset == "PAXG" else 100000)
    df, rep = clean(raw, tf)
    rep["status"], rep["issues"] = quality_verdict(rep, cfg["days"])
    rep["asset"], rep["pair"], rep["source"] = asset, pair, args.source
    rep["derived_from_5m"] = derived
    clean_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(clean_dir / f"{pair}_{tf}_clean.csv.gz")
    return df, rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="intraday_out")
    ap.add_argument("--config")
    ap.add_argument("--source", choices=["coindcx", "csv", "synthetic"], default="coindcx")
    ap.add_argument("--csv-dir")
    ap.add_argument("--assets", nargs="*", default=None, help="labels from config symbols, e.g. BTC PAXG")
    ap.add_argument("--timeframes", nargs="*", default=None)
    ap.add_argument("--days", type=int)
    ap.add_argument("--null-seeds", type=int)
    args = ap.parse_args(argv)
    cfg = C.load(args.config, days=args.days, null_seeds=args.null_seeds)
    if args.timeframes:
        cfg["timeframes"] = args.timeframes
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log = Log(out / "run_log.txt")
    C.save(cfg, out / "config.json")
    assets = args.assets or list(cfg["symbols"])
    quality, results, blockers = [], [], []
    for asset in assets:
        pair = cfg["symbols"][asset]
        if args.source == "coindcx":
            try:
                info = check_instrument(pair, out_dir=out / "data", log=log)
                log(f"{asset}: {pair} listed on CoinDCX futures ({info['n_active_usdt_futures']} active USDT pairs)")
            except DataError as exc:
                log(f"BLOCKER {asset}: {exc}")
                blockers.append(str(exc))
                continue
        for tf in cfg["timeframes"]:
            log(f"{asset} {tf}: data")
            try:
                df, rep = prepare(asset, pair, tf, cfg, args, out, log)
            except DataError as exc:
                log(f"BLOCKER {asset} {tf}: {exc}")
                blockers.append(f"{asset} {tf}: {exc}")
                continue
            quality.append(rep)
            log(f"  quality {rep['status']}: {rep['coverage_days']}d, {rep['rows_clean']} bars, missing {rep['missing_pct']}% {rep['issues']}")
            if rep["status"] == "POOR":
                blockers.append(f"{asset} {tf}: data quality POOR, research skipped ({rep['issues']})")
                continue
            feats = build(df, tf)
            results.append(run_study(feats, tf, cfg, out / asset / tf, log, f"{asset} {tf}"))
    (out / "data_quality.json").write_text(json.dumps(quality, indent=2, default=_json))
    (out / "summary.json").write_text(json.dumps({"blockers": blockers, "results": results}, indent=2, default=_json))
    (out / "summary.md").write_text(overall_md(cfg, args, quality, results, blockers))
    log("ALL DONE")


def overall_md(cfg, args, quality, results, blockers) -> str:
    L = ["# CoinDCX futures intraday research: BTC + PAXG (5m / 15m)", "",
         f"Round: **{cfg.get('round', '')}**. Source: **{args.source}**. Run at {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC. Research only, no orders.", ""]
    if args.source == "synthetic":
        L += ["> SYNTHETIC DATA: this run only checks that the pipeline works. Its numbers mean nothing.", ""]
    if blockers:
        L += ["## Blockers", ""] + [f"- {b}" for b in blockers] + [""]
    L += ["## Data quality", "", "| asset | tf | first | last | days | bars | missing % | dupes | outliers | zero-vol | status |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for q in quality:
        L.append(f"| {q['asset']} | {q['tf']} | {q['first_bar'][:16]} | {q['last_bar'][:16]} | {q['coverage_days']} | "
                 f"{q['rows_clean']} | {q['missing_pct']} | {q['duplicates']} | {q['outlier_bars_robust_z_gt_15']} | "
                 f"{q['zero_volume_bars']} | {q['status']} |")
    L += ["", "## Results (TEST = last 25%, never used for selection)", ""]
    for r in results:
        L.append(summary_md(r))
    L += ["## How to read", "",
          "- R = net profit / planned stop loss. exp R 0.10 = average +0.1 of the risk per trade after costs.",
          "- CANDIDATE needs: >= 30 test trades, test and val positive, PF >= 1.15, still positive at 1.5x costs, "
          "walk-forward positive in >= 50% of folds, neighbouring exits also positive, and the search beating >= 95% of random searches.",
          "- Even a CANDIDATE is only a reason to paper trade. Nothing here promises profit."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
