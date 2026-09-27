"""Backtest harness - replays each strategy against real historical
candles and simulates whether the stop loss or take profit would have
been hit first. This never touches a broker; it only replays history
to measure how a strategy would have performed.

Two ways to get candles:

1. load_mt5_csv() - THE RECOMMENDED WAY for XAUUSD specifically. Yahoo
   Finance and this session's other free data sources do not carry the
   retail XAUUSD spot/CFD feed at all (confirmed by hand - Yahoo has no
   XAUUSD=X or XAU=X ticker, and the FMP forex/commodity endpoints need
   a paid plan). Your MetaTrader 5 terminal already has your broker's
   real XAUUSD price history sitting in it. Export it and point this
   at the file:
     In MT5: open an XAUUSD chart -> right-click -> "Save As" (or
     View > History Center) -> save as .csv.
   That is your actual broker's feed - more correct than any proxy.

2. fetch_yahoo_candles() - a quick, no-setup sanity check using GC=F
   (COMEX Gold futures), since Yahoo has no real XAUUSD ticker. Futures
   track spot gold closely but are NOT identical: different trading
   hours, a small futures/spot basis, occasional contract-roll jumps.
   Use this to poke at an idea quickly; use load_mt5_csv() before
   drawing any real conclusion about XAUUSD specifically.

Simulation assumption: when a single candle's range touches BOTH the
stop loss and the take profit, the stop loss is assumed to hit first
(the conservative assumption - OHLC data alone can't tell us what
happened tick by tick inside that candle).

This is a small sample backtest for a sanity check, not a rigorous
strategy evaluation - a handful of days of candles is nowhere near
enough data to judge whether a strategy actually has an edge.
"""

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Type, TypeVar
from urllib.request import Request, urlopen

import strategy1_sweep_wick as s1
import strategy2_bos_fvg as s2
import strategy3_wick_sweep_after as s3
from levels import fixed_distance_levels

CandleT = TypeVar("CandleT")


def fetch_yahoo_candles(
    candle_cls: Type[CandleT],
    symbol: str = "GC=F",
    range_: str = "5d",
    interval: str = "15m",
) -> List[CandleT]:
    """Fetches real OHLC candles from Yahoo Finance's public chart API
    and builds them as `candle_cls` instances (so the same fetch works
    for both Strategy 1/3's Candle type and Strategy 2's distinct one).
    Bars with a missing value (Yahoo sometimes leaves illiquid bars as
    null) are skipped."""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?range={range_}&interval={interval}"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)

    results = payload.get("chart", {}).get("result")
    if not results:
        error = payload.get("chart", {}).get("error")
        raise RuntimeError(f"Yahoo Finance returned no data for {symbol}: {error}")

    result = results[0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]

    candles: List[CandleT] = []
    for i, ts in enumerate(timestamps):
        o, h, l, c = quote["open"][i], quote["high"][i], quote["low"][i], quote["close"][i]
        if None in (o, h, l, c):
            continue
        time_label = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        try:
            candles.append(candle_cls(time_label, o, h, l, c))
        except ValueError:
            continue  # skip any bar whose OHLC values fail validation

    return candles


def load_mt5_csv(path: str, candle_cls: Type[CandleT]) -> List[CandleT]:
    """Loads real candles exported from MetaTrader 5 (your broker's
    actual XAUUSD feed - see the module docstring for how to export
    one). Accepts MT5's standard export layout:

        <DATE>  <TIME>  <OPEN>  <HIGH>  <LOW>  <CLOSE>  <TICKVOL>  <VOL>  <SPREAD>
        2026.09.22  00:00:00  4315.20  4318.50  4313.10  4317.80  245  0  12

    Tab or comma separated, header row optional, TICKVOL/VOL/SPREAD
    columns ignored if present. Rows that fail to parse (wrong column
    count, non-numeric price, or an invalid OHLC combination) are
    skipped and counted rather than crashing the whole load, since a
    hand-exported file occasionally has a stray blank line."""
    candles: List[CandleT] = []
    skipped = 0

    with open(path, newline="") as f:
        sniffer_sample = f.read(2048)
        f.seek(0)
        dialect = csv.excel_tab if "\t" in sniffer_sample else csv.excel
        reader = csv.reader(f, dialect=dialect)

        for row in reader:
            if not row:
                continue  # blank line
            first_cell = row[0].strip().upper()
            if first_cell.startswith("<DATE") or first_cell == "DATE":
                continue  # header row (MT5's "<DATE>" style or a plain "Date" column)
            if len(row) < 6:
                skipped += 1
                continue

            date_str, time_str, o_str, h_str, l_str, c_str = row[:6]
            try:
                time_label = f"{date_str.strip().replace('.', '-')} {time_str.strip()}"
                o, h, l, c = float(o_str), float(h_str), float(l_str), float(c_str)
                candles.append(candle_cls(time_label, o, h, l, c))
            except ValueError:
                skipped += 1
                continue

    if skipped:
        print(f"load_mt5_csv: skipped {skipped} unparseable row(s) in {path}")
    if not candles:
        raise ValueError(f"No valid candles loaded from {path} - check the file format")

    return candles


def average_range(candles: list) -> float:
    """Average high-low range across a candle list - used to size the
    stop distance relative to how much this symbol actually moves,
    instead of guessing a fixed dollar amount."""
    if not candles:
        raise ValueError("candles must not be empty")
    return sum(c.high - c.low for c in candles) / len(candles)


@dataclass
class TradeResult:
    strategy: str
    entry_time: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    outcome: str  # "win", "loss", or "open" (ran out of data before either hit)
    exit_time: Optional[str]


