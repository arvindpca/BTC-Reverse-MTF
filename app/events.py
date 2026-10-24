"""Movement-first study: what did the indicators look like BEFORE moves that paid?

For every bar of a decision timeframe (5m / 15m / 1h / 4h) we ask, separately for LONG and SHORT:
"if I had entered at this bar's close with stop = 1.5 ATR and target = 2 x risk, would it have paid
after costs?"  (triple barrier: stop / target / 48-bar time limit, stop first if both hit in one bar).
Then, for every indicator state known at that close (trend, RSI, breakout, volatility, volume spike,
distance from EMA, session, ...) and every PAIR of states, we replay the trades that state would have
produced (one trade at a time, no overlap) and keep it as a "clue" only if it was positive after costs on
BOTH assets and in BOTH the train part and the untouched test part.  The same scan on random-walk data
tells how many clues pass by pure luck - a real finding must beat that number.

    python -m app.events --assets BTCUSDT PAXGUSDT --days 180 --warmup 60 --null-trials 3
"""
from __future__ import annotations

import argparse
import itertools
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .data import get_1m
from .mtf import atr, efficiency_ratio, ema, last_closed_pos, normalize_1m, resample, rsi, take
from .synthetic import make_random_walk, make_synthetic

TFS = {"5m": 5, "15m": 15, "1h": 60, "4h": 240}
HORIZON = {"5m": 48, "15m": 48, "1h": 48, "4h": 30}  # bars until the time-limit exit
COST_PCT = 2 * (0.06 + 0.02)                          # round trip, % of notional
STOP_ATR, RR = 1.5, 2.0
PASS = dict(train_n=20, test_n=12)                    # min trades per part, per asset


# ----------------------------------------------------------------------------- features
@dataclass
class TFData:
    name: str
    index: pd.DatetimeIndex
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    atr: np.ndarray
    feats: dict          # name -> (int8 codes, labels); -1 = unknown
    trend4: np.ndarray   # +1/-1/nan  (4h EMA20 vs EMA50)
    trend30: np.ndarray  # +1/-1/nan  (daily close vs 30 days earlier)

    def directional(self, d: int) -> dict:
        """Add 'with / against the trend' features for a trade in direction d (+1 long, -1 short)."""
        out = dict(self.feats)
        for key, tr in (("align4h", self.trend4), ("align30d", self.trend30)):
            codes = np.full(len(tr), -1, dtype=np.int8)
            ok = np.isfinite(tr)
            codes[ok & (np.sign(tr) == d)] = 0
            codes[ok & (np.sign(tr) != d)] = 1
            out[key] = (codes, ["with", "against"])
        return out


def _cat(x: np.ndarray, edges: list[float], labels: list[str]) -> tuple[np.ndarray, list[str]]:
    codes = np.digitize(np.nan_to_num(x, nan=0.0), edges).astype(np.int8)
    codes[~np.isfinite(x)] = -1
    return codes, labels


