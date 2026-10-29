"""LIVE-METHOD paper trading for the BTC 1h setup (behaves like a real bot, but places NO orders).

How it differs from the hourly paper log (paper_btc1h.py):
  * runs continuously (one GitHub job of ~6 hours, then the next one takes over from the saved state)
  * the moment a 1h candle closes with a signal -> BUY at the LIVE price right then (like a market order)
  * stop loss and target are watched every ~15 s from CoinDCX 1-minute candles (high/low, so spikes are not missed)
      - stop: fills at the stop, or at the 1-minute open if price gapped through it (like a stop-market order)
      - target: fills at the target (like a take-profit limit order)
      - stop and target inside the same minute -> stop first (pessimistic)
  * 48 hours after entry -> sell at the live price
  * a Telegram message goes out immediately for every entry / exit
  * restart-safe: after a gap it replays the missed 1-minute candles, so a stop/target hit during the gap is still
    booked at the right price (the alert just comes late). A signal found more than 15 min late is skipped, not chased.
Same rules, money plan and costs as the backtest (see paper_btc1h.py).

python -m intraday.live_btc1h --state-dir <dir> --minutes 345 [--save-cmd "bash intraday/live_save.sh <dir>"]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .paper_btc1h import (HEAD, LINE, PAIR, SETTINGS, _funding_n, _money, _month_report, ist, msg, n, report,
                          signal_mask)

H = pd.Timedelta(hours=1)
M = pd.Timedelta(minutes=1)
LIVE_HEAD = HEAD.replace("PAPER TRADE", "PAPER TRADE (LIVE)")
STALE_SIGNAL = pd.Timedelta(minutes=15)
HEARTBEAT_UTC_HOUR = 3  # 08:30 IST daily status


def lmsg(title, *blocks):
    return msg(title, *blocks).replace(HEAD, LIVE_HEAD, 1)


# ------------------------------------------------------------------------------------------------ data feed
class CoinDCXFeed:
    """Public CoinDCX futures candles. 1h for signals, 1m for live price / stop / target."""

    def __init__(self, log=print):
        import requests
        self.s = requests.Session()
        self.log = log

    def hourly(self) -> pd.DataFrame:
        from .clean import clean
        from .data import fetch_candles
        from .features import build
        raw, _ = fetch_candles(PAIR, "1h", 90, session=self.s, log=self.log)
        df, _ = clean(raw, "1h")
        return build(df, "1h")

    def minutes(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        """1m candles with open time in [start, end], INCLUDING the still-forming minute (its close = live price)."""
        from .data import CANDLES_URL, _get_json, parse_candles
        out, cur = [], int(start.timestamp()) // 60 * 60
        stop = int(end.timestamp())
        while cur <= stop:
            to = min(stop, cur + 900 * 60)
            js = _get_json(self.s, CANDLES_URL, {"pair": PAIR, "from": cur, "to": to, "resolution": "1", "pcode": "f"},
                           log=self.log)
            df = parse_candles(js)
            if len(df):
                out.append(df)
            cur = to + 60
        if not out:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.concat(out)
        df = df[~df.index.duplicated(keep="last")].sort_index()
        return df[(df.index >= start.floor("min")) & (df.index <= end)]


# ------------------------------------------------------------------------------------------------ trader
class LiveTrader:
    def __init__(self, st: dict, feed, send, save, log=print):
        self.st, self.feed, self.send, self.save, self.log = st, feed, send, save, log
        s = st.setdefault("settings", dict(SETTINGS))
        for k, v in SETTINGS.items():
            s.setdefault(k, v)
        st.setdefault("mode", "live")
        st.setdefault("events", [])
        if st.get("pending"):                       # left over from the hourly paper log -> cannot be filled live now
            st["events"].append({"t": str(pd.Timestamp.now(tz="UTC")), "e": f"old pending signal dropped: {st['pending']}"})
            st["pending"] = None
        self.dirty = False

    # ---- helpers
    def _say(self, text):
        self.send(text)
        self.st["events"] = (self.st["events"] + [{"t": str(pd.Timestamp.now(tz="UTC")), "e": text.split("\n")[3] if text.count("\n") > 3 else text[:80]}])[-200:]
        self.dirty = True

    def housekeeping(self, now: pd.Timestamp):
        st, s = self.st, self.st["settings"]
        month = now.strftime("%Y-%m")
        if month != st["month"]:
            self._say(_month_report(st, st["month"]).replace(HEAD, LIVE_HEAD, 1))
            st["months_done"].append(st["month"])
            st["month"] = month
            st["equity"] += s["monthly_add"]
            st["deposited"] += s["monthly_add"]
            st["peak"] = max(st["peak"], st["equity"])
            st["deposits"].append({"month": month, "amount": s["monthly_add"]})
            self._say(lmsg(f"💰 NAYA MAHINA: +{n(s['monthly_add'])} joda (paper)", _money(st)))
            if st["risk"] < s["risk_upgraded"] and len(st["months_done"]) >= s["upgrade_after_months"]:
                k, tot = len(st["trades"]), sum(x["R"] for x in st["trades"])
                if k >= s["upgrade_min_trades"] and tot > 0:
                    st["risk"] = s["risk_upgraded"]
                    self._say(lmsg("⬆️ RISK BADHA (plan ka rule)", [f"{k} trades, kul {tot:+.1f}R (plus)",
                                                                   f"Ab har trade ka risk: {100 * st['risk']:.0f}%"]))
        day = now.strftime("%Y-%m-%d")
        if now.hour >= HEARTBEAT_UTC_HOUR and st.get("last_heartbeat") != day:
            st["last_heartbeat"] = day
            op = st.get("open")
            blk = ["Koi trade khula nahi hai, signal ka intezaar."]
            if op:
                last = st.get("last_price") or op["entry"]
                g = (last - op["entry"]) / op["entry"]
                blk = [f"Khula trade: BUY @ {n(op['entry'], 1)}", f"SL {n(op['stop'], 1)} | Target {n(op['target'], 1)}",
                       f"Abhi price ~{n(last, 1)} ({100 * g:+.2f}%, ~{op['position'] * g:+,.0f})"]
            self._say(lmsg("🟢 SYSTEM CHAL RAHA HAI (roz ka status)", blk, _money(st)))

    def on_hour(self, now: pd.Timestamp, f: pd.DataFrame | None = None):
        """Check the 1h candles that closed since the last check. Live entry only for a fresh signal."""
        st, s = self.st, self.st["settings"]
        f = self.feed.hourly() if f is None else f
        last = pd.Timestamp(st["last_bar"])
        new = f.index[f.index > last]
        if not len(new):
            return False
        mask = signal_mask(f)
        a, c = f["atr"].to_numpy(float), f["close"].to_numpy(float)
        for t in new:
            i = f.index.get_loc(t)
            if mask[i] and not st.get("open") and np.isfinite(a[i]):
                d = s["sl_atr"] * a[i]
                if 100 * d / c[i] < s["min_stop_pct"]:
                    st["events"].append({"t": str(now), "e": f"signal {t} skipped: stop < {s['min_stop_pct']}%"})
                elif t == new[-1] and now - (t + H) <= STALE_SIGNAL:
                    self.enter(now, t, d)
                else:
                    self._say(lmsg("⚠️ SIGNAL CHHOOT GAYA", [f"Candle band {ist(t + H)} par signal tha,",
                                                            "system der se chala, isliye entry nahi li (pichha nahi karte)."]))
            st["last_bar"] = str(t)
        self.dirty = True
        return True

    def enter(self, now: pd.Timestamp, sig_t: pd.Timestamp, d: float):
        st, s = self.st, self.st["settings"]
        m = self.feed.minutes(now - 3 * M, now)
        if not len(m):
            self.log("no live price for entry, will retry")
            raise RuntimeError("no live price")
        px = float(m["close"].iloc[-1])
        risk_amt = st["equity"] * st["risk"]
        pos = min(risk_amt / (d / px), st["equity"] * s["max_leverage"])
        st["open"] = {"signal_time": str(sig_t), "entry_time": str(now), "entry": px, "stop": px - d,
                      "target": px + s["rr"] * d, "stop_dist": d, "stop_pct": 100 * d / px, "position": pos,
                      "qty": pos / px, "margin_30x": pos / s["max_leverage"], "risk_amt": pos * d / px,
                      "equity_at_entry": st["equity"], "risk_used": st["risk"], "last_check": str(now.floor("min")),
                      "mode": "live"}
        st["last_price"] = px
        op = st["open"]
        self._say(lmsg("✅ BUY HO GAYA (LONG) — live price par",
                       ["Coin: BTC/USDT Futures (CoinDCX)", f"Signal candle band: {ist(sig_t + H)}",
                        f"Entry time: {ist(now)}", f"Entry price: {n(px, 1)}",
                        f"🛑 Stop Loss: {n(op['stop'], 1)}  (-{op['stop_pct']:.2f}%)",
                        f"🎯 Target: {n(op['target'], 1)}  (+{s['rr'] * op['stop_pct']:.2f}%)",
                        f"⏱ Time exit: {ist(now + 48 * H)}"],
                       [f"Position: {n(pos)}  (qty {op['qty']:.4f} BTC)", f"Margin (30x): {n(op['margin_30x'])}",
                        f"SL lage to loss: ~{n(op['risk_amt'])}", f"Target lage to profit: ~{n(op['risk_amt'] * s['rr'])}"]))

    def monitor(self, now: pd.Timestamp, m: pd.DataFrame | None = None):
        """Check SL / target / 48h on 1m candles since the last check (replays any gap)."""
        st, op = self.st, self.st.get("open")
        if not op:
            return
        entry_t = pd.Timestamp(op["entry_time"])
        frm = max(pd.Timestamp(op["last_check"]), entry_t.floor("min"))
        m = self.feed.minutes(frm, now) if m is None else m
        deadline = entry_t + 48 * H
        for t, r in m.iterrows():
            if t < entry_t.floor("min"):
                continue
            if t >= deadline:                              # 48h over before this minute: sell at its open
                return self.exit(t, float(r.open), "TIME (48h)")
            first_min = t == entry_t.floor("min")          # part of this minute was before the entry: use close only
            lo, hi = (r.close, r.close) if first_min else (r.low, r.high)
            done_t = min(t + M, now)
            if lo <= op["stop"]:
                return self.exit(done_t, float(op["stop"] if first_min else min(r.open, op["stop"])), "SL")
            if hi >= op["target"]:
                return self.exit(done_t, float(op["target"]), "TP")
            st["last_price"] = float(r.close)
            if t + M <= now:
                op["last_check"] = str(t)                  # the forming minute is re-checked next time
            if t + M > deadline and t + M <= now:          # deadline fell inside this finished minute
                return self.exit(t + M, float(r.close), "TIME (48h)")
        if now >= deadline + 5 * M and st.get("open"):    # no candles at all after the deadline
            return self.exit(now, float(st.get("last_price") or op["entry"]), "TIME (48h)")

    def exit(self, t: pd.Timestamp, px: float, reason: str):
        st, s, op = self.st, self.st["settings"], self.st["open"]
        t_in = pd.Timestamp(op["entry_time"])
        fn = _funding_n(t_in, t)
        net = (px - op["entry"]) / op["entry"] - 2 * s["cost_per_side_pct"] / 100 - fn * s["funding_pct_per_8h"] / 100
        pnl, R = op["position"] * net, net / (op["stop_dist"] / op["entry"])
        st["equity"] += pnl
        st["peak"] = max(st["peak"], st["equity"])
        tr = {"signal_time": op["signal_time"], "entry_time": op["entry_time"], "exit_time": str(t),
              "entry_ist": ist(t_in), "exit_ist": ist(t), "entry": round(op["entry"], 2), "exit": round(px, 2),
              "reason": reason, "stop_pct": round(op["stop_pct"], 3), "position": round(op["position"], 2),
              "risk_used": op["risk_used"], "funding_n": fn, "net_ret_pct": round(100 * net, 4), "R": round(R, 3),
              "pnl": round(pnl, 2), "equity": round(st["equity"], 2), "mode": op.get("mode", "hourly")}
        st["trades"].append(tr)
        st["open"] = None
        why = {"SL": "🔴 STOP LOSS laga", "TP": "🟢 TARGET laga"}.get(reason, "⏱ 48 GHANTE pure")
        self._say(lmsg(f"{why} — SELL (EXIT)", [f"Entry: {n(tr['entry'], 1)}  →  Exit: {n(px, 1)}",
                                                f"Exit time: {ist(t)}",
                                                f"Is trade ka P/L: {'+' if pnl >= 0 else ''}{n(pnl)}  ({R:+.2f}R)"],
                       _money(st)))
        dd = (st["peak"] - st["equity"]) / st["peak"]
        if dd >= s["dd_alert"] and not st["dd_alerted"]:
            st["dd_alerted"] = True
            self._say(lmsg("⚠️ RULE ALERT: RUKO AUR CHECK KARO",
                           [f"Account apne best level se {100 * dd:.0f}% neeche hai."], _money(st)))
        elif dd < s["dd_alert"] / 2:
            st["dd_alerted"] = False


# ------------------------------------------------------------------------------------------------ runner
def write_outputs(st: dict, d: Path, log_lines: list[str]):
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text(json.dumps(st, indent=2, default=str))
    (d / "report.md").write_text(report(st, st.get("last_price")).replace(
        "# BTC 1h PAPER trading (log only, no real orders)", "# BTC 1h PAPER trading — LIVE method (no real orders)"))
    pd.DataFrame(st["trades"]).to_csv(d / "trades.csv", index=False)
    (d / "live_log.txt").write_text("\n".join(log_lines[-400:]) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--minutes", type=float, default=345)
    ap.add_argument("--save-cmd", default="")
    ap.add_argument("--poll", type=float, default=15)
    a = ap.parse_args(argv)
    from app.notify import send_telegram
    d = Path(a.state_dir)
    lines: list[str] = []

    def log(x):
        line = f"{pd.Timestamp.now(tz='UTC'):%m-%d %H:%M:%S} {x}"
        print(line, flush=True)
        lines.append(line)

    feed = CoinDCXFeed(log)
    sp = d / "state.json"
    if sp.exists():
        st = json.loads(sp.read_text())
        log(f"state loaded: equity {st['equity']:.2f}, trades {len(st['trades'])}, open {bool(st.get('open'))}")
        fresh = False
    else:
        f = feed.hourly()
        from .paper_btc1h import new_state
        st = new_state(f.index[-1], f.index[-1].strftime("%Y-%m"))
        fresh = True
    if fresh or st.get("mode") != "live":
        send_telegram(LIVE_HEAD + "\n" + LINE + "\n▶️ LIVE METHOD CHALU\nSignal aate hi live price par BUY, SL/Target har "
                      "~15 second check, hit hote hi turant message.\n" + LINE + "\n" + "\n".join(_money(st)))
    trader = LiveTrader(st, feed, send_telegram, None, log)
    st["mode"] = "live"

    def save(reason):
        write_outputs(st, d, lines)
        if a.save_cmd:
            r = subprocess.run(a.save_cmd + f" '{reason}'", shell=True, capture_output=True, text=True)
            if r.returncode:
                log(f"save failed: {r.stderr[-300:]}")
        trader.dirty = False

    end = time.time() + a.minutes * 60
    last_save, next_hour = time.time(), None
    save("start")
    while time.time() < end:
        now = pd.Timestamp.now(tz="UTC")
        try:
            trader.housekeeping(now)
            if next_hour is None or now >= next_hour:
                done = trader.on_hour(now)
                closed_expected = now.floor("h") - H
                if done or pd.Timestamp(st["last_bar"]) >= closed_expected:
                    next_hour = now.floor("h") + H + pd.Timedelta(seconds=20)
                else:                                     # candle not published yet: retry soon
                    next_hour = now + pd.Timedelta(seconds=20)
            trader.monitor(now)
        except Exception as exc:  # noqa: BLE001 - keep the bot alive; the next loop retries
            log(f"error: {exc!r}")
        if trader.dirty or time.time() - last_save > 900:
            save("event" if trader.dirty else "heartbeat")
            last_save = time.time()
        if st.get("open"):
            time.sleep(a.poll)
        else:
            wait = (next_hour - pd.Timestamp.now(tz="UTC")).total_seconds() if next_hour is not None else 5
            time.sleep(max(2.0, min(60.0, wait)))
    save("end of run")
    log("run finished, next run takes over")


if __name__ == "__main__":
    main()
