"""Best-trading-time study: does restricting entries to a time window (hours) create an edge?

1. Hour seasonality: average net return of holding 1h from the start of each UTC hour, per segment (dev/val/test).
2. Time-window filter: for every setup x side x exit (no other filters), pick the contiguous entry window
   (4 / 6 / 8 hours, any start) with the best DEV t-stat. Rank on VAL. TEST evaluated once for the top picks.
3. Null control: the same window search on random entries, to see how good the result looks by pure luck.

python -m intraday.time_study --out time_out --csv-dir <dir with <PAIR>_<tf>_raw.csv.gz>
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
from .engine import candidates
from .features import build
from .metrics import stats
from .research import SEGS, Log, Study

IST = 5.5
LENGTHS = (4, 6, 8)


def window_mask(hours: np.ndarray, start: int, length: int) -> np.ndarray:
    return ((hours - start) % 24) < length


def ist_label(start: int, length: int) -> str:
    a = (start + IST) % 24
    b = (start + length + IST) % 24
    fmt = lambda x: f"{int(x):02d}:{int(round((x % 1) * 60)):02d}"
    return f"{fmt(a)}-{fmt(b)} IST"


def seasonality(f: pd.DataFrame, st: Study) -> pd.DataFrame:
    hourly = f["close"].resample("1h").last()
    opn = f["open"].resample("1h").first()
    ret = (hourly / opn - 1) * 100
    seg_of = np.digitize(np.searchsorted(f.index, ret.index), st.cuts[1:3])
    rows = []
    for h in range(24):
        r = {"utc_hour": h, "ist": ist_label(h, 1)}
        for i, s in enumerate(SEGS):
            x = ret[(ret.index.hour == h) & (seg_of == i)].dropna()
            r[f"{s}_mean_pct"] = round(float(x.mean()), 4)
            r[f"{s}_abs_move_pct"] = round(float(x.abs().mean()), 4)
        rows.append(r)
    return pd.DataFrame(rows)


def search(st: Study, fams: dict, label: str) -> list[dict]:
    hours = st.f.index.hour.values
    mdev, mval = st.cfg["min_trades_dev"], st.cfg["min_trades_val"]
    out = []
    for fam, (ml, ms) in fams.items():
        for side, m in ((1, ml), (-1, ms)):
            for sl, rr, hh in st.exits():
                cand = candidates(st.bars, m, side, sl, rr, st.holds[hh], st.cfg["warmup_bars"],
                                  st.cfg.get("min_stop_pct", 0.0))
                if len(cand.sig) == 0:
                    continue
                best = None
                for length in LENGTHS:
                    for start in range(24):
                        keep = window_mask(hours[cand.sig], start, length)
                        _, _, R, _, seg = st.trades(cand, keep)
                        d = R[seg == 0]
                        if len(d) < mdev:
                            continue
                        t = stats(d)["t_stat"]
                        if best is None or t > best[0]:
                            best = (t, start, length, R, seg)
                if best is None:
                    continue
                t, start, length, R, seg = best
                v = R[seg == 1]
                out.append({"family": fam, "side": "LONG" if side > 0 else "SHORT", "sl_atr": sl, "rr": rr,
                            "hold_h": hh, "utc_start": start, "length_h": length, "window_ist": ist_label(start, length),
                            "dev_n": int((seg == 0).sum()), "dev_exp_R": round(float(R[seg == 0].mean()), 4), "dev_t": t,
                            "val_n": int(len(v)), "val_exp_R": round(float(v.mean()), 4) if len(v) else 0.0,
                            "val_t": stats(v)["t_stat"] if len(v) >= 2 else 0.0, "_R": R, "_seg": seg})
    return out


def run(f, tf, cfg, out: Path, log, label):
    out.mkdir(parents=True, exist_ok=True)
    st = Study(f, tf, cfg, log)
    seas = seasonality(f, st)
    seas.to_csv(out / "hour_seasonality.csv", index=False)
    real = {k: v for k, v in st.fams.items() if not k.startswith("BASE")}
    rows = search(st, real, label)
    mval = cfg["min_trades_val"]
    df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])
    df.to_csv(out / "time_window_search.csv", index=False)
    # null: random entries, same number of setups, same window search; best VAL t of the ranked pick
    rng = np.random.default_rng(cfg["seed"] + 2)
    null_val = []
    for rep in range(cfg["null_seeds"]):
        nf = {f"N{j}": (rng.random(len(f)) < 0.02, rng.random(len(f)) < 0.02) for j in range(len(real))}
        nr = [r for r in search(st, nf, "null") if r["val_n"] >= mval]
        null_val.append(max([r["val_t"] for r in nr], default=-99))
    finals = []
    for side in ("LONG", "SHORT"):
        cand = sorted([r for r in rows if r["side"] == side and r["val_n"] >= mval], key=lambda r: -r["val_t"])
        seen = set()
        for r in cand:
            if r["family"] in seen:
                continue
            seen.add(r["family"])
            R, seg = r["_R"], r["_seg"]
            te = stats(R[seg == 2])
            pct = float(np.mean(np.array(null_val) < r["val_t"]))
            ok = te["n"] >= cfg["min_trades_test"] and te.get("exp_R", -1) > 0 and r["val_exp_R"] > 0 \
                and (te.get("pf") or 0) >= cfg["verdict"]["test_pf_min"] and pct >= 0.95
            verdict = "CANDIDATE (paper trade only)" if ok else (
                "INCONCLUSIVE (too few test trades)" if te["n"] < cfg["min_trades_test"] else "NO EDGE PROVEN")
            finals.append({**{k: v for k, v in r.items() if not k.startswith("_")},
                           "test_n": te["n"], "test_win": te.get("win_rate", 0), "test_exp_R": te.get("exp_R", 0),
                           "test_pf": te.get("pf", 0), "test_sum_R": te.get("sum_R", 0),
                           "test_max_dd_pct": te.get("max_dd_pct", 0), "beats_null_pct": round(pct, 2),
                           "verdict": verdict})
            if len(seen) >= 3:
                break
    res = {"label": label, "configs": len(rows), "null_best_val_t": [round(x, 2) for x in null_val],
           "finalists": finals, "segments": {s: [str(f.index[st.cuts[i]])[:16], str(f.index[st.cuts[i + 1] - 1])[:16]]
                                             for i, s in enumerate(SEGS)}}
    (out / "result.json").write_text(json.dumps(res, indent=2, default=str))
    log(f"  [{label}] {len(rows)} setups searched, finalists: " + "; ".join(x["verdict"] for x in finals))
    return res, seas


def md(res, seas) -> str:
    L = [f"## {res['label']}", "", f"Segments: " + ", ".join(f"{k} {a} to {b}" for k, (a, b) in res["segments"].items()), "",
         "| side | setup | best window (chosen on DEV) | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | beats luck | verdict |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in res["finalists"]:
        L.append(f"| {x['side']} | {x['family']} sl {x['sl_atr']}ATR rr {x['rr']} {x['hold_h']}h | {x['window_ist']} | "
                 f"{x['dev_n']} / {x['dev_exp_R']} | {x['val_n']} / {x['val_exp_R']} | {x['test_n']} | "
                 f"{100 * x['test_win']:.0f} | {x['test_exp_R']} | {x['test_pf']} | {x['test_sum_R']} | "
                 f"{100 * x['beats_null_pct']:.0f}% | **{x['verdict']}** |")
    # seasonality: hours whose 1h drift has the same sign in all three segments
    s = seas.copy()
    same = s[(np.sign(s.dev_mean_pct) == np.sign(s.val_mean_pct)) & (np.sign(s.val_mean_pct) == np.sign(s.test_mean_pct))]
    L += ["", "Hours whose average 1h move had the same direction in DEV, VAL and TEST: " +
          (", ".join(f"{r.ist} ({'up' if r.dev_mean_pct > 0 else 'down'}, avg {r.dev_mean_pct:+.3f}/{r.val_mean_pct:+.3f}/{r.test_mean_pct:+.3f}%)"
                     for r in same.itertuples()) or "none"),
          f"Busiest hours (largest average 1h move): " + ", ".join(
              f"{r.ist} {r.dev_abs_move_pct:.2f}%" for r in s.sort_values("dev_abs_move_pct", ascending=False).head(4).itertuples()), ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="time_out")
    ap.add_argument("--csv-dir", required=True)
    ap.add_argument("--null-seeds", type=int, default=10)
    a = ap.parse_args(argv)
    cfg = C.load(null_seeds=a.null_seeds)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = Log(out / "run_log.txt")
    C.save(cfg, out / "config.json")
    parts = ["# Best trading time study: CoinDCX futures BTC + PAXG (5m / 15m)", "",
             "Only one filter: the entry time window. Window chosen on DEV (first 50%), ranked on VAL (next 25%), "
             "TEST (last 25%) checked once. Costs as in the main study (0.079% per side + funding), min stop 0.25%.", ""]
    for asset, pair in cfg["symbols"].items():
        for tf in cfg["timeframes"]:
            df, _ = clean(load_csv(Path(a.csv_dir) / f"{pair}_{tf}_raw.csv.gz"), tf)
            res, seas = run(build(df, tf), tf, cfg, out / asset / tf, log, f"{asset} {tf}")
            parts.append(md(res, seas))
    (out / "summary.md").write_text("\n".join(parts) + "\n")
    log("ALL DONE")


if __name__ == "__main__":
    main()
