"""Strategy 1 - Sweep + Equal-Wick candle, Auto Trade version.

Same detection as strategy1_sweep_wick.py, but instead of only alerting,
each signal is turned into a real order through a Broker. Only one
position is opened at a time per symbol - once it closes, the next
qualifying signal is free to trade again (the "reboot").

Walks the candles one bar at a time (not signal-by-signal) so an
optional RiskGate can count bars for its cooldown, and each bar polls
broker.pop_closed_outcomes() to learn how the last trade actually
ended - in real trading that comes from the broker (Mt5Broker reads
your account's trade history), not from anything this script simulates
itself.

InpStopDistance/reward_multiple below are simple, symbol-agnostic
placeholders you tune per market - this script makes no claim about what
distance is "correct" for any particular symbol or timeframe.
"""

from typing import List, Optional

from broker import Broker, OrderRequest
from levels import fixed_distance_levels
from risk_gate import RiskGate
from strategy1_sweep_wick import Candle, Signal, find_signals


def evaluate_and_trade(
    candles: List[Candle],
    broker: Broker,
    symbol: str,
    volume: float,
    stop_distance: float,
    reward_multiple: float = 2.0,
    lookback: int = 20,
    tolerance_ratio: float = 0.15,
    gate: Optional[RiskGate] = None,
) -> List[Signal]:
    """Finds every Strategy 1 signal and, walking bar by bar, places a
    trade ONLY if no position is open AND (when a gate is given) the
    gate currently allows it. Returns the signals that were actually
    traded, in order. Pass no gate to get the old reboot-only behavior
    (rearm the instant a position closes, no cooldown or loss limit)."""
    if stop_distance <= 0:
        raise ValueError("stop_distance must be positive")

    signals_by_time = {s.time: s for s in find_signals(candles, lookback, tolerance_ratio)}
    traded: List[Signal] = []

    for candle in candles[lookback:]:
        if gate is not None:
            gate.advance_bar()
            for outcome in broker.pop_closed_outcomes(symbol):
                gate.record_outcome(outcome)

        if broker.has_open_position(symbol):
            continue
        if gate is not None and not gate.can_trade():
            continue

        signal = signals_by_time.get(candle.time)
        if signal is None:
            continue

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
            comment="Strategy1 auto",
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
        Candle("t3", 102.5, 106.0, 101.5, 101.8),
        Candle("t4", 101.8, 102.6, 101.0, 101.8),
    ]
    broker = FakeBroker()
    gate = RiskGate(cooldown_bars=5, max_consecutive_losses=3)
    traded = evaluate_and_trade(
        sample, broker, symbol="XAUUSD", volume=0.01, stop_distance=1.0,
        lookback=3, tolerance_ratio=0.2, gate=gate,
    )
    print(f"Trades placed: {len(traded)}")
    for order in broker.orders:
        print(
            f"  {order.direction} {order.symbol} vol={order.volume} entry={order.entry:.2f} "
            f"SL={order.stop_loss:.2f} TP={order.take_profit:.2f}"
        )
