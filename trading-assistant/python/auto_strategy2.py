"""Strategy 2 - BOS + FVG retest, Auto Trade version.

Same detection as strategy2_bos_fvg.py, but instead of only alerting,
each retest signal is turned into a real order through a Broker. Only
one position is opened at a time per symbol - once it closes, the next
qualifying signal is free to trade again (the "reboot").

Walks the candles one bar at a time (not signal-by-signal) so an
optional RiskGate can count bars for its cooldown, and each bar polls
broker.pop_closed_outcomes() to learn how the last trade actually
ended - in real trading that comes from the broker (Mt5Broker reads
your account's trade history), not from anything this script simulates
itself.
"""

from typing import List, Optional

from broker import Broker, OrderRequest
from risk_gate import RiskGate
from strategy2_bos_fvg import Candle, RetestSignal, find_signals


def evaluate_and_trade(
    candles: List[Candle],
    broker: Broker,
    symbol: str,
    volume: float,
    confirm_bars: int = 2,
    fvg_buffer_ratio: float = 0.25,
    reward_multiple: float = 2.0,
    gate: Optional[RiskGate] = None,
) -> List[RetestSignal]:
    """Finds every Strategy 2 signal and, walking bar by bar, places a
    trade ONLY if no position is open AND (when a gate is given) the
    gate currently allows it. Entry/SL/TP1 come straight from the
    signal; TP2 is used as the order's take-profit since it is the
    further, higher-conviction target. Returns the signals that were
    actually traded, in order."""
    signals_by_time = {
        s.time: s for s in find_signals(candles, confirm_bars, fvg_buffer_ratio, reward_multiple)
    }
    traded: List[RetestSignal] = []

    for candle in candles[2 * confirm_bars:]:
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
    gate = RiskGate(cooldown_bars=5, max_consecutive_losses=3)
    traded = evaluate_and_trade(sample, broker, symbol="XAUUSD", volume=0.01, gate=gate)
    print(f"Trades placed: {len(traded)}")
    for order in broker.orders:
        print(
            f"  {order.direction} {order.symbol} vol={order.volume} entry={order.entry:.2f} "
            f"SL={order.stop_loss:.2f} TP={order.take_profit:.2f}"
        )
