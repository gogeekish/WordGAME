"""Parameter tuning with an honest train/test split.

Tuning and testing on the SAME data is a classic trap: if you try
enough parameter combinations, some will look great purely by chance,
even if the strategy has no real edge. This script tunes each
strategy's parameters on an older "training" slice of real candles,
then checks the winning settings on a separate, newer "test" slice the
tuning never saw - that's the only honest way to tell "better" from
"got lucky on this one grid search."

Data: 60 days of real 15-minute Gold futures candles (GC=F) from Yahoo
Finance, split chronologically: the first 70% is train, the last 30%
is test. Same proxy-symbol caveat as backtest.py applies.
"""

from itertools import product
from typing import Callable, List

import strategy1_sweep_wick as s1
import strategy2_bos_fvg as s2
import strategy3_wick_sweep_after as s3
from backtest import (
    TradeResult,
    average_range,
    backtest_strategy1,
    backtest_strategy2,
    backtest_strategy3,
    fetch_yahoo_candles,
)


def split_train_test(candles: list, train_fraction: float = 0.7):
    cut = int(len(candles) * train_fraction)
    return candles[:cut], candles[cut:]


def score(results: List[TradeResult], reward_multiple: float, min_decided: int) -> dict:
    """Win rate and expectancy (in units of risk, R) for one run. Returns
    None-ish (decided=0) if there weren't enough decided trades to judge."""
    wins = sum(1 for r in results if r.outcome == "win")
    losses = sum(1 for r in results if r.outcome == "loss")
    decided = wins + losses
    if decided < min_decided:
        return None
    win_rate = wins / decided * 100
    expectancy_r = (wins * reward_multiple - losses) / decided
    return {
        "signals": len(results), "wins": wins, "losses": losses,
        "decided": decided, "win_rate": win_rate, "expectancy_r": expectancy_r,
    }


def tune_strategy1_or_3(
    backtest_fn: Callable, candles: list, avg_range: float, min_decided: int,
) -> list:
    grid = product(
        [10, 20, 30],            # lookback
        [0.10, 0.15, 0.20, 0.25],  # tolerance_ratio
        [1.0, 1.5, 2.0],          # stop distance, as a multiple of avg_range
        [1.0, 1.5, 2.0, 3.0],      # reward_multiple
    )
    scored = []
    for lookback, tolerance_ratio, stop_mult, reward_multiple in grid:
        stop_distance = avg_range * stop_mult
        results = backtest_fn(
            candles, stop_distance=stop_distance, reward_multiple=reward_multiple,
            lookback=lookback, tolerance_ratio=tolerance_ratio,
        )
        s = score(results, reward_multiple, min_decided)
        if s is not None:
            scored.append({
                "params": dict(lookback=lookback, tolerance_ratio=tolerance_ratio,
                                stop_mult=stop_mult, reward_multiple=reward_multiple),
                **s,
            })
    scored.sort(key=lambda r: r["expectancy_r"], reverse=True)
    return scored


def tune_strategy2(candles: list, min_decided: int) -> list:
    grid = product(
        [1, 2, 3, 4],        # confirm_bars
        [0.10, 0.25, 0.40],  # fvg_buffer_ratio
        [1.0, 1.5, 2.0, 3.0],  # reward_multiple
    )
    scored = []
    for confirm_bars, fvg_buffer_ratio, reward_multiple in grid:
        results = backtest_strategy2(
            candles, confirm_bars=confirm_bars,
            fvg_buffer_ratio=fvg_buffer_ratio, reward_multiple=reward_multiple,
        )
        s = score(results, reward_multiple, min_decided)
        if s is not None:
            scored.append({
                "params": dict(confirm_bars=confirm_bars, fvg_buffer_ratio=fvg_buffer_ratio,
                                reward_multiple=reward_multiple),
                **s,
            })
    scored.sort(key=lambda r: r["expectancy_r"], reverse=True)
    return scored


