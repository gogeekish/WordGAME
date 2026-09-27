"""Strategy 2 - BOS + FVG retest, Auto Trade version.

Same detection as strategy2_bos_fvg.py, but instead of only alerting,
each retest signal is turned into a real order through a Broker. Only
one position is opened at a time per symbol - once it closes, the next
qualifying signal is free to trade again (the "reboot").
"""

from typing import List

from broker import Broker, OrderRequest
from strategy2_bos_fvg import Candle, RetestSignal, find_signals


def evaluate_and_trade(
    candles: List[Candle],
    broker: Broker,
    symbol: str,
    volume: float,
    confirm_bars: int = 2,
    fvg_buffer_ratio: float = 0.25,
    reward_multiple: float = 2.0,
) -> List[RetestSignal]:
    """Finds every Strategy 2 signal and, for each one, places a trade
    ONLY if no position is currently open for `symbol`. Entry/SL/TP1 come
    straight from the signal; TP2 is used as the order's take-profit
    since it is the further, higher-conviction target. Returns the
    signals that were actually traded, in order."""
    traded: List[RetestSignal] = []
    for signal in find_signals(candles, confirm_bars, fvg_buffer_ratio, reward_multiple):
        if broker.has_open_position(symbol):
            continue  # already in a trade - wait for it to close before trading again

        result = broker.place_order(OrderRequest(
            symbol=symbol,
            direction=signal.direction,
            volume=volume,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit_2,
            comment="Strategy2 auto",
        ))
        if result.accepted:
            traded.append(signal)

    return traded


if __name__ == "__main__":
    from broker import FakeBroker

    sample = [
        Candle("t0", 99.0, 100.0, 98.0, 99.5),
        Candle("t1", 99.5, 101.0, 99.0, 100.5),
        Candle("t2", 100.5, 103.0, 100.0, 102.5),
        Candle("t3", 102.5, 102.8, 101.5, 102.0),
        Candle("t4", 102.0, 102.6, 101.8, 102.2),
        Candle("t5", 105.0, 108.0, 104.0, 107.5),
        Candle("t6", 107.5, 110.0, 107.0, 109.5),
        Candle("t7", 109.5, 109.8, 103.5, 104.5),
    ]
    broker = FakeBroker()
    traded = evaluate_and_trade(sample, broker, symbol="XAUUSD", volume=0.01)
    print(f"Trades placed: {len(traded)}")
    for order in broker.orders:
        print(
            f"  {order.direction} {order.symbol} vol={order.volume} entry={order.entry:.2f} "
            f"SL={order.stop_loss:.2f} TP={order.take_profit:.2f}"
        )
