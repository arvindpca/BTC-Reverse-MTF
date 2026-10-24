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


def build_events(res: dict, state: dict, symbol: str) -> list[str]:
    """Messages for NEW entries and NEW exits only. Mutates `state['notified_entries'/'notified_exits']` so nothing repeats."""
    msgs: list[str] = []
    first = "notified_exits" not in state
    ent, ext = set(state.get("notified_entries", [])), set(state.get("notified_exits", []))
    for r in res["closed"]:
        k = r["entry_time"]
        if k not in ext:
            if not first:
                msgs.append(f"PAPER EXIT {symbol} LONG\nentry {r['entry']:.2f} at {r['entry_time'][:16]} UTC\n"
                            f"exit {r['exit']:.2f} ({r['reason']}) at {r['exit_time'][:16]} UTC\nresult {r['net_r']:+.2f} R, P/L {r['pnl']:+.2f}, "
                            f"paper equity {r['equity']:.2f}")
            ext.add(k)
            ent.add(k)
    o = res["open"]
    if o and o["signal_id"] not in ent:
        msgs.append(f"PAPER ENTRY {symbol} LONG (log only, no real order)\nsignal {o['signal_id'][:16]} UTC at {o['entry']:.2f}\n"
                    f"stop {o['initial_stop']:.2f} ({o['stop_pct']:.2f}% away)\nsize notional {o['notional']:.0f}, margin at 30x {o['margin_at_30x']:.1f}\n"
                    f"liquidation about {o['liquidation']:.2f}")
        ent.add(o["signal_id"])
    state["notified_entries"], state["notified_exits"] = sorted(ent), sorted(ext)
    return msgs