def print_top(label: str, scored: list, n: int = 3) -> None:
    print(f"  Top {min(n, len(scored))} by expectancy on TRAIN (of {len(scored)} combos with enough trades):")
    if not scored:
        print("    None had enough decided trades - grid or min_decided needs adjusting.")
        return
    for row in scored[:n]:
        print(f"    {row['params']}")
        print(f"      train: {row['decided']} decided, win rate {row['win_rate']:.1f}%, expectancy {row['expectancy_r']:+.2f}R")


def evaluate_on_test(label: str, backtest_fn: Callable, test_candles: list, params: dict, avg_range_train: float) -> None:
    kwargs = dict(params)
    reward_multiple = kwargs.pop("reward_multiple")
    stop_mult = kwargs.pop("stop_mult", None)
    if stop_mult is not None:
        kwargs["stop_distance"] = avg_range_train * stop_mult
    kwargs["reward_multiple"] = reward_multiple

    results = backtest_fn(test_candles, **kwargs)
    s = score(results, reward_multiple, min_decided=0)
    if s is None or s["decided"] == 0:
        print(f"  {label}: no decided trades on the unseen test slice - can't judge it there.")
        return
    print(f"  {label}: test: {s['decided']} decided, win rate {s['win_rate']:.1f}%, expectancy {s['expectancy_r']:+.2f}R")


if __name__ == "__main__":
    print("Fetching 60 days of real 15-minute GC=F candles from Yahoo Finance...")
    all_s1 = fetch_yahoo_candles(s1.Candle, "GC=F", "60d", "15m")
    all_s2 = fetch_yahoo_candles(s2.Candle, "GC=F", "60d", "15m")

    train_s1, test_s1 = split_train_test(all_s1)
    train_s2, test_s2 = split_train_test(all_s2)
    print(f"Train: {len(train_s1)} candles ({train_s1[0].time} to {train_s1[-1].time})")
    print(f"Test:  {len(test_s1)} candles ({test_s1[0].time} to {test_s1[-1].time}) - tuning never sees this slice\n")

    avg_range_train = average_range(train_s1)

    print("=" * 70)
    print("STRATEGY 1 (sweep + equal-wick)")
    print("=" * 70)
    default_train = score(
        backtest_strategy1(train_s1, stop_distance=avg_range_train * 1.5, reward_multiple=2.0, lookback=20, tolerance_ratio=0.15),
        2.0, min_decided=0,
    )
    print(f"  Default params on TRAIN: {default_train}")
    scored1 = tune_strategy1_or_3(backtest_strategy1, train_s1, avg_range_train, min_decided=10)
    print_top("Strategy 1", scored1)
    if scored1:
        best = scored1[0]["params"]
        evaluate_on_test("Best-on-train params", backtest_strategy1, test_s1, best, avg_range_train)
    print()

    print("=" * 70)
    print("STRATEGY 2 (BOS + FVG retest)")
    print("=" * 70)
    default_train2 = score(
        backtest_strategy2(train_s2, confirm_bars=2, fvg_buffer_ratio=0.25, reward_multiple=2.0),
        2.0, min_decided=0,
    )
    print(f"  Default params on TRAIN: {default_train2}")
    scored2 = tune_strategy2(train_s2, min_decided=5)
    print_top("Strategy 2", scored2)
    if scored2:
        best2 = scored2[0]["params"]
        evaluate_on_test("Best-on-train params", backtest_strategy2, test_s2, best2, avg_range_train)
    print()

    print("=" * 70)
    print("STRATEGY 3 (equal-wick + sweep after)")
    print("=" * 70)
    default_train3 = score(
        backtest_strategy3(train_s1, stop_distance=avg_range_train * 1.5, reward_multiple=2.0, lookback=20, tolerance_ratio=0.15),
        2.0, min_decided=0,
    )
    print(f"  Default params on TRAIN: {default_train3}")
    scored3 = tune_strategy1_or_3(backtest_strategy3, train_s1, avg_range_train, min_decided=10)
    print_top("Strategy 3", scored3)
    if scored3:
        best3 = scored3[0]["params"]
        evaluate_on_test("Best-on-train params", backtest_strategy3, test_s1, best3, avg_range_train)
