"""All Combined - Auto Trade version.

Runs Strategy 1, Strategy 2, and Strategy 3's detectors over the same
candle history. Whichever signal comes first (in time) gets traded,
using that strategy's own entry/SL/TP rule. Only one position is open
at a time across all three strategies - once it closes, the next
qualifying signal from any strategy is free to trade again (the
"reboot").

Walks candles_s1 one bar at a time as the shared clock (the three
candle lists are expected to be the same underlying market data - see
the "Can These Live in One App?" section of the strategy notebook) so
an optional RiskGate can count bars for its cooldown, and each bar
polls broker.pop_closed_outcomes() to learn how the last trade actually
ended. One gate covers all three strategies together, matching "one
robot managing trades from any of the three."
"""

from dataclasses import dataclass
from typing import List, Optional

import strategy1_sweep_wick as s1
import strategy2_bos_fvg as s2
import strategy3_wick_sweep_after as s3
from broker import Broker, OrderRequest
from levels import fixed_distance_levels
from risk_gate import RiskGate


@dataclass
class TaggedOrder:
    strategy: str
    time: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float


def _s1_orders(
    candles: List[s1.Candle], stop_distance: float, reward_multiple: float,
    lookback: int = 20, tolerance_ratio: float = 0.15,
) -> List[TaggedOrder]:
    orders = []
    for signal in s1.find_signals(candles, lookback, tolerance_ratio):
        sl, tp = fixed_distance_levels(signal.direction, signal.entry_price, stop_distance, reward_multiple)
        orders.append(TaggedOrder("Strategy 1", signal.time, signal.direction, signal.entry_price, sl, tp))
    return orders


def _s2_orders(
    candles: List[s2.Candle],
    confirm_bars: int = 2, fvg_buffer_ratio: float = 0.25, s2_reward_multiple: float = 2.0,
) -> List[TaggedOrder]:
    orders = []
    for signal in s2.find_signals(candles, confirm_bars, fvg_buffer_ratio, s2_reward_multiple):
        orders.append(TaggedOrder(
            "Strategy 2", signal.time, signal.direction,
            signal.entry, signal.stop_loss, signal.take_profit_2,
        ))
    return orders


def _s3_orders(
    candles: List[s3.Candle], stop_distance: float, reward_multiple: float,
    lookback: int = 20, tolerance_ratio: float = 0.15, max_wait_bars: int = 10,
) -> List[TaggedOrder]:
    orders = []
    for signal in s3.find_signals(candles, lookback, tolerance_ratio, max_wait_bars):
        sl, tp = fixed_distance_levels(signal.direction, signal.entry_price, stop_distance, reward_multiple)
        orders.append(TaggedOrder("Strategy 3", signal.time, signal.direction, signal.entry_price, sl, tp))
    return orders


def find_all_orders(
    candles_s1: List[s1.Candle],
    candles_s2: List[s2.Candle],
    candles_s3: List[s3.Candle],
    stop_distance: float,
    reward_multiple: float = 2.0,
    s1_lookback: int = 20,
    s1_tolerance_ratio: float = 0.15,
    s2_confirm_bars: int = 2,
    s2_fvg_buffer_ratio: float = 0.25,
    s2_reward_multiple: float = 2.0,
    s3_lookback: int = 20,
    s3_tolerance_ratio: float = 0.15,
    s3_max_wait_bars: int = 10,
) -> List[TaggedOrder]:
    """Merges the three strategies' signals into one time-sorted list of
    ready-to-place orders. When two signals land on the same candle time,
    Strategy 1 takes priority over Strategy 3 over Strategy 2 - this is
    an arbitrary, explicit tie-break, not a claim that one strategy is
    "better"."""
    orders = (
        _s1_orders(candles_s1, stop_distance, reward_multiple, s1_lookback, s1_tolerance_ratio)
        + _s3_orders(candles_s3, stop_distance, reward_multiple, s3_lookback, s3_tolerance_ratio, s3_max_wait_bars)
        + _s2_orders(candles_s2, s2_confirm_bars, s2_fvg_buffer_ratio, s2_reward_multiple)
    )
    orders.sort(key=lambda o: o.time)
    return orders


def evaluate_and_trade(
    candles_s1: List[s1.Candle],
    candles_s2: List[s2.Candle],
    candles_s3: List[s3.Candle],
    broker: Broker,
    symbol: str,
    volume: float,
    stop_distance: float,
    reward_multiple: float = 2.0,
    gate: Optional[RiskGate] = None,
    **detector_kwargs,
) -> List[TaggedOrder]:
    """Places a trade for the first qualifying signal from any strategy
    (walking candles_s1 bar by bar), then skips every other signal
    until the position closes AND, when a gate is given, the gate
    allows trading again. Returns the orders that were actually traded,
    in order. detector_kwargs are forwarded to find_all_orders (e.g.
    s1_lookback)."""
    if stop_distance <= 0:
        raise ValueError("stop_distance must be positive")

    all_orders = find_all_orders(
        candles_s1, candles_s2, candles_s3, stop_distance, reward_multiple, **detector_kwargs
    )
    # setdefault keeps the first (highest-priority, per the tie-break
    # above) order already sorted into each time slot.
    orders_by_time = {}
    for order in all_orders:
        orders_by_time.setdefault(order.time, order)

    traded: List[TaggedOrder] = []
    for candle in candles_s1:
        if gate is not None:
            gate.advance_bar()
            for outcome in broker.pop_closed_outcomes(symbol):
                gate.record_outcome(outcome)

        if broker.has_open_position(symbol):
            continue
        if gate is not None and not gate.can_trade():
            continue

        order = orders_by_time.get(candle.time)
        if order is None:
            continue

        result = broker.place_order(OrderRequest(
            symbol=symbol,
            direction=order.direction,
            volume=volume,
            entry=order.entry,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            comment=f"{order.strategy} auto (combined)",
        ))
        if result.accepted:
            traded.append(order)

    return traded


if __name__ == "__main__":
    from broker import FakeBroker

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

    broker = FakeBroker()
    gate = RiskGate(cooldown_bars=5, max_consecutive_losses=3)
    traded = evaluate_and_trade(
        sample_s1, sample_s2, sample_s3, broker,
        symbol="XAUUSD", volume=0.01, stop_distance=1.0,
        s1_lookback=3, s1_tolerance_ratio=0.2,
        s3_lookback=3, s3_tolerance_ratio=0.2, s3_max_wait_bars=5,
        gate=gate,
    )
    print(f"Trades placed: {len(traded)} (only the first-in-time signal should fire, the rest wait)")
    for order in broker.orders:
        print(
            f"  {order.comment}: {order.direction} vol={order.volume} entry={order.entry:.2f} "
            f"SL={order.stop_loss:.2f} TP={order.take_profit:.2f}"
        )
