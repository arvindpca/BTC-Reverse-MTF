"""Deep analysis of candidate v2 (PAXG): what do winning and losing trades look like, and which filters really help?

Filters are validated TWICE: thresholds learned on the first 60% and tested on the last 40%, and the other way round
(learned on the last 60%, tested on the first 40%). A filter is only accepted if it helps in BOTH directions.
Research only; no orders.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import reverse_eng as re_
from .engine import summarize
from .final import equity, streak
from .mtf import atr
from .paper_run import STOP_ATR, v2_condition
from .refine import trades_of
from .reverse_eng import clue_masks, fetch_klines, make_null_1h

WARM = 700


def feature_arrays(df: pd.DataFrame) -> dict[str, np.ndarray]:
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    a = atr(h, l, c, 14)
    s = pd.Series
    from .mtf import efficiency_ratio, ema, rsi
    e50, e200 = ema(c, 50), ema(c, 200)
    with np.errstate(invalid="ignore", divide="ignore"):
        F = {
            "er20": efficiency_ratio(c, 20),
            "rsi14": rsi(c, 14),
            "dist_ema50_atr": (c - e50) / a,
            "dist_ema200_pct": (c - e200) / e200 * 100,
            "atr_pct": a / c * 100,
            "atr_rank500": s(a / c).rolling(500, min_periods=100).rank(pct=True).to_numpy(),
            "run3_atr": (c - np.roll(o, 2)) / a,                       # last 3 candles, open of first to close of last
            "ret24h_pct": (c / np.roll(c, 24) - 1) * 100,
            "ret72h_pct": (c / np.roll(c, 72) - 1) * 100,
            "from_7d_high_pct": (c / s(h).rolling(168).max().to_numpy() - 1) * 100,
            "vol_ratio20": v / s(v).rolling(20).mean().to_numpy(),
            "last_body_atr": np.abs(c - o) / a,
            "last_close_pos": (c - l) / np.where(h > l, h - l, np.nan),   # 1 = closed at the high of the candle
            "er20_prev": np.roll(efficiency_ratio(c, 20), 1),
            "hour_utc": df.index.hour.to_numpy().astype(float),
        }
    for k in ("run3_atr", "ret24h_pct", "ret72h_pct", "er20_prev"):
        F[k][:80] = np.nan
    return F


def life(df, t):
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    risk = t.entry - t.stop
    seg_h, seg_l = h[t.entry_idx + 1:t.exit_idx + 1], l[t.entry_idx + 1:t.exit_idx + 1]
    if len(seg_h) == 0:
        return 0.0, 0.0
    return (seg_h.max() - t.entry) / risk, (t.entry - seg_l.min()) / risk


def base_trades(df, cond, a, lo, hi):
    return trades_of(df, cond, a, lo, hi, None, STOP_ATR)


def trade_table(df, tr, F) -> pd.DataFrame:
    rows = []
    for t in tr:
        mfe, mae = life(df, t)
        r = dict(idx=t.entry_idx, time=df.index[t.entry_idx], net_r=t.net_r, reason=t.reason, hold=t.exit_idx - t.entry_idx,
                 mfe=mfe, mae=mae, stop_pct=t.risk_pct)
        r.update({k: v[t.entry_idx] for k, v in F.items()})
        rows.append(r)
    return pd.DataFrame(rows)


def distribution(tt: pd.DataFrame) -> list[str]:
    r = tt["net_r"]
    bins = [(-9, -1.0, "worse than -1R"), (-1.0, 0, "-1R to 0"), (0, 1, "0 to +1R"), (1, 2, "+1R to +2R"), (2, 4, "+2R to +4R"), (4, 99, "above +4R")]
    L = ["| result of a trade | trades | share | total R |", "|---|---|---|---|"]
    for lo, hi, nm in bins:
        m = (r >= lo) & (r < hi)
        L.append(f"| {nm} | {int(m.sum())} | {m.mean()*100:.0f}% | {r[m].sum():+.1f} |")
    srt = r.sort_values(ascending=False)
    k = max(1, len(r) // 10)
    L += ["", f"- Top 10% of trades ({k}) make {srt.head(k).sum():+.1f} R of the total {r.sum():+.1f} R. Without them: {r.sum()-srt.head(k).sum():+.1f} R.",
          f"- Winners: avg {r[r>0].mean():+.2f} R, avg hold {tt[r>0]['hold'].mean():.0f} h. Losers: avg {r[r<=0].mean():+.2f} R, avg hold {tt[r<=0]['hold'].mean():.0f} h."]
    ex = tt.groupby("reason")["net_r"].agg(["count", "mean", "sum"])
    L.append("- Exit reasons: " + "; ".join(f"{k} {int(v['count'])} trades avg {v['mean']:+.2f} R" for k, v in ex.iterrows()))
    los = tt[tt["net_r"] <= 0]
    win = tt[tt["net_r"] > 0]
    L += [f"- Losers: {(los['mfe']>=1).mean()*100:.0f}% had been at least +1R in profit before reversing, {(los['mfe']>=0.5).mean()*100:.0f}% at least +0.5R.",
          f"- Winners: median worst dip before winning {win['mae'].median():.2f} R; {(win['mae']>0.5).mean()*100:.0f}% dipped more than half a stop first.", ""]
    return L


def make_variants(F, thr_src: pd.DataFrame, feats: list[str]):
    """For every feature: 'high' (value >= median of the source trades) and 'low' (< median)."""
    out = []
    for f in feats:
        med = float(np.nanmedian(thr_src[f]))
        out.append((f"{f} >= {med:.3g}", F[f] >= med))
        out.append((f"{f} < {med:.3g}", F[f] < med))
    return out


def score(df, cond, a, lo, hi):
    tr = base_trades(df, cond, a, lo, hi)
    s = summarize(tr)
    e, dd = equity(tr)
    return s, e, dd, tr


def validate(df, F, base_cond, a, learn, test, feats):
    """Thresholds from trades in `learn`; returns rows with learn/test stats for base and each filter."""
    lt = base_trades(df, base_cond, a, *learn)
    tt = trade_table(df, lt, F)
    rows = []
    sb_l, sb_t = score(df, base_cond, a, *learn)[0], score(df, base_cond, a, *test)[0]
    for name, m in make_variants(F, tt, feats):
        c = base_cond & np.nan_to_num(m, nan=0).astype(bool)
        sl, el, dl, _ = score(df, c, a, *learn)
        st, et, dt, _ = score(df, c, a, *test)
        rows.append(dict(filter=name, l_n=sl["n"], l_pf=sl["pf"], l_net=sl["net_r"], t_n=st["n"], t_pf=st["pf"], t_net=st["net_r"],
                         t_eq=et, t_dd=dt, ok=(sl["n"] >= 25 and st["n"] >= 20 and sl["pf"] > sb_l["pf"] and st["pf"] > sb_t["pf"]
                                               and sl["net_r"] > 0 and st["net_r"] > 0)))
    return pd.DataFrame(rows), sb_l, sb_t


def report(df: pd.DataFrame, label: str) -> list[str]:
    n = len(df)
    masks, a = clue_masks(df)
    cond = v2_condition(df, masks)
    F = feature_arrays(df)
    tr = base_trades(df, cond, a, WARM, n)
    tt = trade_table(df, tr, F)
    s = summarize(tr)
    e, dd = equity(tr)
    L = [f"# {label}: deep analysis of candidate v2", "",
         f"{n} 1h bars, {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}. v2 over the whole history: {s['n']} trades, win {s['win_rate']*100:.0f}%, "
         f"net {s['net_r']:+.1f} R, PF {re_.fmt(s['pf'])}, 300 -> {e:.0f} at 2% risk, max drawdown {dd*100:.0f}%, longest loss streak {streak(tr)}.", "",
         "## 1. How the trades behave", ""] + distribution(tt)

    feats = [k for k in F if k not in ("hour_utc",)]
    L += ["## 2. Winners vs losers: what differs at entry? (whole history, v2 trades)", "",
          "| feature | avg for winners | avg for losers | R/trade when feature is above its median | below its median |", "|---|---|---|---|---|"]
    w, lo_ = tt[tt["net_r"] > 0], tt[tt["net_r"] <= 0]
    for f in feats:
        med = tt[f].median()
        L.append(f"| {f} | {w[f].mean():.3g} | {lo_[f].mean():.3g} | {tt[tt[f]>=med]['net_r'].mean():+.2f} (n={int((tt[f]>=med).sum())}) | "
                 f"{tt[tt[f]<med]['net_r'].mean():+.2f} (n={int((tt[f]<med).sum())}) |")
    L.append("")

    cut = int(n * 0.6)
    cut2 = int(n * 0.4)
    dirA = validate(df, F, cond, a, (WARM, cut), (cut, n), feats)
    dirB = validate(df, F, cond, a, (cut2, n), (WARM, cut2), feats)
    A, bAl, bAt = dirA
    B, bBl, bBt = dirB
    L += ["## 3. Filters, validated both ways", "",
          f"{len(A)} single filters tried in each direction. Direction A: learn on the first 60%, test on the last 40%. "
          f"Direction B: learn on the last 60%, test on the first 40%. Base v2 PF: A learn {re_.fmt(bAl['pf'])} / test {re_.fmt(bAt['pf'])}; "
          f"B learn {re_.fmt(bBl['pf'])} / test {re_.fmt(bBt['pf'])}.", "",
          "A filter counts only if it beats the base PF on both learn and test parts AND stays profitable, in BOTH directions.", ""]
    keyed = {}
    for d, T in (("A", A), ("B", B)):
        T = T.copy()
        T["feat"] = T["filter"].str.split(" ").str[0]
        T["side"] = np.where(T["filter"].str.contains(" >= "), "high", "low")
        keyed[d] = T
    both = []
    for _, ra in keyed["A"].iterrows():
        rb = keyed["B"][(keyed["B"]["feat"] == ra["feat"]) & (keyed["B"]["side"] == ra["side"])]
        if ra["ok"] and len(rb) and bool(rb.iloc[0]["ok"]):
            both.append((ra, rb.iloc[0]))
    ok_a, ok_b = int(A["ok"].sum()), int(B["ok"].sum())
    L.append(f"Passing in A: {ok_a}. Passing in B: {ok_b}. Passing in BOTH: {len(both)}. "
             f"(With {len(A)} tries per direction, a few passes by luck alone are expected.)")
    L.append("")
    if both:
        L += ["| filter (side) | A: test n | A: test PF | A: test net R | B: test n | B: test PF | B: test net R |", "|---|---|---|---|---|---|---|"]
        for ra, rb in both:
            L.append(f"| {ra['feat']} {ra['side']} | {ra['t_n']} | {re_.fmt(ra['t_pf'])} | {ra['t_net']:+.1f} | {rb['t_n']} | {re_.fmt(rb['t_pf'])} | {rb['t_net']:+.1f} |")
        L.append("")
    else:
        L += ["No single filter passed in both directions, so v2 stays as it is.", ""]

    # ---- 4. combined accepted filters on whole history (thresholds from whole-history trade medians)
    final_note = []
    if both:
        feats_ok = [(ra["feat"], ra["side"]) for ra, _ in both]
        L += ["## 4. Accepted filters applied to the whole history (thresholds = median of v2 trades)", "",
              "| variant | trades | win% | net R | PF | 300 -> | max DD | loss streak |", "|---|---|---|---|---|---|---|---|"]
        def row(nm, c):
            t_ = base_trades(df, c, a, WARM, n)
            s_ = summarize(t_)
            e_, d_ = equity(t_)
            L.append(f"| {nm} | {s_['n']} | {s_['win_rate']*100:.0f} | {s_['net_r']:+.1f} | {re_.fmt(s_['pf'])} | {e_:.0f} | {d_*100:.0f}% | {streak(t_)} |")
        row("v2 (no extra filter)", cond)
        combo = cond.copy()
        for f, sd in feats_ok:
            med = float(np.nanmedian(tt[f]))
            m = (F[f] >= med) if sd == "high" else (F[f] < med)
            m = np.nan_to_num(m, nan=0).astype(bool)
            row(f"v2 + {f} {sd} (median {med:.3g})", cond & m)
            combo &= m
        row("v2 + ALL accepted filters together", combo)
        L += ["", "Combining filters cuts the number of trades a lot; if the trade count drops below about 40 the numbers are not reliable.", ""]
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="PAXGUSDT")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--out", default="deep_out")
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    df = make_null_1h(24 * 900, 17) if a.synthetic else fetch_klines(a.symbol, "1h", a.days, 3_600_000)
    L = report(df, a.symbol)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
