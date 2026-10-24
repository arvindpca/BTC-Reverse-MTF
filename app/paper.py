"""Paper-trading rules for CoinDCX-style futures: sizing, liquidation guard, and NO duplicate entries.

Research/paper only - no exchange calls. The same rules are meant to be reused by a live executor later.

Duplicate protection (all four are enforced here):
  1. every signal id is traded at most once (remembered across restarts in `state_path`)
  2. one position at a time; a same-side signal while in a trade is ignored
  3. an opposite signal closes the position and flips (the 'reverse' mechanism)
  4. every order carries a deterministic client_order_id derived from the signal id
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PaperConfig:
    margin: float = 300.0          # capital used per account (in your margin currency)
    leverage: int = 30             # maximum leverage; same hard cap as BTC-SMC-Live
    sizing: str = "full"           # "full": notional = margin x leverage | "risk": a stop loses `risk_pct` of margin
    risk_pct: float = 2.0
    maint_pct: float = 0.5         # ASSUMED maintenance margin %, check the CoinDCX contract page
    liq_buffer: float = 0.9        # skip signals whose stop is beyond 90% of the liquidation distance
    fee_pct: float = 0.06          # assumed per side
    slip_pct: float = 0.02         # assumed per side
    leverage_cap: int = 30

    def __post_init__(self):
        if not (1 <= self.leverage <= self.leverage_cap):
            raise ValueError(f"leverage must be 1..{self.leverage_cap}")
        if self.margin <= 0 or self.sizing not in ("full", "risk") or self.liq_dist_pct <= 0:
            raise ValueError("bad paper config")

    @property
    def liq_dist_pct(self) -> float:
        return 100.0 / self.leverage - self.maint_pct


def size_position(cfg: PaperConfig, entry: float, stop: float) -> tuple[dict | None, str]:
    stop_pct = abs(entry - stop) / entry * 100.0
    if stop_pct <= 0:
        return None, "BAD_STOP"
    if stop_pct > cfg.liq_buffer * cfg.liq_dist_pct:
        return None, "STOP_BEYOND_LIQUIDATION_GUARD"
    full = cfg.margin * cfg.leverage
    notional = full if cfg.sizing == "full" else min(full, cfg.margin * cfg.risk_pct / stop_pct)
    return dict(notional=notional, qty=notional / entry, margin_used=notional / cfg.leverage,
                loss_at_stop=notional * stop_pct / 100.0,
                fee_round_trip=notional * 2 * (cfg.fee_pct + cfg.slip_pct) / 100.0), "OK"


def client_order_id(signal_id: str) -> str:
    return "rv" + hashlib.sha1(signal_id.encode()).hexdigest()[:16]


class PaperBook:
    def __init__(self, cfg: PaperConfig, state_path: str | Path | None = None):
        self.cfg, self.path = cfg, (Path(state_path) if state_path else None)
        self.position: dict | None = None
        self.seen: set[str] = set()
        self.closed: list[dict] = []
        if self.path and self.path.exists():
            st = json.loads(self.path.read_text())
            self.position, self.seen, self.closed = st["position"], set(st["seen"]), st["closed"]

    def _save(self):
        if self.path:
            self.path.write_text(json.dumps(dict(position=self.position, seen=sorted(self.seen), closed=self.closed)))

    def _close(self, price: float, reason: str):
        p = self.position
        gross = p["side"] * (price - p["entry"]) / p["entry"] * p["notional"]
        if reason == "LIQUIDATED":
            gross = -p["margin_used"]                               # liquidation takes the whole margin (loss + maintenance)
        pnl = max(gross, -p["margin_used"]) - p["fee_round_trip"]
        self.closed.append(dict(signal_id=p["signal_id"], side=p["side"], entry=p["entry"], exit=price,
                                reason=reason, pnl=round(pnl, 4)))
        self.position = None

    def on_signal(self, signal_id: str, side: int, entry: float, stop: float) -> dict:
        if signal_id in self.seen:
            return dict(action="REJECT", reason="DUPLICATE_SIGNAL")
        self.seen.add(signal_id)                                    # each signal is decided exactly once
        if self.position and self.position["side"] == side:
            self._save()
            return dict(action="REJECT", reason="SAME_SIDE_POSITION_OPEN")
        if (side > 0 and stop >= entry) or (side < 0 and stop <= entry):
            self._save()
            return dict(action="REJECT", reason="STOP_ON_WRONG_SIDE")
        sized, why = size_position(self.cfg, entry, stop)
        flipped = False
        if self.position:                                           # opposite signal: reverse
            self._close(entry, "REVERSE")
            flipped = True
        if sized is None:
            self._save()
            return dict(action="CLOSED_ONLY" if flipped else "REJECT", reason=why)
        liq = entry * (1 - side * self.cfg.liq_dist_pct / 100.0)
        self.position = dict(signal_id=signal_id, side=side, entry=entry, stop=stop, liq=liq,
                             client_order_id=client_order_id(signal_id), **sized)
        self._save()
        return dict(action="FLIP" if flipped else "OPEN", reason="OK", order=self.position)

    def on_candle(self, high: float, low: float) -> dict | None:
        """Exit check on a finished candle: stop and liquidation, whichever is nearer to entry; stop first if equal."""
        p = self.position
        if not p:
            return None
        if p["side"] > 0:
            level, hit = max(p["stop"], p["liq"]), low <= max(p["stop"], p["liq"])
        else:
            level, hit = min(p["stop"], p["liq"]), high >= min(p["stop"], p["liq"])
        if not hit:
            return None
        reason = "STOP" if level == p["stop"] else "LIQUIDATED"
        self._close(level, reason)
        self._save()
        return self.closed[-1]
