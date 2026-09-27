"""Strategy 3 - Equal-wick candle first, confirmed by a liquidity sweep
afterward, alert-only trade assistant.

Rule (the reverse order of Strategy 1):
1. Watch every candle for an equal-wick candle, same measuring as
   Strategy 1 - but don't act on it yet, just remember it.
2. Keep watching the following candles for a sweep past a nearby high or
   low, in either direction.
3. The moment that follow-up sweep happens, the setup is confirmed.
4. If no sweep shows up within `max_wait_bars` candles, forget about that
   equal-wick candle and go back to watching for a new one.

This module never places a trade - it only detects and reports. It
reuses the swing-level and wick-measuring building blocks from Strategy 1
instead of duplicating them.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional

from strategy1_sweep_wick import (
    Candle,
    detect_sweep,
    is_equal_wick,
    swing_high,
    swing_low,
)


@dataclass
class Signal:
    time: str            # time of the confirming sweep candle
    direction: str        # "bullish" or "bearish" sweep direction
    candle_time: str      # time of the original equal-wick candle
    entry_price: float


def find_signals(
    candles: List[Candle],
    lookback: int = 20,
    tolerance_ratio: float = 0.15,
    max_wait_bars: int = 10,
) -> List[Signal]:
    """Scan a full list of candles and return every Strategy 3 signal found."""
    if lookback < 1:
        raise ValueError("lookback must be at least 1")
    if not 0 <= tolerance_ratio <= 1:
        raise ValueError("tolerance_ratio must be between 0 and 1")
    if max_wait_bars < 1:
        raise ValueError("max_wait_bars must be at least 1")

    signals: List[Signal] = []
    pending_candle_index: Optional[int] = None

    for i in range(lookback, len(candles)):
        candle = candles[i]

        if pending_candle_index is not None and (i - pending_candle_index) > max_wait_bars:
            pending_candle_index = None  # gave up waiting for a confirming sweep

        if pending_candle_index is not None:
            level_high = swing_high(candles, i, lookback)
            level_low = swing_low(candles, i, lookback)
            direction = detect_sweep(candle, level_high, level_low)
            if direction is not None:
                signals.append(Signal(
                    time=candle.time,
                    direction=direction,
                    candle_time=candles[pending_candle_index].time,
                    entry_price=candle.close,
                ))
                pending_candle_index = None
                continue

        if pending_candle_index is None and is_equal_wick(candle, tolerance_ratio):
            pending_candle_index = i

    return signals


def run_alert_assistant(
    candles: List[Candle],
    on_signal: Callable[[Signal], None],
    lookback: int = 20,
    tolerance_ratio: float = 0.15,
    max_wait_bars: int = 10,
) -> None:
    """Trade-assistant entry point: finds signals and hands each one to
    on_signal. Never places trades - the caller decides what to do."""
    for signal in find_signals(candles, lookback, tolerance_ratio, max_wait_bars):
        on_signal(signal)


if __name__ == "__main__":
    # Smoke test: an equal-wick candle forms at t3, then two quiet candles,
    # then a candle that sweeps above the recent high and closes back
    # below it -> one bearish signal confirmed two bars after the candle.
    sample = [
        Candle("t0", 99.0, 100.0, 98.0, 99.5),
        Candle("t1", 99.5, 101.0, 99.0, 100.5),
        Candle("t2", 100.5, 102.0, 100.0, 101.5),
        Candle("t3", 101.5, 102.3, 100.7, 101.5),   # equal wicks: 0.8 / 0.8
        Candle("t4", 101.4, 101.8, 101.0, 101.4),   # quiet, no sweep
        Candle("t5", 101.4, 103.0, 101.3, 101.9),   # sweeps above ~102.3, closes back below
    ]

    def print_signal(signal: Signal) -> None:
        print(
            f"[ALERT] {signal.direction} setup confirmed at {signal.time} "
            f"(candle formed at {signal.candle_time}), entry ~{signal.entry_price:.2f}"
        )

    run_alert_assistant(sample, print_signal, lookback=3, tolerance_ratio=0.2, max_wait_bars=5)