def simulate_outcome(
    candles: list,
    start_index: int,
    strategy: str,
    direction: str,
    entry: float,
    stop_loss: float,
    take_profit: float,
) -> TradeResult:
    """Walks forward from the bar after start_index, checking each
    candle's high/low against the stop loss and take profit."""
    for candle in candles[start_index + 1:]:
        if direction == "bullish":
            hit_sl = candle.low <= stop_loss
            hit_tp = candle.high >= take_profit
        else:
            hit_sl = candle.high >= stop_loss
            hit_tp = candle.low <= take_profit

        if hit_sl:
            return TradeResult(strategy, "", direction, entry, stop_loss, take_profit, "loss", candle.time)
        if hit_tp:
            return TradeResult(strategy, "", direction, entry, stop_loss, take_profit, "win", candle.time)

    return TradeResult(strategy, "", direction, entry, stop_loss, take_profit, "open", None)


def backtest_strategy1(candles: List[s1.Candle], stop_distance: float, reward_multiple: float = 2.0, **kwargs) -> List[TradeResult]:
    time_to_index = {c.time: i for i, c in enumerate(candles)}
    results = []
    for signal in s1.find_signals(candles, **kwargs):
        stop_loss, take_profit = fixed_distance_levels(signal.direction, signal.entry_price, stop_distance, reward_multiple)
        result = simulate_outcome(
            candles, time_to_index[signal.time], "Strategy 1",
            signal.direction, signal.entry_price, stop_loss, take_profit,
        )
        result.entry_time = signal.time
        results.append(result)
    return results


def backtest_strategy2(candles: List[s2.Candle], **kwargs) -> List[TradeResult]:
    time_to_index = {c.time: i for i, c in enumerate(candles)}
    results = []
    for signal in s2.find_signals(candles, **kwargs):
        result = simulate_outcome(
            candles, time_to_index[signal.time], "Strategy 2",
            signal.direction, signal.entry, signal.stop_loss, signal.take_profit_2,
        )
        result.entry_time = signal.time
        results.append(result)
    return results


def backtest_strategy3(candles: List[s3.Candle], stop_distance: float, reward_multiple: float = 2.0, **kwargs) -> List[TradeResult]:
    time_to_index = {c.time: i for i, c in enumerate(candles)}
    results = []
    for signal in s3.find_signals(candles, **kwargs):
        stop_loss, take_profit = fixed_distance_levels(signal.direction, signal.entry_price, stop_distance, reward_multiple)
        result = simulate_outcome(
            candles, time_to_index[signal.time], "Strategy 3",
            signal.direction, signal.entry_price, stop_loss, take_profit,
        )
        result.entry_time = signal.time
        results.append(result)
    return results


def summarize(results: List[TradeResult]) -> None:
    if not results:
        print("  No signals found in this data.")
        return

    wins = sum(1 for r in results if r.outcome == "win")
    losses = sum(1 for r in results if r.outcome == "loss")
    still_open = sum(1 for r in results if r.outcome == "open")
    decided = wins + losses

    print(f"  Signals: {len(results)}  Wins: {wins}  Losses: {losses}  Still open at end of data: {still_open}")
    if decided:
        print(f"  Win rate (of decided trades): {wins / decided * 100:.1f}%")
    for r in results:
        print(f"    {r.entry_time}  {r.strategy}  {r.direction:8s}  entry {r.entry:.2f}  -> {r.outcome}"
              + (f" at {r.exit_time}" if r.exit_time else ""))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # python3 backtest.py path/to/your_mt5_export.csv
        csv_path = sys.argv[1]
        print(f"Loading real candles from your MT5 export: {csv_path}")
        try:
            candles_s1 = load_mt5_csv(csv_path, s1.Candle)
            candles_s2 = load_mt5_csv(csv_path, s2.Candle)
        except (OSError, ValueError) as exc:
            print(f"Could not load {csv_path} ({exc}). No backtest run.")
            raise SystemExit(1)
    else:
        SYMBOL = "GC=F"     # COMEX Gold futures - proxy for XAUUSD, see module docstring
        RANGE = "5d"
        INTERVAL = "15m"
        print(f"No CSV path given - fetching {INTERVAL} candles for {SYMBOL} ({RANGE}) from Yahoo Finance instead.")
        print("(For real XAUUSD: python3 backtest.py path/to/your_mt5_export.csv)")
        try:
            candles_s1 = fetch_yahoo_candles(s1.Candle, SYMBOL, RANGE, INTERVAL)
            candles_s2 = fetch_yahoo_candles(s2.Candle, SYMBOL, RANGE, INTERVAL)
        except Exception as exc:
            print(f"Could not fetch real market data ({exc}). No backtest run.")
            raise SystemExit(1)

    print(f"Got {len(candles_s1)} candles, from {candles_s1[0].time} to {candles_s1[-1].time}.\n")

    stop_distance = average_range(candles_s1) * 1.5
    print(f"Using stop_distance = {stop_distance:.2f} (1.5x the average 15-minute candle range).\n")

    print("=== Strategy 1 (sweep + equal-wick) ===")
    summarize(backtest_strategy1(candles_s1, stop_distance=stop_distance))

    print("\n=== Strategy 2 (BOS + FVG retest) ===")
    summarize(backtest_strategy2(candles_s2))

    print("\n=== Strategy 3 (equal-wick + sweep after) ===")
    summarize(backtest_strategy3(candles_s1, stop_distance=stop_distance))
