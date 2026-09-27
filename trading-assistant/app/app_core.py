"""App logic with no GUI and no MetaTrader5 import in it, so it can be
tested on its own. gui_app.py wraps this in a window; live_data.py is
the only file that actually talks to MetaTrader 5.

This does not duplicate the strategy detection or risk-gate rules -
it just wires the already-tested modules from trading-assistant/python
(strategy1_sweep_wick.py etc., levels.py, risk_gate.py, broker.py)
together into one live loop that can run any of the four strategy
choices in either Trade Assistant or Auto Trade mode.
"""

import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import strategy1_sweep_wick as s1
import strategy2_bos_fvg as s2
import strategy3_wick_sweep_after as s3
from broker import Broker, OrderRequest
from levels import fixed_distance_levels
from risk_gate import RiskGate

STRATEGY_CHOICES = [
    "Strategy 1 (Sweep + Equal-Wick)",
    "Strategy 2 (BOS + FVG Retest)",
    "Strategy 3 (Equal-Wick + Sweep After)",
    "Combined (all three)",
]
MODE_CHOICES = ["Trade Assistant (alerts only)", "Auto Trade (places real orders)"]
TIMEFRAME_CHOICES = ["M1", "M5", "M15", "M30", "H1"]


@dataclass
class UnifiedSignal:
    strategy: str
    time: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    detail: str


def compute_signals(
    strategy_choice: str,
    candles_s1: list,
    candles_s2: list,
    stop_distance: float,
    reward_multiple: float,
    lookback: int = 20,
    tolerance_ratio: float = 0.15,
    confirm_bars: int = 2,
    fvg_buffer_ratio: float = 0.25,
    max_wait_bars: int = 10,
) -> List[UnifiedSignal]:
    """Pure function: given candle history, returns every signal from
    whichever strategy/strategies are selected, each turned into the
    same entry/SL/TP shape regardless of which strategy found it.
    candles_s2 is a separate list because Strategy 2 defines its own
    Candle class (see strategy2_bos_fvg.py) - pass the same underlying
    market data built with each module's own Candle type."""
    out: List[UnifiedSignal] = []
    want_1 = strategy_choice.startswith("Strategy 1") or strategy_choice.startswith("Combined")
    want_2 = strategy_choice.startswith("Strategy 2") or strategy_choice.startswith("Combined")
    want_3 = strategy_choice.startswith("Strategy 3") or strategy_choice.startswith("Combined")

    if want_1:
        for sig in s1.find_signals(candles_s1, lookback, tolerance_ratio):
            sl, tp = fixed_distance_levels(sig.direction, sig.entry_price, stop_distance, reward_multiple)
            out.append(UnifiedSignal("Strategy 1", sig.time, sig.direction, sig.entry_price, sl, tp,
                                      f"sweep at {sig.sweep_time}"))

    if want_2:
        for sig in s2.find_signals(candles_s2, confirm_bars, fvg_buffer_ratio, reward_multiple):
            out.append(UnifiedSignal("Strategy 2", sig.time, sig.direction, sig.entry,
                                      sig.stop_loss, sig.take_profit_2, f"TP1 {sig.take_profit_1:.2f}"))

    if want_3:
        for sig in s3.find_signals(candles_s1, lookback, tolerance_ratio, max_wait_bars):
            sl, tp = fixed_distance_levels(sig.direction, sig.entry_price, stop_distance, reward_multiple)
            out.append(UnifiedSignal("Strategy 3", sig.time, sig.direction, sig.entry_price, sl, tp,
                                      f"candle at {sig.candle_time}"))

    out.sort(key=lambda u: u.time)
    return out