def build_tf(d1m: pd.DataFrame, name: str, minutes: int) -> TFData:
    r = resample(d1m, minutes)
    o, h, l, c, v = (r[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close", "volume"))
    a = atr(h, l, c, 14)
    a[:30] = np.nan
    rs = rsi(c, 14)
    rs[:30] = np.nan
    e20 = ema(c, 20)
    hi = pd.Series(h).shift(1).rolling(20).max().to_numpy()
    lo = pd.Series(l).shift(1).rolling(20).min().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        brk = np.where(c > hi, 0, np.where(c < lo, 1, 2)).astype(np.int8)
        brk[~np.isfinite(hi)] = -1
        dist = (c - e20) / a
        atrp = pd.Series(a / c)
        q33 = atrp.shift(1).rolling(720, min_periods=100).quantile(0.33).to_numpy()
        q66 = atrp.shift(1).rolling(720, min_periods=100).quantile(0.66).to_numpy()
        volc = np.where(atrp.to_numpy() < q33, 0, np.where(atrp.to_numpy() > q66, 2, 1)).astype(np.int8)
        volc[~(np.isfinite(q33) & np.isfinite(atrp.to_numpy()))] = -1
        vavg = pd.Series(v).shift(1).rolling(20).mean().to_numpy()
        spike = np.where(np.isfinite(vavg) & (vavg > 0), (v > 2 * vavg).astype(np.int8), -1).astype(np.int8)
    hour = r.index.hour.to_numpy()
    feats = {
        "rsi": _cat(rs, [30, 45, 55, 70], ["<30", "30-45", "45-55", "55-70", ">70"]),
        "break20": (brk, ["up", "down", "none"]),
        "volatility": (volc, ["low", "mid", "high"]),
        "vol_spike": (spike, ["no", "yes"]),
        "dist_ema20": _cat(dist, [-2, -0.5, 0.5, 2], ["<-2", "-2..-0.5", "-0.5..0.5", "0.5..2", ">2"]),
        "session": (np.digitize(hour, [8, 14, 22]).astype(np.int8), ["asia", "europe", "us", "late"]),
        "day": ((r.index.dayofweek.to_numpy() >= 5).astype(np.int8), ["weekday", "weekend"]),
    }
    # higher-timeframe context, aligned to bars that are fully CLOSED when this bar closes
    r4, rd = resample(d1m, 240), resample(d1m, 1440)
    t4 = np.where(ema(r4["close"], 20) > ema(r4["close"], 50), 1.0, -1.0)
    t4[:60] = np.nan
    er4 = efficiency_ratio(r4["close"], 20)
    cd = rd["close"].to_numpy(dtype=float)
    t30 = np.full(len(cd), np.nan)
    if len(cd) > 30:
        t30[30:] = np.sign(cd[30:] - cd[:-30])
    p4 = last_closed_pos(r.index, r4.index, 240, minutes)
    pdy = last_closed_pos(r.index, rd.index, 1440, minutes)
    feats["er4h"] = _cat(take(er4, p4), [0.3, 0.5], ["range", "mid", "trend"])
    return TFData(name, r.index, o, h, l, c, a, feats, take(t4, p4), take(t30, pdy))


# ----------------------------------------------------------------------------- labeling
def label(tf: TFData, side: int, horizon: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Net R, exit index and cost R for a trade entered at every bar's close (NaN where undefined)."""
    n = len(tf.c)
    R = np.full(n, np.nan)
    C = np.full(n, np.nan)
    ex = np.full(n, -1, dtype=np.int64)
    hl, ll, cl, al = tf.h.tolist(), tf.l.tolist(), tf.c.tolist(), tf.atr.tolist()
    for t in range(n - horizon):
        at = al[t]
        if not (at == at) or at <= 0:
            continue
        entry, risk = cl[t], STOP_ATR * at
        stop, tp = entry - side * risk, entry + side * RR * risk
        res = None
        for k in range(t + 1, t + horizon + 1):
            if side > 0:
                if ll[k] <= stop:
                    res = (-1.0, k)
                    break
                if hl[k] >= tp:
                    res = (RR, k)
                    break
            else:
                if hl[k] >= stop:
                    res = (-1.0, k)
                    break
                if ll[k] <= tp:
                    res = (RR, k)
                    break
        if res is None:
            res = (side * (cl[t + horizon] - entry) / risk, t + horizon)
        cost_r = COST_PCT / (risk / entry * 100.0)
        R[t], C[t], ex[t] = res[0] - cost_r, cost_r, res[1]
    return R, ex, C


def replay(idx: np.ndarray, ex: np.ndarray) -> list[int]:
    """One trade at a time: take a signal only after the previous trade has exited."""
    taken, last = [], -1
    for t in idx.tolist():
        if t > last:
            taken.append(t)
            last = int(ex[t])
    return taken


def stats(tr: list[int], R: np.ndarray, C: np.ndarray) -> dict:
    n = len(tr)
    if n == 0:
        return dict(n=0, win=0.0, avg=0.0, cost=0.0, t=0.0)
    x = R[tr]
    sd = x.std(ddof=1) if n > 1 else 0.0
    return dict(n=n, win=float((x > 0).mean()), avg=float(x.mean()), cost=float(C[tr].mean()),
                t=float(x.mean() / (sd / np.sqrt(n))) if sd > 0 else 0.0)


# ----------------------------------------------------------------------------- scan
def scan_asset(name: str, d1m: pd.DataFrame, warmup_days: int, split: float = 0.6, tfs=None) -> pd.DataFrame:
    d = normalize_1m(d1m)
    rows = []
    for tfname, minutes in (tfs or TFS).items():
        tf = build_tf(d, tfname, minutes)
        n = len(tf.c)
        start = int(tf.index.searchsorted(d.index[0] + pd.Timedelta(days=warmup_days)))
        cut = start + int((n - start) * split)
        for dirn, dname in ((1, "LONG"), (-1, "SHORT")):
            R, ex, C = label(tf, dirn, HORIZON[tfname])
            valid = np.isfinite(R)
            singles = []
            for fname, (codes, labs) in tf.directional(dirn).items():
                for i, lab in enumerate(labs):
                    m = (codes == i) & valid
                    if m[start:].sum() >= 25:
                        singles.append((fname, f"{fname}={lab}", m))
            entries = [("ALL", 0, valid)] + [(k, 1, m) for _, k, m in singles]
            for (f1, k1, m1), (f2, k2, m2) in itertools.combinations(singles, 2):
                if f1 != f2:
                    m = m1 & m2
                    if m[start:].sum() >= 25:
                        entries.append((f"{k1} & {k2}", 2, m))
            for key, nf, m in entries:
                tr = replay(np.flatnonzero(m[start:cut]) + start, ex)
                te = replay(np.flatnonzero(m[cut:]) + cut, ex)
                rows.append({"asset": name, "tf": tfname, "dir": dname, "key": key, "nfeat": nf,
                             **{f"train_{k}": v for k, v in stats(tr, R, C).items()},
                             **{f"test_{k}": v for k, v in stats(te, R, C).items()}})
    return pd.DataFrame(rows)


def combine(frames: list[pd.DataFrame]) -> pd.DataFrame:
    keys = ["tf", "dir", "key", "nfeat"]
    out = None
    for f in frames:
        a = f.asset.iloc[0]
        g = f.drop(columns="asset").rename(columns={c: f"{a}:{c}" for c in f.columns if c.startswith(("train_", "test_"))})
        out = g if out is None else out.merge(g, on=keys, how="inner")
    return out


def passes(c: pd.DataFrame, assets: list[str]) -> pd.Series:
    ok = pd.Series(True, index=c.index)
    for a in assets:
        ok &= ((c[f"{a}:train_n"] >= PASS["train_n"]) & (c[f"{a}:test_n"] >= PASS["test_n"])
               & (c[f"{a}:train_avg"] > 0) & (c[f"{a}:test_avg"] > 0))
    return ok


def null_passes(trials: int, days: int, warmup: int, tfs=None) -> pd.DataFrame:
    """Average number of clues that pass the SAME filter on random-walk data, per timeframe and clue size."""
    res = []
    for t in range(trials):
        n = (days + warmup) * 1440
        fr = [scan_asset(f"RW{k}", make_random_walk(n, 1000 * t + k), warmup, tfs=tfs) for k in range(2)]
        c = combine(fr)
        c = c[passes(c, ["RW0", "RW1"])]
        res.append(c.groupby(["tf", "nfeat"]).size().rename(t))
    return pd.concat(res, axis=1).fillna(0).mean(axis=1).rename("expected").reset_index() if res else pd.DataFrame()


# ----------------------------------------------------------------------------- report
def _cell(c, a, part):
    return f"{int(c[f'{a}:{part}_n'])}t {c[f'{a}:{part}_avg']:+.2f}R"


def report(c: pd.DataFrame, assets: list[str], meta: dict, null: pd.DataFrame, out: Path) -> str:
    L = ["# Movement-first study: indicator status before profitable moves", "",
         f"Window {meta['start']} -> {meta['end']} (after {meta['warmup']}d warm-up); train/test split 60/40. "
         f"Trade = stop {STOP_ATR} ATR, target {RR}R, <= horizon bars, costs {COST_PCT:.2f}% round trip. "
         "One trade at a time per condition. R = initial risk.", "",
         "## 1. Which timeframe can even pay for its costs?", "",
         "Entering at EVERY bar (no indicator), average per trade after costs - this is the baseline any clue must beat.", "",
         "| tf | dir | " + " | ".join(f"{a} cost/trade | {a} test net R/trade" for a in assets) + " |",
         "|---|---|" + "---|---|" * len(assets)]
    base = c[c.key == "ALL"]
    for _, r in base.sort_values(["tf", "dir"]).iterrows():
        L.append(f"| {r.tf} | {r['dir']} | " + " | ".join(f"{r[f'{a}:test_cost']:.2f}R | {r[f'{a}:test_avg']:+.2f}R" for a in assets) + " |")
    ok = c[passes(c, assets) & (c.key != "ALL")]
    L += ["", "## 2. Clues that were positive after costs on BOTH assets, in BOTH train and test", ""]
    exp = {(r.tf, int(r.nfeat)): r.expected for r in null.itertuples()} if len(null) else {}
    miss = 0.0 if len(null) else float('nan')  # a (tf, size) absent from the null table passed 0 times
    L += ["| tf | clues passed (1 indicator) | expected by luck | clues passed (2 indicators) | expected by luck |", "|---|---|---|---|---|"]
    for tfn in TFS:
        s = ok[(ok.tf == tfn)]
        L.append(f"| {tfn} | {int((s.nfeat == 1).sum())} | {exp.get((tfn, 1), miss):.1f} | "
                 f"{int((s.nfeat == 2).sum())} | {exp.get((tfn, 2), miss):.1f} |")
    L += ["", "A clue that passes is only interesting if the 'passed' count is clearly ABOVE the 'expected by luck' count.", ""]
    ok = ok.assign(score=ok[[f"{a}:test_avg" for a in assets]].min(axis=1))
    for tfn in TFS:
        s = ok[ok.tf == tfn].sort_values("score", ascending=False).head(8)
        if s.empty:
            continue
        L += [f"### {tfn} - top passing clues (by the weaker asset's test result)", "",
              "| dir | indicator status before entry | " + " | ".join(f"{a} train | {a} test" for a in assets) + " |",
              "|---|---|" + "---|---|" * len(assets)]
        for _, r in s.iterrows():
            L.append(f"| {r['dir']} | {r.key} | " + " | ".join(f"{_cell(r, a, 'train')} | {_cell(r, a, 'test')}" for a in assets) + " |")
        L.append("")
    text = "\n".join(L) + "\n"
    (out / "summary.md").write_text(text)
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", nargs="*", default=["BTCUSDT", "PAXGUSDT"])
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--warmup", type=int, default=60)
    ap.add_argument("--null-trials", type=int, default=3)
    ap.add_argument("--out", default="events_out")
    ap.add_argument("--cache", default="data_cache")
    ap.add_argument("--synthetic", action="store_true", help="fake data smoke test")
    ap.add_argument("--tfs", nargs="*", default=None, help="subset, e.g. 1h 4h")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tfs = {k: TFS[k] for k in a.tfs} if a.tfs else None
    names = ["SYN_A", "SYN_B"] if a.synthetic else a.assets
    frames, start, end = [], None, None
    for k, name in enumerate(names):
        df = make_synthetic(n=(a.days + a.warmup) * 1440, seed=7 + k) if a.synthetic else get_1m(name, a.days + a.warmup, cache_dir=a.cache)
        frames.append(scan_asset(name, df, a.warmup, tfs=tfs))
        start, end = str(df.index[0] + pd.Timedelta(days=a.warmup)), str(df.index[-1])
    c = combine(frames)
    c.to_csv(out / "clues.csv", index=False)
    null = null_passes(a.null_trials, a.days, a.warmup, tfs) if a.null_trials else pd.DataFrame()
    print(report(c, names, dict(start=start, end=end, warmup=a.warmup), null, out))


if __name__ == "__main__":
    main()
