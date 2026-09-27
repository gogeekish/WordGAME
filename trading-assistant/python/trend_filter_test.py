"""Trend filter test: only take a signal if its direction agrees with a
longer-period moving-average trend, and see whether that actually
helps - changing ONE thing at a time (just the filter, not also
re-tuning every other parameter) so any improvement can be credited to
the filter itself, not to a fresh round of overfitting.

Uses default, untuned parameters for Strategy 1 / Strategy 3 (the same
defaults backtest.py uses) and the same train/test split as tune.py:
first 70% of 60 days of real GC=F 15-minute candles to look at, last
30% to check honestly. Every moving-average period is reported on both
slices side by side - if the filter has a real effect, both slices
should broadly agree; if only the training slice looks better, that's
the same overfitting pattern as before.
"""

from typing import List, Optional

import strategy1_sweep_wick as s1
import strategy3_wick_sweep_after as s3
from backtest import average_range, fetch_yahoo_candles, load_mt5_csv, simulate_outcome
from levels import fixed_distance_levels
from tune import score, split_train_test

DEFAULT_LOOKBACK = 20
DEFAULT_TOLERANCE_RATIO = 0.15
DEFAULT_STOP_MULT = 1.5
DEFAULT_REWARD_MULTIPLE = 2.0
MA_PERIODS = [20, 50, 100, 200]  # 5h, 12.5h, 25h, 50h of 15-minute bars


def sma(closes: List[float], end_index: int, period: int) -> Optional[float]:
    start = end_index - period + 1
    if start < 0:
        return None
    window = closes[start:end_index + 1]
    return sum(window) / len(window)


def trend_at(closes: List[float], index: int, period: int) -> Optional[str]:
    """"bullish" if price is above its own recent average (uptrend),
    "bearish" if below (downtrend), None if there isn't enough history
    yet or price sits exactly on the average."""
    avg = sma(closes, index, period)
    if avg is None:
        return None
    if closes[index] > avg:
        return "bullish"
    if closes[index] < avg:
        return "bearish"
    return None


def backtest_with_optional_trend_filter(
    find_signals_fn,
    candles: list,
    stop_distance: float,
    reward_multiple: float,
    ma_period: Optional[int],
    label: str,
) -> list:
    """Runs a strategy's own find_signals, optionally drops any signal
    that disagrees with the trend at that bar, then simulates each
    surviving signal forward exactly like backtest.py does."""
    time_to_index = {c.time: i for i, c in enumerate(candles)}
    closes = [c.close for c in candles]

    results = []
    for signal in find_signals_fn(candles, lookback=DEFAULT_LOOKBACK, tolerance_ratio=DEFAULT_TOLERANCE_RATIO):
        idx = time_to_index[signal.time]

        if ma_period is not None:
            trend = trend_at(closes, idx, ma_period)
            if trend is None or trend != signal.direction:
                continue  # filtered out - fighting the trend

        stop_loss, take_profit = fixed_distance_levels(
            signal.direction, signal.entry_price, stop_distance, reward_multiple
        )
        result = simulate_outcome(candles, idx, label, signal.direction, signal.entry_price, stop_loss, take_profit)
        result.entry_time = signal.time
        results.append(result)

    return results


def report_row(label: str, results: list) -> None:
    s = score(results, DEFAULT_REWARD_MULTIPLE, min_decided=0)
    if s is None or s["decided"] == 0:
        print(f"    {label:28s} 0 signals")
        return
    print(f"    {label:28s} {s['signals']:3d} signals, {s['decided']:3d} decided, "
          f"win rate {s['win_rate']:5.1f}%, expectancy {s['expectancy_r']:+.2f}R")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # python3 trend_filter_test.py path/to/your_mt5_export.csv
        csv_path = sys.argv[1]
        print(f"Loading real candles from your MT5 export: {csv_path}")
        all_candles = load_mt5_csv(csv_path, s1.Candle)
    else:
        print("No CSV path given - fetching 60 days of 15-minute GC=F candles from Yahoo Finance instead.")
        print("(For real XAUUSD: python3 trend_filter_test.py path/to/your_mt5_export.csv)")
        all_candles = fetch_yahoo_candles(s1.Candle, "GC=F", "60d", "15m")

    train, test = split_train_test(all_candles)
    print(f"Train: {len(train)} candles ({train[0].time} to {train[-1].time})")
    print(f"Test:  {len(test)} candles ({test[0].time} to {test[-1].time})\n")

    stop_distance_train = average_range(train) * DEFAULT_STOP_MULT
    stop_distance_test = average_range(test) * DEFAULT_STOP_MULT

    for strategy_name, find_signals_fn in [("Strategy 1 (sweep + equal-wick)", s1.find_signals),
                                            ("Strategy 3 (equal-wick + sweep-after)", s3.find_signals)]:
        print("=" * 78)
        print(strategy_name)
        print("=" * 78)

        print("  TRAIN:")
        report_row("no trend filter", backtest_with_optional_trend_filter(
            find_signals_fn, train, stop_distance_train, DEFAULT_REWARD_MULTIPLE, None, strategy_name))
        for period in MA_PERIODS:
            report_row(f"trend filter, MA={period}", backtest_with_optional_trend_filter(
                find_signals_fn, train, stop_distance_train, DEFAULT_REWARD_MULTIPLE, period, strategy_name))

        print("  TEST (unseen):")
        report_row("no trend filter", backtest_with_optional_trend_filter(
            find_signals_fn, test, stop_distance_test, DEFAULT_REWARD_MULTIPLE, None, strategy_name))
        for period in MA_PERIODS:
            report_row(f"trend filter, MA={period}", backtest_with_optional_trend_filter(
                find_signals_fn, test, stop_distance_test, DEFAULT_REWARD_MULTIPLE, period, strategy_name))
        print()
