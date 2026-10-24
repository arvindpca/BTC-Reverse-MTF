"""Reverse engineering study (1h bars, years of data).

Step 1  HINDSIGHT: find every big swing (zigzag, size in ATRs) = the profit that was available.
Step 2  CLUES   : what did the indicators look like at the start of those swings, compared with ordinary bars (lift)?
Step 3  RULES   : turn every clue (single and pairs) into a causal entry rule, long and short, and backtest it on the
                  FIRST 60% of history only (cost 0.16% round trip, ATR stop, trailing exit, one trade at a time).
Step 4  PROOF   : the best train rules are then run once on the LAST 40% they never saw. A random-walk control shows how
                  many rules 'work' by pure luck with the same procedure.
Research only. Nothing here places orders.
"""
from __future__ import annotations

import argparse
import itertools
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .data import BINANCE_HOSTS, DataError
from .engine import EngineParams, run, summarize
from .mtf import atr, ema, efficiency_ratio, rsi

STOP_ATR = 3.0
SWING_ATR = 8.0
EP = EngineParams(rr=50.0, be_r=None, max_hold=24 * 20, fee_pct=0.06, slip_pct=0.02,
                  min_risk_pct=0.3, max_risk_pct=2.5, reverse=False, trail_r=1.0, trail_start_r=1.5)
MIN_TRAIN_TRADES, TOP_K = 25, 10


# ---------------------------------------------------------------- data
def fetch_klines(symbol: str, interval: str, days: int, step_ms: int, hosts=BINANCE_HOSTS, session=None) -> pd.DataFrame:
    s = session or requests.Session()
    end = int(time.time() * 1000) // step_ms * step_ms
    cur, rows, hi, errs = end - days * 86_400_000, [], 0, []
    while cur < end:
        while True:
            try:
                r = s.get(f"{hosts[hi]}/api/v3/klines", timeout=20,
                          params=dict(symbol=symbol, interval=interval, startTime=cur, endTime=end - 1, limit=1000))
                r.raise_for_status()
                ch = r.json()
                break
            except (requests.RequestException, ValueError) as e:
                errs.append(str(e))
                hi += 1
                if hi >= len(hosts):
                    raise DataError(f"all hosts failed for {symbol}: {errs[-3:]}") from e
        if not ch:
            break
        rows += ch
        nxt = int(ch[-1][0]) + step_ms
        if nxt <= cur:
            break
        cur = nxt
        time.sleep(0.05)
    if not rows:
        raise DataError(f"no candles for {symbol}")
    df = pd.DataFrame(rows).iloc[:, :6]
    df.columns = ["ts", "open", "high", "low", "close", "volume"]
    df.index = pd.to_datetime(df.pop("ts").astype("int64"), unit="ms", utc=True)
    return df.astype(float)[~df.index.duplicated()].sort_index()


