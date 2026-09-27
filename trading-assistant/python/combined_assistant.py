"""All Combined - Trade Assistant version.

Runs Strategy 1, Strategy 2, and Strategy 3's detectors over the same
candle history and reports every signal from all three, each one tagged
with which strategy raised it. This module never places a trade - it
only detects and reports.
"""

from dataclasses import dataclass
from typing import Callable, List

import strategy1_sweep_wick as s1
import strategy2_bos_fvg as s2
import strategy3_wick_sweep_after as s3


@dataclass
class TaggedSignal:
    strategy: str  # "Strategy 1", "Strategy 2", or "Strategy 3"
    time: str
    direction: str
    detail: str  # a short human-readable summary specific to that strategy


def find_all_signals(
    candles_s1: List[s1.Candle],
    candles_s2: List[s2.Candle],
    candles_s3: List[s3.Candle],
    s1_lookback: int = 20,
    s1_tolerance_ratio: float = 0.15,
    s2_confirm_bars: int = 2,
    s2_fvg_buffer_ratio: float = 0.25,
    s2_reward_multiple: float = 2.0,
    s3_lookback: int = 20,
    s3_tolerance_ratio: float = 0.15,
    s3_max_wait_bars: int = 10,
) -> List[TaggedSignal]:
    """Runs all three detectors and returns every signal, tagged by
    strategy, sorted by time. The three candle lists are accepted
    separately because each strategy module defines its own Candle type
    (they happen to have the same shape, but are not the same class).
    Each strategy's own tuning parameters are passed straight through -
    there is no single "lookback" that fits all three."""
    tagged: List[TaggedSignal] = []

    for signal in s1.find_signals(candles_s1, s1_lookback, s1_tolerance_ratio):
        tagged.append(TaggedSignal(
            strategy="Strategy 1",
            time=signal.time,
            direction=signal.direction,
            detail=f"sweep at {signal.sweep_time}, entry ~{signal.entry_price:.2f}",
        ))

    for signal in s2.find_signals(candles_s2, s2_confirm_bars, s2_fvg_buffer_ratio, s2_reward_multiple):
        tagged.append(TaggedSignal(
            strategy="Strategy 2",
            time=signal.time,
            direction=signal.direction,
            detail=(
                f"entry {signal.entry:.2f}, SL {signal.stop_loss:.2f}, "
                f"TP1 {signal.take_profit_1:.2f}, TP2 {signal.take_profit_2:.2f}"
            ),
        ))

    for signal in s3.find_signals(candles_s3, s3_lookback, s3_tolerance_ratio, s3_max_wait_bars):
        tagged.append(TaggedSignal(
            strategy="Strategy 3",
            time=signal.time,
            direction=signal.direction,
            detail=f"candle formed at {signal.candle_time}, entry ~{signal.entry_price:.2f}",
        ))

    tagged.sort(key=lambda t: t.time)
    return tagged


def run_alert_assistant(
    candles_s1: List[s1.Candle],
    candles_s2: List[s2.Candle],
    candles_s3: List[s3.Candle],
    on_signal: Callable[[TaggedSignal], None],
    **detector_kwargs,
) -> None:
    """Trade-assistant entry point: finds signals from all three
    strategies and hands each one to on_signal. Never places trades.
    detector_kwargs are forwarded to find_all_signals (e.g. s1_lookback)."""
    for signal in find_all_signals(candles_s1, candles_s2, candles_s3, **detector_kwargs):
        on_signal(signal)


if __name__ == "__main__":
    # Reuse each strategy's own smoke-test candles so this demo is
    # guaranteed to produce one signal from each strategy.
    sample_s1 = [
        s1.Candle("t0", 99.0, 100.0, 98.0, 99.5),
        s1.Candle("t1", 99.5, 101.0, 99.0, 100.5),
        s1.Candle("t2", 100.5, 103.0, 100.0, 102.5),
        s1.Candle("t3", 102.5, 106.0, 101.5, 101.8),
        s1.Candle("t4", 101.8, 102.6, 101.0, 101.8),
    ]
    sample_s2 = [
        s2.Candle("t0", 99.0, 100.0, 98.0, 99.5),
        s2.Candle("t1", 99.5, 101.0, 99.0, 100.5),
        s2.Candle("t2", 100.5, 103.0, 100.0, 102.5),
        s2.Candle("t3", 102.5, 102.8, 101.5, 102.0),
        s2.Candle("t4", 102.0, 102.6, 101.8, 102.2),
        s2.Candle("t5", 105.0, 108.0, 104.0, 107.5),
        s2.Candle("t6", 107.5, 110.0, 107.0, 109.5),
        s2.Candle("t7", 109.5, 109.8, 103.5, 104.5),
    ]
    sample_s3 = [
        s3.Candle("t0", 99.0, 100.0, 98.0, 99.5),
        s3.Candle("t1", 99.5, 101.0, 99.0, 100.5),
        s3.Candle("t2", 100.5, 102.0, 100.0, 101.5),
        s3.Candle("t3", 101.5, 102.3, 100.7, 101.5),
        s3.Candle("t4", 101.4, 101.8, 101.0, 101.4),
        s3.Candle("t5", 101.4, 103.0, 101.3, 101.9),
    ]

    def print_signal(signal: TaggedSignal) -> None:
        print(f"[ALERT] {signal.strategy} - {signal.direction} at {signal.time}: {signal.detail}")

    run_alert_assistant(
        sample_s1, sample_s2, sample_s3, print_signal,
        s1_lookback=3, s1_tolerance_ratio=0.2,
        s3_lookback=3, s3_tolerance_ratio=0.2, s3_max_wait_bars=5,
    )
