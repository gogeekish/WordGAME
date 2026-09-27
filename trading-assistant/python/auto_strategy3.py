"""Strategy 3 - Equal-Wick candle + Sweep After, Auto Trade version.

Same detection as strategy3_wick_sweep_after.py, but instead of only
alerting, each confirmed signal is turned into a real order through a
Broker. Only one position is opened at a time per symbol - once it
closes, the next qualifying signal is free to trade again (the "reboot").
"""

from typing import List

from broker import Broker, OrderRequest
from levels import fixed_distance_levels
from strategy3_wick_sweep_after import Candle, Signal, find_signals


def evaluate_and_trade(
    candles: List[Candle],
    broker: Broker,
    symbol: str,
    volume: float,
    stop_distance: float,
    reward_multiple: float = 2.0,
    lookback: int = 20,
    tolerance_ratio: float = 0.15,
    max_wait_bars: int = 10,
) -> List[Signal]:
    """Finds every Strategy 3 signal and, for each one, places a trade
    ONLY if no position is currently open for `symbol`. Returns the
    signals that were actually traded, in order."""
    if stop_distance <= 0:
        raise ValueError("stop_distance must be positive")

    traded: List[Signal] = []
    for signal in find_signals(candles, lookback, tolerance_ratio, max_wait_bars):
        if broker.has_open_position(symbol):
            continue  # already in a trade - wait for it to close before trading again

        stop_loss, take_profit = fixed_distance_levels(
            signal.direction, signal.entry_price, stop_distance, reward_multiple
        )

        result = broker.place_order(OrderRequest(
            symbol=symbol,
            direction=signal.direction,
            volume=volume,
            entry=signal.entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment="Strategy3 auto",
        ))
        if result.accepted:
            traded.append(signal)

    return traded


if __name__ == "__main__":
    from broker import FakeBroker

    sample = [
        Candle("t0", 99.0, 100.0, 98.0, 99.5),
        Candle("t1", 99.5, 101.0, 99.0, 100.5),
        Candle("t2", 100.5, 102.0, 100.0, 101.5),
        Candle("t3", 101.5, 102.3, 100.7, 101.5),
        Candle("t4", 101.4, 101.8, 101.0, 101.4),
        Candle("t5", 101.4, 103.0, 101.3, 101.9),
    ]
    broker = FakeBroker()
    traded = evaluate_and_trade(
        sample, broker, symbol="XAUUSD", volume=0.01, stop_distance=1.0,
        lookback=3, tolerance_ratio=0.2, max_wait_bars=5,
    )
    print(f"Trades placed: {len(traded)}")
    for order in broker.orders:
        print(
            f"  {order.direction} {order.symbol} vol={order.volume} entry={order.entry:.2f} "
            f"SL={order.stop_loss:.2f} TP={order.take_profit:.2f}"
        )