class AppController:
    """Owns the background polling loop. Kept separate from the Tk
    widgets so it can run (and be tested) without opening a window."""

    def __init__(self, log: Callable[[str], None]):
        self.log = log
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.gate: Optional[RiskGate] = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, config: dict, data_source, broker: Broker) -> None:
        if self.is_running():
            return
        self._stop_event.clear()
        self.gate = RiskGate(config["cooldown_bars"], config["max_consecutive_losses"])
        self._thread = threading.Thread(target=self._run, args=(config, data_source, broker), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def reset_gate(self) -> None:
        if self.gate is not None:
            self.gate.reset()
            self.log("Risk gate manually reset - trading is allowed again.")

    def run_once(self, config: dict, data_source, broker: Broker, last_bar_time: Optional[str]) -> Optional[str]:
        """Fetches the latest candles, checks the gate, and acts on any
        signal on the newest bar. Returns the newest bar's time (so the
        caller can pass it back in as last_bar_time next call) or None
        if no data was available this round. Split out from _run so it
        can be called directly, once, in a test - no thread involved."""
        candles_s1 = data_source.fetch_recent_candles("s1", config["symbol"], config["timeframe"], config["history_bars"])
        if not candles_s1:
            return last_bar_time

        current_bar_time = candles_s1[-1].time
        if current_bar_time == last_bar_time:
            return last_bar_time  # still the same forming/last bar, nothing new to do

        candles_s2 = data_source.fetch_recent_candles("s2", config["symbol"], config["timeframe"], config["history_bars"])

        symbol = config["symbol"]
        was_halted = self.gate is not None and self.gate.halted
        if self.gate is not None:
            self.gate.advance_bar()
            for outcome in broker.pop_closed_outcomes(symbol):
                self.gate.record_outcome(outcome)
            if self.gate.halted and not was_halted:
                self.log(f"RISK GATE HALTED: {self.gate.halted_reason}. "
                         f"Use the Reset Gate button to resume.")

        signals = compute_signals(
            config["strategy"], candles_s1, candles_s2,
            config["stop_distance"], config["reward_multiple"],
            lookback=config.get("lookback", 20),
            tolerance_ratio=config.get("tolerance_ratio", 0.15),
            confirm_bars=config.get("confirm_bars", 2),
            fvg_buffer_ratio=config.get("fvg_buffer_ratio", 0.25),
            max_wait_bars=config.get("max_wait_bars", 10),
        )
        newest = [sig for sig in signals if sig.time == current_bar_time]

        for sig in newest:
            self.log(
                f"[{sig.strategy}] {sig.direction} at {sig.time}: entry {sig.entry:.2f} "
                f"SL {sig.stop_loss:.2f} TP {sig.take_profit:.2f} ({sig.detail})"
            )

            if not config["mode"].startswith("Auto"):
                continue  # Trade Assistant mode: alert only, never trade

            if broker.has_open_position(symbol):
                self.log("  -> not traded: a position is already open")
                continue
            if self.gate is not None and not self.gate.can_trade():
                reason = "halted (too many losses in a row)" if self.gate.halted else "cooling down after a loss"
                self.log(f"  -> not traded: {reason}")
                continue

            result = broker.place_order(OrderRequest(
                symbol=symbol, direction=sig.direction, volume=config["volume"],
                entry=sig.entry, stop_loss=sig.stop_loss, take_profit=sig.take_profit,
                comment=sig.strategy,
            ))
            self.log(f"  -> order {'accepted' if result.accepted else 'REJECTED: ' + result.message}")

        return current_bar_time

    def _run(self, config: dict, data_source, broker: Broker) -> None:
        last_bar_time: Optional[str] = None
        self.log(f"Started: {config['strategy']} / {config['mode']} on {config['symbol']} {config['timeframe']}")
        while not self._stop_event.is_set():
            try:
                last_bar_time = self.run_once(config, data_source, broker, last_bar_time)
            except Exception as exc:  # a live loop must not die silently on one bad tick
                self.log(f"ERROR: {exc}")
            self._stop_event.wait(config.get("poll_seconds", 5))
        self.log("Stopped.")
