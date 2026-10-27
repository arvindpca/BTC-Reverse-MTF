"""PAPER trading (log only, NO real orders) for the BTC 1h momentum setup found in the 1h/4h study.

Setup (frozen, same as the backtest):
  signal on a CLOSED 1h candle: green candle, body > 70% of range, volume > 1.5x avg(20)  (candle_momo)
                                + ADX(14) > 25 + EMA20 > EMA50 on 1h
  entry at the NEXT candle's open, stop = entry - 1.5 x ATR(14 of the signal candle), target = entry + 3 x stop distance,
  time exit at the close of the 48th candle. Stop checked before target inside one candle. One position at a time.
  Skip if the stop is < 0.25% of price.
Money plan: start 3000, +1000 added at the start of every new month, risk 2% of the account per trade
  (4% after 6 months if there were >= 20 trades and the total R is positive). Position capped at 30x the account.
  Costs per side 0.05% fee + 18% GST + 0.02% slippage, funding 0.01% charged per 8h crossed.
Rule: if the account falls 20% below its best level, a STOP-AND-CHECK alert is sent (trading log continues).

python -m intraday.paper_btc1h --state paper_btc1h/state.json --out paper_btc1h
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

PAIR = "B-BTC_USDT"
SETTINGS = {
    "start_capital": 3000.0, "monthly_add": 1000.0, "risk": 0.02, "risk_upgraded": 0.04,
    "upgrade_after_months": 6, "upgrade_min_trades": 20, "max_leverage": 30,
    "sl_atr": 1.5, "rr": 3.0, "hold_bars": 48, "min_stop_pct": 0.25,
    "cost_per_side_pct": 0.05 * 1.18 + 0.02, "funding_pct_per_8h": 0.01, "dd_alert": 0.20,
}
IST = pd.Timedelta(hours=5, minutes=30)
H = pd.Timedelta(hours=1)
EIGHT_H = pd.Timedelta(hours=8)


def ist(ts) -> str:
    return (pd.Timestamp(ts) + IST).strftime("%d-%b %H:%M IST")


def signal_mask(f: pd.DataFrame) -> np.ndarray:
    from .signals import families, filters
    fam, flt = families(f), filters(f)
    return fam["candle_momo"][0] & flt["adx_trend"][0] & flt["htf1h"][0]


def new_state(last_bar: pd.Timestamp, now_month: str) -> dict:
    s = SETTINGS
    return {"version": 1, "pair": PAIR, "started_at": str(last_bar + H), "settings": s,
            "equity": s["start_capital"], "deposited": s["start_capital"], "peak": s["start_capital"],
            "risk": s["risk"], "month": now_month, "last_bar": str(last_bar), "pending": None, "open": None,
            "trades": [], "deposits": [{"month": now_month, "amount": s["start_capital"]}], "dd_alerted": False,
            "months_done": []}


def _funding_n(t_in: pd.Timestamp, t_out: pd.Timestamp) -> int:
    return int(t_out.value // EIGHT_H.value - t_in.value // EIGHT_H.value)


def _month_report(st: dict, month: str) -> str:
    tr = [t for t in st["trades"] if t["exit_time"][:7] == month]
    pnl = sum(t["pnl"] for t in tr)
    wins = sum(t["pnl"] > 0 for t in tr)
    return (f"BTC 1h PAPER - {month} ka hisaab\n"
            f"trades {len(tr)}, jeet {wins}, mahine ka P/L {pnl:+.0f}\n"
            f"account {st['equity']:.0f}, ab tak kul daala {st['deposited']:.0f}, "
            f"fayda/nuksaan {st['equity'] - st['deposited']:+.0f}")


def step(st: dict, f: pd.DataFrame, mask: np.ndarray) -> tuple[dict, list[str]]:
    """Process every CLOSED candle after st['last_bar'] in time order. Idempotent: re-running on the same data does nothing."""
    s = st["settings"]
    msgs: list[str] = []
    last = pd.Timestamp(st["last_bar"])
    idx = np.flatnonzero(f.index > last)
    o, h, l, c, a = (f[k].to_numpy(float) for k in ("open", "high", "low", "close", "atr"))
    for i in idx:
        t = f.index[i]
        month = t.strftime("%Y-%m")
        # ---- new month: report the old one, add the monthly money, maybe upgrade risk
        if month != st["month"]:
            msgs.append(_month_report(st, st["month"]))
            st["months_done"].append(st["month"])
            st["month"] = month
            st["equity"] += s["monthly_add"]
            st["deposited"] += s["monthly_add"]
            st["peak"] = max(st["peak"], st["equity"])
            st["deposits"].append({"month": month, "amount": s["monthly_add"]})
            msgs.append(f"Naya mahina {month}: +{s['monthly_add']:.0f} joda (paper). Account ab {st['equity']:.0f}")
            if st["risk"] < s["risk_upgraded"] and len(st["months_done"]) >= s["upgrade_after_months"]:
                n = len(st["trades"])
                tot = sum(x["R"] for x in st["trades"])
                if n >= s["upgrade_min_trades"] and tot > 0:
                    st["risk"] = s["risk_upgraded"]
                    msgs.append(f"Plan rule: {n} trades, kul {tot:+.1f}R plus -> risk ab {100 * st['risk']:.0f}% per trade")
        # ---- fill a pending entry at this candle's open
        if st["pending"] and not st["open"]:
            p = st["pending"]
            entry = o[i]
            d = p["stop_dist"]
            risk_amt = st["equity"] * st["risk"]
            pos = min(risk_amt / (d / entry), st["equity"] * s["max_leverage"])
            st["open"] = {"signal_time": p["signal_time"], "entry_time": str(t), "entry": entry,
                          "stop": entry - d, "target": entry + s["rr"] * d, "stop_dist": d,
                          "stop_pct": 100 * d / entry, "position": pos, "qty": pos / entry,
                          "margin_30x": pos / s["max_leverage"], "risk_amt": pos * d / entry, "held": 0,
                          "equity_at_entry": st["equity"], "risk_used": st["risk"]}
            st["pending"] = None
            op = st["open"]
            msgs.append(f"PAPER ENTRY BTC LONG bhar gaya @ {entry:.1f} ({ist(t)})\n"
                        f"SL {op['stop']:.1f} ({op['stop_pct']:.2f}%), Target {op['target']:.1f}\n"
                        f"position {pos:.0f} (qty {op['qty']:.5f} BTC), 30x margin {op['margin_30x']:.0f}, "
                        f"SL lage to loss ~{op['risk_amt']:.0f}")
        # ---- manage the open position on this candle
        if st["open"]:
            op = st["open"]
            reason = px = None
            if l[i] <= op["stop"]:
                reason, px = "SL", min(o[i], op["stop"])
            elif h[i] >= op["target"]:
                reason, px = "TP", op["target"]
            else:
                op["held"] += 1
                if op["held"] >= s["hold_bars"]:
                    reason, px = "TIME (48h)", c[i]
            if reason:
                t_in = pd.Timestamp(op["entry_time"])
                fn = _funding_n(t_in, t + H)
                gross = (px - op["entry"]) / op["entry"]
                net = gross - 2 * s["cost_per_side_pct"] / 100 - fn * s["funding_pct_per_8h"] / 100
                pnl = op["position"] * net
                R = net / (op["stop_dist"] / op["entry"])
                st["equity"] += pnl
                st["peak"] = max(st["peak"], st["equity"])
                tr = {"signal_time": op["signal_time"], "entry_time": op["entry_time"], "exit_time": str(t + H),
                      "entry_ist": ist(op["entry_time"]), "exit_ist": ist(t + H), "entry": round(op["entry"], 2),
                      "exit": round(px, 2), "reason": reason, "stop_pct": round(op["stop_pct"], 3),
                      "position": round(op["position"], 2), "risk_used": op["risk_used"], "funding_n": fn,
                      "net_ret_pct": round(100 * net, 4), "R": round(R, 3), "pnl": round(pnl, 2),
                      "equity": round(st["equity"], 2)}
                st["trades"].append(tr)
                st["open"] = None
                msgs.append(f"PAPER EXIT BTC LONG - {reason}\nentry {tr['entry']:.1f} -> exit {tr['exit']:.1f}\n"
                            f"result {R:+.2f}R, P/L {pnl:+.0f}\naccount {st['equity']:.0f} "
                            f"(kul daala {st['deposited']:.0f}, fayda {st['equity'] - st['deposited']:+.0f})")
                dd = (st["peak"] - st["equity"]) / st["peak"]
                if dd >= s["dd_alert"] and not st["dd_alerted"]:
                    st["dd_alerted"] = True
                    msgs.append(f"RULE ALERT: account best level se {100 * dd:.0f}% neeche. Plan ke hisaab se RUKO aur check karo.")
                elif dd < s["dd_alert"] / 2:
                    st["dd_alerted"] = False
        # ---- new signal on this closed candle (only when flat)
        if not st["open"] and not st["pending"] and mask[i] and np.isfinite(a[i]):
            d = s["sl_atr"] * a[i]
            if 100 * d / c[i] >= s["min_stop_pct"]:
                st["pending"] = {"signal_time": str(t), "stop_dist": d}
                risk_amt = st["equity"] * st["risk"]
                pos = min(risk_amt / (d / c[i]), st["equity"] * s["max_leverage"])
                msgs.append(f"PAPER SIGNAL BTC LONG (koi asli order nahi)\ncandle band {ist(t + H)}, close {c[i]:.1f}\n"
                            f"agli candle ke open par BUY. Andaaza: SL ~{c[i] - d:.1f} ({100 * d / c[i]:.2f}%), "
                            f"Target ~{c[i] + s['rr'] * d:.1f}\nposition ~{pos:.0f} (risk {100 * st['risk']:.0f}% = {risk_amt:.0f}), "
                            f"30x margin ~{pos / s['max_leverage']:.0f}")
        st["last_bar"] = str(t)
    return st, msgs


def report(st: dict, last_close: float | None) -> str:
    s = st["settings"]
    L = ["# BTC 1h PAPER trading (log only, no real orders)", "",
         f"Started {ist(st['started_at'])}. Last candle checked: {ist(pd.Timestamp(st['last_bar']) + H)} (close "
         f"{last_close if last_close is not None else '-'}).", "",
         f"Plan: start {s['start_capital']:.0f}, +{s['monthly_add']:.0f} every month, risk {100 * st['risk']:.0f}% per trade "
         f"(4% after 6 months if >= 20 trades and total R > 0), 20% drawdown = stop-and-check.", "",
         f"**Account {st['equity']:.0f}** | kul daala {st['deposited']:.0f} | fayda/nuksaan **{st['equity'] - st['deposited']:+.0f}** "
         f"| best level {st['peak']:.0f}", ""]
    if st["open"]:
        op = st["open"]
        unr = ""
        if last_close is not None:
            g = (last_close - op["entry"]) / op["entry"]
            unr = f", abhi {100 * g:+.2f}% = {op['position'] * g:+.0f}"
        L += ["## OPEN position", "", f"LONG since {ist(op['entry_time'])} @ {op['entry']:.1f}, SL {op['stop']:.1f}, "
              f"target {op['target']:.1f}, position {op['position']:.0f}, candles held {op['held']}/48{unr}", ""]
    elif st["pending"]:
        L += ["## Signal aaya, agli candle ke open par entry hogi", ""]
    else:
        L += ["Koi open trade nahi.", ""]
    tr = pd.DataFrame(st["trades"])
    if len(tr):
        tr["month"] = tr.exit_time.str[:7]
        g = tr.groupby("month").agg(trades=("pnl", "size"), wins=("pnl", lambda x: int((x > 0).sum())),
                                    pnl=("pnl", "sum"), R=("R", "sum"))
        L += ["## Monthly", "", "| month | trades | wins | P/L | R |", "|---|---|---|---|---|"]
        L += [f"| {m} | {r.trades} | {r.wins} | {r.pnl:+.0f} | {r.R:+.2f} |" for m, r in g.iterrows()]
        L += ["", "## Trades", "", "| entry (IST) | exit (IST) | entry | exit | reason | stop % | position | R | P/L | account |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        L += [f"| {x.entry_ist} | {x.exit_ist} | {x.entry} | {x.exit} | {x.reason} | {x.stop_pct} | {x.position:.0f} | "
              f"{x.R:+.2f} | {x.pnl:+.0f} | {x.equity:.0f} |" for x in tr.itertuples()]
        L += ["", f"Total: {len(tr)} trades, win {100 * (tr.pnl > 0).mean():.0f}%, {tr.R.sum():+.2f}R, P/L {tr.pnl.sum():+.0f}"]
    else:
        L += ["Abhi tak koi trade band nahi hua."]
    return "\n".join(L) + "\n"


def run(state_path: Path, out: Path, *, f: pd.DataFrame | None = None, send=None) -> list[str]:
    from app.notify import send_telegram
    send = send or send_telegram
    out.mkdir(parents=True, exist_ok=True)
    if f is None:
        from .clean import clean
        from .data import fetch_candles
        from .features import build
        raw, _ = fetch_candles(PAIR, "1h", 90)
        df, rep = clean(raw, "1h")
        f = build(df, "1h")
    mask = signal_mask(f)
    if state_path.exists():
        st = json.loads(state_path.read_text())
        msgs_pre = []
    else:
        last = f.index[-1]
        st = new_state(last, last.strftime("%Y-%m"))
        s = st["settings"]
        msgs_pre = [f"BTC 1h PAPER TRADE shuru (koi asli order nahi)\ncapital {s['start_capital']:.0f}, har mahine +{s['monthly_add']:.0f}, "
                    f"risk {100 * s['risk']:.0f}% per trade\nSetup: 1h strong green candle + volume + ADX>25 + EMA20>EMA50, "
                    f"SL 1.5 ATR, target 3R, 48h max.\nSignal aane par yahin message aayega."]
    st, msgs = step(st, f, mask)
    msgs = msgs_pre + msgs
    for m in msgs:
        send(m)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(st, indent=2, default=str))
    (out / "report.md").write_text(report(st, float(f["close"].iloc[-1])))
    pd.DataFrame(st["trades"]).to_csv(out / "trades.csv", index=False)
    (out / "messages_last_run.txt").write_text("\n\n".join(msgs) if msgs else "(no new events)")
    return msgs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="paper_btc1h/state.json")
    ap.add_argument("--out", default="paper_btc1h")
    a = ap.parse_args(argv)
    msgs = run(Path(a.state), Path(a.out))
    print(f"{len(msgs)} new event(s)")
    for m in msgs:
        print("---\n" + m)


if __name__ == "__main__":
    main()