def make_null_1h(n: int, seed: int, base: float = 60000.0) -> pd.DataFrame:
    """iid random walk 1h bars - no edge by construction."""
    rng = np.random.default_rng(seed)
    vol = np.repeat(rng.choice([0.003, 0.005, 0.009], size=n // 240 + 1), 240)[:n]
    c = base * np.exp(np.cumsum(rng.normal(0, vol)))
    o = np.concatenate([[base], c[:-1]])
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol * 0.5)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol * 0.5)))
    idx = pd.date_range("2022-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame(dict(open=o, high=h, low=l, close=c, volume=1.0), index=idx)


# ---------------------------------------------------------------- step 1: hindsight swings
def zigzag(high: np.ndarray, low: np.ndarray, atr_pct: np.ndarray, mult: float = SWING_ATR) -> list[tuple[int, int]]:
    """Confirmed pivots as (bar, +1 for a swing HIGH / -1 for a swing LOW). Hindsight only - never used to trade."""
    n, piv = len(high), []
    hi_i = lo_i = 0
    d = 0
    for i in range(1, n):
        if np.isnan(atr_pct[i]):
            continue
        thr = mult * atr_pct[i]
        if high[i] > high[hi_i]:
            hi_i = i
        if low[i] < low[lo_i]:
            lo_i = i
        if d >= 0 and high[hi_i] > 0 and (high[hi_i] - low[i]) / high[hi_i] >= thr and hi_i < i:
            piv.append((hi_i, +1))
            d, lo_i, hi_i = -1, i, i
        elif d <= 0 and low[lo_i] > 0 and (high[i] - low[lo_i]) / low[lo_i] >= thr and lo_i < i:
            piv.append((lo_i, -1))
            d, hi_i, lo_i = +1, i, i
    # keep strictly alternating pivots
    out: list[tuple[int, int]] = []
    for p in piv:
        if out and out[-1][1] == p[1]:
            continue
        out.append(p)
    return out


def swings(df: pd.DataFrame, piv: list[tuple[int, int]]) -> pd.DataFrame:
    rows = []
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    for (a, da), (b, db) in zip(piv[:-1], piv[1:]):
        pa = l[a] if da == -1 else h[a]
        pb = h[b] if db == +1 else l[b]
        rows.append(dict(start=a, end=b, dir=+1 if db == +1 else -1, move_pct=abs(pb - pa) / pa * 100, bars=b - a))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- step 2: clue masks (all causal)
GROUPS = ("rsi", "er", "dist", "trend", "slope", "donch", "vol", "seq")


def clue_masks(df: pd.DataFrame) -> tuple[dict[str, np.ndarray], np.ndarray]:
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a = atr(h, l, c, 14)
    r, er = rsi(c, 14), efficiency_ratio(c, 20)
    e50, e200 = ema(c, 50), ema(c, 200)
    with np.errstate(invalid="ignore", divide="ignore"):
        dist = (c - e50) / a
    s = pd.Series
    hh = s(h).rolling(48).max().shift(1).to_numpy()
    ll = s(l).rolling(48).min().shift(1).to_numpy()
    pos = (c - ll) / (hh - ll)
    apct = s(a / c).rolling(500, min_periods=100).rank(pct=True).to_numpy()
    sl = e200 - np.concatenate([np.full(24, np.nan), e200[:-24]])
    up, dn = c > o, c < o
    up3 = up & np.roll(up, 1) & np.roll(up, 2)
    dn3 = dn & np.roll(dn, 1) & np.roll(dn, 2)
    up3[:3] = dn3[:3] = False
    M = {
        "rsi<30": r < 30, "rsi30-45": (r >= 30) & (r < 45), "rsi45-55": (r >= 45) & (r < 55),
        "rsi55-70": (r >= 55) & (r < 70), "rsi>70": r >= 70,
        "er<.2": er < .2, "er.2-.4": (er >= .2) & (er < .4), "er>.4": er >= .4,
        "dist<-3": dist < -3, "dist-3..-1": (dist >= -3) & (dist < -1), "dist-1..1": (dist >= -1) & (dist < 1),
        "dist1..3": (dist >= 1) & (dist < 3), "dist>3": dist >= 3,
        "ema50>200": e50 > e200, "ema50<200": e50 < e200,
        "slope up": sl > 0, "slope down": sl < 0,
        "breakout up48": c > hh, "breakout dn48": c < ll, "range low<.1": pos < .1, "range high>.9": pos > .9,
        "vol low": apct < .33, "vol high": apct > .66,
        "3 up bars": up3, "3 down bars": dn3,
    }
    for k in M:
        M[k] = np.asarray(M[k], dtype=bool)
    return M, a


_PREFIX = (("rsi", "rsi"), ("er", "er"), ("dist", "dist"), ("ema50", "trend"), ("slope", "slope"),
           ("breakout", "donch"), ("range", "donch"), ("vol", "vol"), ("3 ", "seq"))


def group_of(name: str) -> str:
    for pre, g in _PREFIX:
        if name.startswith(pre):
            return g
    raise KeyError(name)


def lifts(masks: dict[str, np.ndarray], sw: pd.DataFrame, lo: int, hi: int, direction: int) -> pd.DataFrame:
    """P(clue at swing start) / P(clue on any bar). >1 = clue is more common right before such a move."""
    s = sw[(sw["dir"] == direction) & (sw["start"] >= lo) & (sw["start"] < hi)]
    st = s["start"].to_numpy()
    rows = []
    for k, m in masks.items():
        base = m[lo:hi].mean()
        at = m[st].mean() if len(st) else np.nan
        rows.append(dict(clue=k, at_start=at, all_bars=base, lift=at / base if base > 0 else np.nan, n_swings=len(st)))
    return pd.DataFrame(rows).sort_values("lift", ascending=False)


# ---------------------------------------------------------------- step 3: causal rules and backtest
def rule_signal(cond: np.ndarray, side: int, df: pd.DataFrame, a: np.ndarray):
    edge = cond & ~np.concatenate([[False], cond[:-1]])
    c = df["close"].to_numpy(float)
    sd = np.where(edge, side, 0).astype(np.int8)
    stop = np.where(edge, c - side * STOP_ATR * a, np.nan)
    return sd, stop, np.arange(len(c))


def candidates(masks: dict[str, np.ndarray]) -> list[tuple[str, np.ndarray]]:
    out = [(k, m) for k, m in masks.items()]
    for (k1, m1), (k2, m2) in itertools.combinations(list(masks.items()), 2):
        if group_of(k1) != group_of(k2):
            out.append((f"{k1} & {k2}", m1 & m2))
    return out


def backtest(df: pd.DataFrame, cond: np.ndarray, side: int, a: np.ndarray, lo: int, hi: int) -> dict:
    sd, stop, sid = rule_signal(cond, side, df, a)
    tr = run(df["open"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy(), sd, stop, sid, EP, lo, hi)
    return summarize(tr) | dict(trades=tr)


def mine(df: pd.DataFrame, split: float = 0.6, warm: int = 600) -> pd.DataFrame:
    """Rank every rule on TRAIN, then run the top K on TEST once."""
    n = len(df)
    cut = int(n * split)
    masks, a = clue_masks(df)
    rows = []
    for name, m in candidates(masks):
        for side in (1, -1):
            s = backtest(df, m, side, a, warm, cut)
            if s["n"] >= MIN_TRAIN_TRADES and s["net_r"] > 0:
                rows.append(dict(rule=name, side=side, train_n=s["n"], train_net_r=s["net_r"], train_avg_r=s["avg_net_r"],
                                 train_win=s["win_rate"], train_t=s["t_stat"], train_pf=s["pf"]))
    if not rows:
        return pd.DataFrame()
    t = pd.DataFrame(rows).sort_values("train_t", ascending=False).head(TOP_K).reset_index(drop=True)
    cmap = dict(candidates(masks))
    te = []
    for _, r in t.iterrows():
        s = backtest(df, cmap[r["rule"]], int(r["side"]), a, cut, n)
        te.append(dict(test_n=s["n"], test_net_r=s["net_r"], test_avg_r=s["avg_net_r"], test_win=s["win_rate"],
                       test_t=s["t_stat"], test_pf=s["pf"], test_dd_r=s["max_dd_r"]))
    return pd.concat([t, pd.DataFrame(te)], axis=1)


def null_luck(n_bars: int, trials: int, split: float = 0.6) -> list[dict]:
    out = []
    for i in range(trials):
        m = mine(make_null_1h(n_bars, 1000 + i), split)
        if m.empty:
            out.append(dict(top_k=0, test_pos=0, best_test=0.0, mean_test=0.0))
        else:
            out.append(dict(top_k=len(m), test_pos=int((m["test_net_r"] > 0).sum()),
                            best_test=float(m["test_net_r"].max()), mean_test=float(m["test_net_r"].mean())))
    return out


# ---------------------------------------------------------------- report
def pnl_curve(tr, margin=300.0, lev=30) -> tuple[float, float]:
    """Currency P/L with fixed notional margin*lev, stop% from each trade. Returns (total, worst drawdown)."""
    notional = margin * lev
    vals = [t.net_r * abs(t.entry - t.stop) / t.entry * notional for t in tr] if tr else []
    eq = np.cumsum(vals) if vals else np.array([0.0])
    dd = float((np.maximum.accumulate(np.maximum(eq, 0)) - eq).max())
    return float(eq[-1]), dd


def fmt(x, p=2):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{p}f}"


def asset_report(name: str, df: pd.DataFrame, split: float = 0.6) -> tuple[list[str], pd.DataFrame]:
    n = len(df)
    cut = int(n * split)
    masks, a = clue_masks(df)
    piv = zigzag(df["high"].to_numpy(), df["low"].to_numpy(), a / df["close"].to_numpy())
    sw = swings(df, piv)
    yrs = n / (24 * 365)
    L = [f"## {name}", "", f"{n} 1h bars (~{yrs:.1f} years) {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}. "
         f"Train = first {int(split*100)}% (until {df.index[cut]:%Y-%m-%d}), test = the rest.", ""]
    if len(sw):
        L += ["### 1. Movement available in hindsight (swings >= %g ATR)" % SWING_ATR, "",
              f"- swings: {len(sw)} ({len(sw)/yrs:.1f} per year), median move {sw['move_pct'].median():.1f}%, "
              f"median length {sw['bars'].median():.0f} hours",
              f"- hindsight profit if every swing were caught perfectly: {sw['move_pct'].sum()/yrs:.0f}% of price per year "
              "(an upper bound nobody can reach)", ""]
    for d, nm in ((1, "UP swings (what looked like this before a rally)"), (-1, "DOWN swings")):
        lf = lifts(masks, sw, 600, cut, d) if len(sw) else pd.DataFrame()
        if lf.empty:
            continue
        L += [f"### 2. Clues at the start of {nm} - train period", "", "| clue | at swing start | on all bars | lift |", "|---|---|---|---|"]
        for _, r in pd.concat([lf.head(5), lf.tail(3)]).iterrows():
            L.append(f"| {r['clue']} | {r['at_start']*100:.0f}% | {r['all_bars']*100:.0f}% | {fmt(r['lift'])}x |")
        L.append("")
    m = mine(df, split)
    L += ["### 3-4. Rules built from clues: ranked on train, then run ONCE on test", ""]
    if m.empty:
        L += ["No rule had >= %d trades and positive net result on train." % MIN_TRAIN_TRADES, ""]
    else:
        L += ["| rule | side | train n | train net R | train t | test n | test net R | test win% | test PF | test max DD R |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in m.iterrows():
            L.append(f"| {r['rule']} | {'long' if r['side']>0 else 'short'} | {r['train_n']:.0f} | {r['train_net_r']:.1f} | "
                     f"{r['train_t']:.1f} | {r['test_n']:.0f} | {r['test_net_r']:.1f} | {r['test_win']*100:.0f} | "
                     f"{fmt(r['test_pf'])} | {r['test_dd_r']:.1f} |")
        L += ["", f"Top-{len(m)} train rules positive on test: {(m['test_net_r']>0).sum()} of {len(m)}.", ""]
        best = m.iloc[0]
        cmap = dict(candidates(masks))
        s = backtest(df, cmap[best["rule"]], int(best["side"]), a, cut, n)
        tot, dd = pnl_curve(s["trades"])
        L += [f"Best-by-train rule `{best['rule']}` ({'long' if best['side']>0 else 'short'}) on the unseen test part, "
              f"margin 300 x 30x (notional 9000), costs included: **{tot:+.0f}** total, worst drawdown {dd:.0f}, "
              f"{s['n']} trades.", ""]
    return L, m


def verdict(results: dict[str, pd.DataFrame], null: list[dict]) -> list[str]:
    L = ["## Verdict", ""]
    ok = []
    for nm, m in results.items():
        if m.empty:
            continue
        good = m[(m["test_net_r"] > 0) & (m["test_n"] >= 12) & (m["test_t"] > 1.0)]
        ok.append(set(good["rule"] + "|" + good["side"].astype(str)))
        L.append(f"- {nm}: {len(good)} of {len(m)} top rules held up on test (net > 0, t > 1, >= 12 trades).")
    if null:
        pos = np.mean([x["test_pos"] / x["top_k"] for x in null if x["top_k"]]) if any(x["top_k"] for x in null) else 0.0
        L.append(f"- Luck baseline (random walk, same procedure, {len(null)} trials): on average {pos*100:.0f}% of the top rules "
                 f"were positive on test; best single test result {max(x['best_test'] for x in null):.1f} R.")
    both = set.intersection(*ok) if len(ok) >= 2 and all(ok) else set()
    L += ["", ("- Rules good on BOTH assets (the only kind worth trusting): " + ", ".join(sorted(both))) if both else
          "- No rule held up on both assets. Treat every single-asset result above as unconfirmed.", ""]
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", nargs="*", default=["BTCUSDT", "PAXGUSDT"])
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--null-trials", type=int, default=3)
    ap.add_argument("--out", default="reverse_out")
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = ["# Reverse engineering study (1h bars)", "",
         f"READ THIS FIRST: clues measured at a swing start look strong even on pure random data (a swing low is by definition "
         "after a drop, so 'oversold' always shows a big lift). Only the test table (rules chosen on train, run once on unseen "
         "data) and the luck baseline say anything about real edge.", "",
         f"Costs 0.16% round trip. ATR stop {STOP_ATR:g}x, trailing exit, one trade at a time. Research only, no orders.", ""]
    res, nbars = {}, 0
    for sym in a.assets:
        df = make_null_1h(24 * 400, 5) if a.synthetic else fetch_klines(sym, "1h", a.days, 3_600_000)
        nbars = max(nbars, len(df))
        lines, m = asset_report(sym, df)
        L += lines
        res[sym] = m
        m.to_csv(out / f"{sym}_rules.csv", index=False)
    null = null_luck(nbars, a.null_trials)
    L += verdict(res, null)
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
