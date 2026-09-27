"""Strategy 2 - BOS + FVG retest, alert-only trade assistant.

Rule:
1. Track swing highs/lows with a simple fractal: a bar is confirmed as a
   swing high once `confirm_bars` bars on both sides all have a lower high
   (mirrored for a swing low).
2. A Break of Structure (BOS) happens when a bar's close moves past the
   most recently confirmed swing high (bullish) or swing low (bearish).
3. On the BOS bar, look for a classic 3-candle Fair Value Gap: a gap
   between the BOS bar and the bar two candles before it.
4. Track the highest high (bullish) / lowest low (bearish) reached since
   the BOS - that becomes the first take-profit target.
5. Once price comes back and touches the FVG zone, raise a retest signal
   with entry / stop-loss / take-profit levels. This module never places
   a trade - it only detects and reports.

Simplification worth knowing: the FVG is only checked using the exact
3-candle pattern ending on the BOS bar itself, not a wider search window.
A very fast multi-candle breakout might leave its gap a bar or two later
than that - this module will miss those.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional


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
class FVG:
    direction: str  # "bullish" or "bearish"
    top: float
    bottom: float
    formed_at: str


@dataclass
class RetestSignal:
    time: str
    direction: str
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float


def find_fvg_at_bos(candles: List[Candle], bos_index: int, direction: str) -> Optional[FVG]:
    """Check the exact 3-candle pattern ending at bos_index for a gap."""
    if bos_index < 2:
        return None
    a, c = candles[bos_index - 2], candles[bos_index]
    if direction == "bullish" and a.high < c.low:
        return FVG("bullish", top=c.low, bottom=a.high, formed_at=c.time)
    if direction == "bearish" and a.low > c.high:
        return FVG("bearish", top=a.low, bottom=c.high, formed_at=c.time)
    return None


def _is_confirmed_swing_high(candles: List[Candle], index: int, confirm_bars: int) -> bool:
    left = candles[index - confirm_bars:index]
    right = candles[index + 1:index + 1 + confirm_bars]
    peak = candles[index].high
    return all(c.high < peak for c in left) and all(c.high < peak for c in right)


def _is_confirmed_swing_low(candles: List[Candle], index: int, confirm_bars: int) -> bool:
    left = candles[index - confirm_bars:index]
    right = candles[index + 1:index + 1 + confirm_bars]
    trough = candles[index].low
    return all(c.low > trough for c in left) and all(c.low > trough for c in right)


def find_signals(
    candles: List[Candle],
    confirm_bars: int = 2,
    fvg_buffer_ratio: float = 0.25,
    reward_multiple: float = 2.0,
) -> List[RetestSignal]:
    """Scan a full list of candles and return every Strategy 2 signal found."""
    if confirm_bars < 1:
        raise ValueError("confirm_bars must be at least 1")
    if fvg_buffer_ratio < 0:
        raise ValueError("fvg_buffer_ratio must not be negative")
    if reward_multiple <= 0:
        raise ValueError("reward_multiple must be positive")

    last_swing_high: Optional[float] = None
    last_swing_low: Optional[float] = None

    active_fvg: Optional[FVG] = None
    impulse_extreme: Optional[float] = None
    bos_direction: Optional[str] = None

    signals: List[RetestSignal] = []

    for j in range(2 * confirm_bars, len(candles)):
        candidate_idx = j - confirm_bars
        if _is_confirmed_swing_high(candles, candidate_idx, confirm_bars):
            last_swing_high = candles[candidate_idx].high
        if _is_confirmed_swing_low(candles, candidate_idx, confirm_bars):
            last_swing_low = candles[candidate_idx].low

        candle = candles[j]

        # Track the extreme of the move since a BOS, until the FVG is retested.
        if active_fvg is not None:
            if bos_direction == "bullish":
                impulse_extreme = max(impulse_extreme, candle.high)
                touched = candle.low <= active_fvg.top and candle.high >= active_fvg.bottom
            else:
                impulse_extreme = min(impulse_extreme, candle.low)
                touched = candle.high >= active_fvg.bottom and candle.low <= active_fvg.top

            if touched:
                buffer = (active_fvg.top - active_fvg.bottom) * fvg_buffer_ratio
                if bos_direction == "bullish":
                    entry = active_fvg.top
                    stop_loss = active_fvg.bottom - buffer
                    take_profit_1 = impulse_extreme
                else:
                    entry = active_fvg.bottom
                    stop_loss = active_fvg.top + buffer
                    take_profit_1 = impulse_extreme
                reward_leg = abs(take_profit_1 - entry)
                take_profit_2 = (
                    entry + reward_multiple * reward_leg
                    if bos_direction == "bullish"
                    else entry - reward_multiple * reward_leg
                )
                signals.append(RetestSignal(
                    time=candle.time,
                    direction=bos_direction,
                    entry=entry,
                    stop_loss=stop_loss,
                    take_profit_1=take_profit_1,
                    take_profit_2=take_profit_2,
                ))
                active_fvg = None
                impulse_extreme = None
                bos_direction = None
            continue

        if last_swing_high is not None and candle.close > last_swing_high:
            fvg = find_fvg_at_bos(candles, j, "bullish")
            if fvg is not None:
                active_fvg = fvg
                impulse_extreme = candle.high
                bos_direction = "bullish"
            last_swing_high = None
        elif last_swing_low is not None and candle.close < last_swing_low:
            fvg = find_fvg_at_bos(candles, j, "bearish")
            if fvg is not None:
                active_fvg = fvg
                impulse_extreme = candle.low
                bos_direction = "bearish"
            last_swing_low = None

    return signals


def run_alert_assistant(
    candles: List[Candle],
    on_signal: Callable[[RetestSignal], None],
    confirm_bars: int = 2,
    fvg_buffer_ratio: float = 0.25,
    reward_multiple: float = 2.0,
) -> None:
    """Trade-assistant entry point: finds signals and hands each one to
    on_signal. Never places trades - the caller decides what to do."""
    for signal in find_signals(candles, confirm_bars, fvg_buffer_ratio, reward_multiple):
        on_signal(signal)


if __name__ == "__main__":
    # Smoke test: a swing high forms near 103, a breakout candle closes
    # above it while leaving a gap behind (102.8 -> 104.0), price runs
    # further to 110, then retraces into the gap -> one bullish signal.
    sample = [
        Candle("t0", 99.0, 100.0, 98.0, 99.5),
        Candle("t1", 99.5, 101.0, 99.0, 100.5),
        Candle("t2", 100.5, 103.0, 100.0, 102.5),   # swing high candidate (103)
        Candle("t3", 102.5, 102.8, 101.5, 102.0),   # right-confirm bar 1 (high 102.8 < 103)
        Candle("t4", 102.0, 102.6, 101.8, 102.2),   # right-confirm bar 2 (high 102.6 < 103)
        Candle("t5", 105.0, 108.0, 104.0, 107.5),   # BOS (close 107.5 > 103), gap vs t3's high
        Candle("t6", 107.5, 110.0, 107.0, 109.5),   # impulse extends to 110
        Candle("t7", 109.5, 109.8, 103.5, 104.5),   # retraces into the 102.8-104.0 gap
    ]

    def print_signal(signal: RetestSignal) -> None:
        print(
            f"[ALERT] {signal.direction} retest at {signal.time}: "
            f"entry {signal.entry:.2f}, SL {signal.stop_loss:.2f}, "
            f"TP1 {signal.take_profit_1:.2f}, TP2 {signal.take_profit_2:.2f}"
        )

    run_alert_assistant(sample, print_signal, confirm_bars=2)
