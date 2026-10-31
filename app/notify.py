"""Optional Telegram alerts for the paper runner. Does nothing unless TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set.
Never raises (a failed alert must not break the paper log) and never prints the token."""
from __future__ import annotations

import os

import requests


def send_telegram(text: str) -> bool:
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not tok or not chat:
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", json=dict(chat_id=chat, text=text[:3500]), timeout=15)
        return r.ok
    except requests.RequestException:
        return False


HEAD = "📘 PAXG (Digital Gold) · PAPER TRADE · v2"
LINE = "━━━━━━━━━━━━━━━━"
REASONS = {"TRAIL": "Trailing stop", "STOP": "Stop loss", "SL": "Stop loss", "TP": "Target", "TIME": "Time exit"}


def _ist(ts: str) -> str:
    """'2026-10-30 23:00:00+00:00' -> '31-Oct 04:30 IST'"""
    try:
        import pandas as pd
        t = pd.Timestamp(ts)
        t = t.tz_localize("UTC") if t.tzinfo is None else t
        return t.tz_convert("Asia/Kolkata").strftime("%d-%b %H:%M IST")
    except Exception:  # noqa: BLE001
        return f"{str(ts)[:16]} UTC"


def _n(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}"


def _entry_msg(o: dict) -> str:
    loss, prof = 1e5 * o["stop_pct"] / 100, 2e5 * o["stop_pct"] / 100
    return "\n".join([
        HEAD, LINE,
        "🟢 PAPER ENTRY — BUY (LONG)",
        "⚠️ Sirf paper par (no real order)",
        "",
        f"📅 Signal: {_ist(o['signal_id'])}",
        f"💵 Entry: {_n(o['entry'])}",
        f"🛑 Stop loss: {_n(o['initial_stop'])} ({o['stop_pct']:.2f}% neeche)",
        "",
        "📦 Paper account ke hisaab se:",
        f"   Position: {_n(o['notional'], 0)}",
        f"   Margin (30x): {_n(o['margin_at_30x'], 1)}",
        f"   Liquidation: ~{_n(o['liquidation'])}",
        "",
        "💡 1,00,000 ki position par (bina leverage):",
        f"   Stop laga to loss: ~{_n(loss, 0)}",
        f"   +2R par profit: ~{_n(prof, 0)}",
    ])


def _exit_msg(r: dict) -> str:
    win = r["net_r"] > 0
    reason = REASONS.get(str(r["reason"]).upper().split()[0], str(r["reason"]))
    return "\n".join([
        HEAD, LINE,
        f"{'✅' if win else '❌'} PAPER EXIT — SELL ({'PROFIT' if win else 'LOSS'})",
        "",
        f"💵 Entry: {_n(r['entry'])}  ({_ist(r['entry_time'])})",
        f"🏁 Exit: {_n(r['exit'])}  ({_ist(r['exit_time'])})",
        f"📌 Wajah: {reason}",
        "",
        f"📊 Result: {r['net_r']:+.2f}R  |  P/L: {r['pnl']:+,.2f}",
        f"💼 Paper account ab: {_n(r['equity'])}",
    ])


def build_events(res: dict, state: dict, symbol: str) -> list[str]:
    """Messages for NEW entries and NEW exits only. Mutates `state['notified_entries'/'notified_exits']` so nothing repeats."""
    msgs: list[str] = []
    first = "notified_exits" not in state
    ent, ext = set(state.get("notified_entries", [])), set(state.get("notified_exits", []))
    for r in res["closed"]:
        k = r["entry_time"]
        if k not in ext:
            if not first:
                msgs.append(_exit_msg(r))
            ext.add(k)
            ent.add(k)
    o = res["open"]
    if o and o["signal_id"] not in ent:
        msgs.append(_entry_msg(o))
        ent.add(o["signal_id"])
    state["notified_entries"], state["notified_exits"] = sorted(ent), sorted(ext)
    return msgs
