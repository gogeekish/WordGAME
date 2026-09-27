"""Does the risk gate (cooldown-after-loss + consecutive-loss circuit
breaker) actually help, on the same real data used throughout this
project? Runs the exact auto-trade loop shape (bar by bar, gate
consulted every bar) against real candles, using a broker that looks
ahead with backtest.py's own simulate_outcome() to know exactly when
and how each trade closes - fair game offline, since the whole history
is already sitting in memory, unlike a real live broker.

Same discipline as trend_filter_test.py: change ONE thing (add the
gate) on top of the untuned defaults, and report both the training
slice and the untouched test slice side by side.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import strategy1_sweep_wick as s1
import strategy3_wick_sweep_after as s3
from backtest import average_range, fetch_yahoo_candles, load_mt5_csv, simulate_outcome
from broker import OrderRequest, OrderResult
from levels import fixed_distance_levels
from risk_gate import RiskGate
from tune import score, split_train_test

DEFAULT_LOOKBACK = 20
DEFAULT_TOLERANCE_RATIO = 0.15
DEFAULT_STOP_MULT = 1.5
DEFAULT_REWARD_MULTIPLE = 2.0
DEFAULT_MAX_WAIT_BARS = 10


@dataclass
class SimulatingBroker:
    """Offline-only broker: on place_order, looks ahead in `candles`
    with simulate_outcome() to know in advance exactly when/how the
    trade closes, then reports that outcome once the bar loop actually
    reaches that time. Never used for real trading - see broker.py for
    the FakeBroker/Mt5Broker used there."""

    candles: list
    _current_index: int = 0
    _open: Dict[str, dict] = field(default_factory=dict)
    _ready_outcomes: Dict[str, List[str]] = field(default_factory=dict)
    orders: list = field(default_factory=list)

    def advance_to(self, index: int) -> None:
        self._current_index = index
        candle_time = self.candles[index].time
        for symbol in list(self._open):
            info = self._open[symbol]
            if info["exit_time"] == candle_time:
                self._ready_outcomes.setdefault(symbol, []).append(info["outcome"])
                del self._open[symbol]

    def has_open_position(self, symbol: str) -> bool:
        return symbol in self._open

    def pop_closed_outcomes(self, symbol: str) -> List[str]:
        return self._ready_outcomes.pop(symbol, [])

    def place_order(self, request: OrderRequest) -> OrderResult:
        if request.volume <= 0:
            return OrderResult(accepted=False, message="volume must be positive")
        result = simulate_outcome(
            self.candles, self._current_index, "", request.direction,
            request.entry, request.stop_loss, request.take_profit,
        )
        self.orders.append(request)
        # exit_time is None for a trade that never closes within the
        # available data ("open") - that never matches a real candle
        # time, so the position correctly just stays open for the rest
        # of the run, same as backtest.py treats it.
        self._open[request.symbol] = {"exit_time": result.exit_time, "outcome": result.outcome}
        return OrderResult(accepted=True, ticket=len(self.orders))


def run(strategy_module, candles: list, stop_distance: float, gate: Optional[RiskGate]) -> list:
    """Walks `candles` bar by bar exactly like the real auto_strategy1
    /auto_strategy3 scripts do, placing a trade on every qualifying
    signal that the gate (if any) allows. Returns the list of "win"/
    "loss"/"open" outcomes actually realized."""
    find_kwargs = dict(lookback=DEFAULT_LOOKBACK, tolerance_ratio=DEFAULT_TOLERANCE_RATIO)
    if strategy_module is s3:
        find_kwargs["max_wait_bars"] = DEFAULT_MAX_WAIT_BARS

    signals_by_time = {sig.time: sig for sig in strategy_module.find_signals(candles, **find_kwargs)}
    broker = SimulatingBroker(candles)
    symbol = "SIM"
    realized_outcomes: List[str] = []

    for i in range(DEFAULT_LOOKBACK, len(candles)):
        broker.advance_to(i)
        if gate is not None:
            gate.advance_bar()
            for outcome in broker.pop_closed_outcomes(symbol):
                gate.record_outcome(outcome)
                realized_outcomes.append(outcome)
        else:
            realized_outcomes.extend(broker.pop_closed_outcomes(symbol))

        if broker.has_open_position(symbol):
            continue
        if gate is not None and not gate.can_trade():
            continue

        signal = signals_by_time.get(candles[i].time)
        if signal is None:
            continue

        stop_loss, take_profit = fixed_distance_levels(
            signal.direction, signal.entry_price, stop_distance, DEFAULT_REWARD_MULTIPLE
        )
        broker.place_order(OrderRequest(symbol, signal.direction, 0.01, signal.entry_price, stop_loss, take_profit))

    return realized_outcomes


def report(label: str, outcomes: List[str]) -> None:
    wins = outcomes.count("win")
    losses = outcomes.count("loss")
    decided = wins + losses
    if decided == 0:
        print(f"    {label:28s} 0 decided trades")
        return
    win_rate = wins / decided * 100
    expectancy = (wins * DEFAULT_REWARD_MULTIPLE - losses) / decided
    total_r = wins * DEFAULT_REWARD_MULTIPLE - losses
    print(f"    {label:28s} {decided:3d} decided, win rate {win_rate:5.1f}%, "
          f"expectancy {expectancy:+.2f}R, total {total_r:+.1f}R")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        print(f"Loading real candles from your MT5 export: {csv_path}")
        all_candles = load_mt5_csv(csv_path, s1.Candle)
    else:
        print("No CSV path given - fetching 60 days of 15-minute GC=F candles from Yahoo Finance instead.")
        print("(For real XAUUSD: python3 risk_gate_test.py path/to/your_mt5_export.csv)")
        all_candles = fetch_yahoo_candles(s1.Candle, "GC=F", "60d", "15m")

    train, test = split_train_test(all_candles)
    print(f"Train: {len(train)} candles ({train[0].time} to {train[-1].time})")
    print(f"Test:  {len(test)} candles ({test[0].time} to {test[-1].time})\n")

    for strategy_name, module in [("Strategy 1 (sweep + equal-wick)", s1), ("Strategy 3 (equal-wick + sweep-after)", s3)]:
        print("=" * 78)
        print(strategy_name)
        print("=" * 78)

        for label, candles in [("TRAIN", train), ("TEST (unseen)", test)]:
            stop_distance = average_range(candles) * DEFAULT_STOP_MULT
            print(f"  {label}:")
            report("no gate (instant reboot)", run(module, candles, stop_distance, gate=None))
            report("cooldown=5, max-loss=3", run(module, candles, stop_distance,
                                                   gate=RiskGate(cooldown_bars=5, max_consecutive_losses=3)))
            report("cooldown=10, max-loss=2", run(module, candles, stop_distance,
                                                    gate=RiskGate(cooldown_bars=10, max_consecutive_losses=2)))
        print()
