"""Strategy 1 - Sweep + Equal-Wick candle, alert-only trade assistant.

Rule:
1. Track the most recent swing high and swing low over a lookback window.
2. Wait for a candle to sweep one of those levels: its wick pokes past the
   level but its close snaps back on the other side.
3. On the very next candle, check whether its upper wick and lower wick
   are about the same length.
4. If both conditions hold, raise a signal. This module never places a
   trade - it only detects and reports.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


@dataclass
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if not (self.low <= self.open <= self.high):
            raise ValueError(f"candle {self.time}: open must be between low and high")
        if not (self.low <= self.close <= self.high):
            raise ValueError(f"candle {self.time}: close must be between low and high")
        if self.low > self.high:
            raise ValueError(f"candle {self.time}: low must not exceed high")


@dataclass
class Signal:
    time: str
    direction: str  # "bullish" or "bearish"
    sweep_time: str
    entry_price: float
    upper_wick: float
    lower_wick: float


def swing_high(candles: List[Candle], end_index: int, lookback: int) -> float:
    start = max(0, end_index - lookback)
    return max(c.high for c in candles[start:end_index])


def swing_low(candles: List[Candle], end_index: int, lookback: int) -> float:
    start = max(0, end_index - lookback)
    return min(c.low for c in candles[start:end_index])


def detect_sweep(candle: Candle, level_high: float, level_low: float) -> Optional[str]:
    """Return "bearish" if the candle swept the high and closed back below
    it, "bullish" if it swept the low and closed back above it, else None."""
    if candle.high > level_high and candle.close < level_high:
        return "bearish"
    if candle.low < level_low and candle.close > level_low:
        return "bullish"
    return None


def wicks(candle: Candle) -> Tuple[float, float]:
    body_top = max(candle.open, candle.close)
    body_bottom = min(candle.open, candle.close)
    upper = candle.high - body_top
    lower = body_bottom - candle.low
    return upper, lower


def is_equal_wick(candle: Candle, tolerance_ratio: float) -> bool:
    upper, lower = wicks(candle)
    candle_range = candle.high - candle.low
    if candle_range <= 0:
        return False
    return abs(upper - lower) <= tolerance_ratio * candle_range


def find_signals(
    candles: List[Candle],
    lookback: int = 20,
    tolerance_ratio: float = 0.15,
) -> List[Signal]:
    """Scan a full list of candles and return every Strategy 1 signal found."""
    if lookback < 1:
        raise ValueError("lookback must be at least 1")
    if not 0 <= tolerance_ratio <= 1:
        raise ValueError("tolerance_ratio must be between 0 and 1")

    signals: List[Signal] = []
    pending_direction: Optional[str] = None
    pending_sweep_time: Optional[str] = None

    for i in range(lookback, len(candles)):
        candle = candles[i]

        if pending_direction is not None:
            if is_equal_wick(candle, tolerance_ratio):
                upper, lower = wicks(candle)
                signals.append(Signal(
                    time=candle.time,
                    direction=pending_direction,
                    sweep_time=pending_sweep_time,
                    entry_price=candle.close,
                    upper_wick=upper,
                    lower_wick=lower,
                ))
            pending_direction = None
            pending_sweep_time = None
            continue

        level_high = swing_high(candles, i, lookback)
        level_low = swing_low(candles, i, lookback)
        direction = detect_sweep(candle, level_high, level_low)
        if direction is not None:
            pending_direction = direction
            pending_sweep_time = candle.time

    return signals


def run_alert_assistant(
    candles: List[Candle],
    on_signal: Callable[[Signal], None],
    lookback: int = 20,
    tolerance_ratio: float = 0.15,
) -> None:
    """Trade-assistant entry point: finds signals and hands each one to
    on_signal. Never places trades - the caller decides what to do."""
    for signal in find_signals(candles, lookback, tolerance_ratio):
        on_signal(signal)


if __name__ == "__main__":
    # Smoke test: a recent swing high near 103, a candle that sweeps above
    # it and closes back below (bearish sweep), then a candle with equal
    # upper/lower wicks right after -> should produce one bearish signal.
    sample = [
        Candle("t0", 99.0, 100.0, 98.0, 99.5),
        Candle("t1", 99.5, 101.0, 99.0, 100.5),
        Candle("t2", 100.5, 103.0, 100.0, 102.5),
        Candle("t3", 102.5, 106.0, 101.5, 101.8),   # sweeps above 103, closes back below
        Candle("t4", 101.8, 102.6, 101.0, 101.8),   # upper wick 0.8, lower wick 0.8
    ]

    def print_signal(signal: Signal) -> None:
        print(
            f"[ALERT] {signal.direction} setup at {signal.time} "
            f"(swept at {signal.sweep_time}), entry ~{signal.entry_price:.2f}, "
            f"upper wick {signal.upper_wick:.2f}, lower wick {signal.lower_wick:.2f}"
        )

    run_alert_assistant(sample, print_signal, lookback=3, tolerance_ratio=0.2)
