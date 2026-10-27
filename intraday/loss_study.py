"""Loss analysis for one config: what was different about the losing trades, and does a filter built from that help?

Discipline: winners vs losers are compared on DEV trades only; a filter threshold is picked on DEV, checked on VAL,
and the single chosen filter is evaluated on TEST once. Random 'noise' features go through the same search, so we
can see how much improvement pure luck produces.

python -m intraday.loss_study --raw <PAIR>_1h_raw.csv.gz --tf 1h --out loss_out
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from .clean import clean
from .data import load_csv
from .features import build
from .metrics import stats
from .research import SEGS, Log, Study

BASE = dict(family="candle_momo", side=1, sl=1.5, rr=3.0, hold=48, filters=("adx_trend", "htf1h"))
QS = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)


def extra_features(f: pd.DataFrame) -> pd.DataFrame:
    x = pd.DataFrame(index=f.index)
    c, a = f["close"], f["atr"]
    x["atr_pct"] = f["atrp"] * 100
    x["vol_regime"] = f["vol_regime"]
    x["adx"] = f["adx"]
    x["rsi"] = f["rsi"]
    x["stoch"] = f["stoch"]
    x["rvol"] = f["rvol"]
    x["body"] = f["body"]
    x["upper_wick"] = (f["high"] - f[["open", "close"]].max(axis=1)) / (f["high"] - f["low"]).replace(0, np.nan)
    x["candle_size_atr"] = (f["high"] - f["low"]) / a
    x["dist_ema20_atr"] = (c - f["ema20"]) / a
    x["dist_ema50_atr"] = (c - f["ema50"]) / a
    x["dist_ema200_atr"] = (c - f["ema200"]) / a
    x["ret_4h_pct"] = c.pct_change(4) * 100
    x["ret_24h_pct"] = c.pct_change(24) * 100
    x["ret_72h_pct"] = c.pct_change(72) * 100
    x["dist_high48_atr"] = (f["don_hi48"] - c) / a
    x["bb_width"] = f["bb_width"]
    x["vwap_dev"] = f["vwap_dev"]
    x["htf4h"] = f["htf4h"]
    x["hour_utc"] = f["hour"]
    x["weekday"] = f["dow"]
    x["macd_h_atr"] = f["macd_h"] / a
    x["ema50_slope_atr"] = (f["ema50"] - f["ema50"].shift(12)) / a
    return x


def run_cfg(st: Study, extra_keep=None):
    b = BASE
    cand = st.cand(b["family"], b["side"], b["sl"], b["rr"], b["hold"])
    keep = st.keep_mask(cand, b["side"], b["filters"])
    if extra_keep is not None:
        keep = keep & extra_keep[cand.sig]
    taken, net, R, gR, seg = st.trades(cand, keep)
    return cand, taken, R, seg


def seg_stats(R, seg):
    return {s: stats(R[seg == i]) for i, s in enumerate(SEGS)}


def search(st, X: pd.DataFrame, base_dev_n: int, min_keep: float):
    rows = []
    for col in X.columns:
        v = X[col].to_numpy(float)
        _, taken, R0, seg0 = run_cfg(st)
        cand = st.cand(BASE["family"], BASE["side"], BASE["sl"], BASE["rr"], BASE["hold"])
        dev_vals = v[cand.sig[taken][seg0 == 0]]
        dev_vals = dev_vals[np.isfinite(dev_vals)]
        if len(np.unique(dev_vals)) < 3:
            continue
        for q in QS:
            th = float(np.quantile(dev_vals, q))
            for op in ("<=", ">="):
                mask = (v <= th) if op == "<=" else (v >= th)
                _, _, R, seg = run_cfg(st, mask)
                d = R[seg == 0]
                if len(d) < min_keep * base_dev_n:
                    continue
                s = seg_stats(R, seg)
                rows.append({"feature": col, "rule": f"{col} {op} {th:.4g}", "dev_n": s["dev"]["n"],
                             "dev_exp_R": s["dev"].get("exp_R", 0), "dev_t": s["dev"].get("t_stat", 0),
                             "val_n": s["val"]["n"], "val_exp_R": s["val"].get("exp_R", 0),
                             "val_t": s["val"].get("t_stat", 0), "_s": s})
    return rows


def compare(trades: pd.DataFrame, X: pd.DataFrame) -> pd.DataFrame:
    d = trades[trades.segment == "dev"]
    xs = X.loc[pd.to_datetime(d.signal_time)]
    win = d.net_R.values > 0
    out = []
    for col in X.columns:
        a, b = xs[col].values[win], xs[col].values[~win]
        out.append({"feature": col, "winners_median": round(float(np.nanmedian(a)), 4),
                    "losers_median": round(float(np.nanmedian(b)), 4),
                    "gap_in_sd": round(float((np.nanmedian(a) - np.nanmedian(b)) / (np.nanstd(xs[col].values) or 1)), 3)})
    return pd.DataFrame(out).sort_values("gap_in_sd", key=abs, ascending=False)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--out", default="loss_out")
    ap.add_argument("--min-keep", type=float, default=0.6, help="filter must keep this share of DEV trades")
    ap.add_argument("--noise", type=int, default=30)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = Log(out / "run_log.txt")
    cfg = C.for_tf(C.load(), a.tf)
    df, _ = clean(load_csv(a.raw), a.tf)
    f = build(df, a.tf)
    st = Study(f, a.tf, cfg, log)
    X = extra_features(f)
    cand, taken, R0, seg0 = run_cfg(st)
    base = seg_stats(R0, seg0)
    log("BASE", {k: (v["n"], v.get("exp_R"), v.get("pf")) for k, v in base.items()})
    tl = pd.DataFrame({"signal_time": f.index[cand.sig[taken]], "net_R": R0, "segment": np.array(SEGS)[seg0],
                       "reason": np.array(["SL", "TP", "TIME"])[cand.reason[taken]]})
    tl = pd.concat([tl, X.loc[tl.signal_time].reset_index(drop=True)], axis=1)
    tl.to_csv(out / "trades_with_features.csv", index=False)
    cmp_ = compare(tl, X)
    cmp_.to_csv(out / "winners_vs_losers_dev.csv", index=False)
    loss_by = {
        "exit_reason_dev": tl[tl.segment == "dev"].groupby("reason").net_R.agg(["size", "sum"]).round(2).to_dict(),
        "by_hour_ist_block_dev": tl[tl.segment == "dev"].assign(
            blk=((tl.hour_utc + 5.5) % 24 // 6).map({0: "00-06", 1: "06-12", 2: "12-18", 3: "18-24"})
        ).groupby("blk").net_R.agg(["size", "mean"]).round(3).to_dict(),
    }
    base_dev_n = base["dev"]["n"]
    rows = search(st, X, base_dev_n, a.min_keep)
    rng = np.random.default_rng(11)
    noise = pd.DataFrame({f"noise{i}": rng.normal(size=len(f)) for i in range(a.noise)}, index=f.index)
    nrows = search(st, noise, base_dev_n, a.min_keep)
    # choose: best min(dev t, val t) with val trades >= 15; then TEST once
    pick = None
    for r in rows:
        r["score"] = min(r["dev_t"], r["val_t"]) if r["val_n"] >= 15 else -99
    rows.sort(key=lambda r: -r["score"])
    if rows and rows[0]["score"] > -99:
        pick = rows[0]
    noise_best = {}
    for r in nrows:
        r["score"] = min(r["dev_t"], r["val_t"]) if r["val_n"] >= 15 else -99
        noise_best[r["feature"]] = max(noise_best.get(r["feature"], -99), r["score"])
    nb = np.array(list(noise_best.values()))
    tab = pd.DataFrame([{k: v for k, v in r.items() if k != "_s"} for r in rows])
    tab.to_csv(out / "filter_search.csv", index=False)
    res = {"base": {k: {kk: v.get(kk) for kk in ("n", "win_rate", "exp_R", "pf", "sum_R", "max_dd_pct")} for k, v in base.items()},
           "losses": loss_by, "base_score": min(base["dev"]["t_stat"], base["val"]["t_stat"]),
           "noise_best_scores": sorted(np.round(nb, 2).tolist())}
    if pick:
        res["pick"] = {"rule": pick["rule"], "score": round(pick["score"], 3),
                       "beats_noise_pct": float((nb < pick["score"]).mean()),
                       **{s: {kk: pick["_s"][s].get(kk) for kk in ("n", "win_rate", "exp_R", "pf", "sum_R", "max_dd_pct")}
                          for s in SEGS}}
        res["top10_dev_val"] = [{k: r[k] for k in ("rule", "dev_n", "dev_exp_R", "val_n", "val_exp_R", "score")}
                                for r in rows[:10]]
    (out / "result.json").write_text(json.dumps(res, indent=2, default=str))
    log(json.dumps(res, indent=1, default=str))
    log("\nWINNERS vs LOSERS (DEV)\n" + cmp_.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
