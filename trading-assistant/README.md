# Trading Assistant - Help Manual

A set of XAUUSD trading tools built step by step in chat: three signal
strategies, each available as an alert-only "Trade Assistant" or a
"Auto Trade" robot, in both Python and MQL5 (MetaTrader 5), plus tools
to test them against real market data.

**Read this before running anything:** every "Auto Trade" script or EA
here can place real orders. Nothing in this folder has been tested
with real money. Test on a MetaTrader 5 **demo account** for a good
while before ever considering a live one, and read "What's NOT
verified" near the bottom of this manual first.

## What's in here

```
trading-assistant/
  python/
    strategy1_sweep_wick.py        Strategy 1 - Trade Assistant (alert only)
    strategy2_bos_fvg.py           Strategy 2 - Trade Assistant (alert only)
    strategy3_wick_sweep_after.py  Strategy 3 - Trade Assistant (alert only)
    combined_assistant.py          All 3 strategies - Trade Assistant
    auto_strategy1.py              Strategy 1 - Auto Trade
    auto_strategy2.py              Strategy 2 - Auto Trade
    auto_strategy3.py              Strategy 3 - Auto Trade
    combined_auto.py               All 3 strategies - Auto Trade
    broker.py                      Shared order-placing interface (FakeBroker for testing, Mt5Broker for real use)
    risk_gate.py                   The "reboot" rules: cooldown after a loss, circuit breaker after a losing streak
    levels.py                      Shared entry/stop-loss/take-profit math
    backtest.py                    Replays a strategy against real historical candles
    tune.py                        Parameter search with an honest train/test split
    trend_filter_test.py           Tests adding a longer-trend filter on top of Strategy 1/3
    risk_gate_test.py              Tests whether the reboot upgrades actually help, on real data
  mql5/
    Strategy1_SweepWick_Assistant.mq5      Strategy 1 - Trade Assistant EA
    Strategy2_BOS_FVG_Assistant.mq5        Strategy 2 - Trade Assistant EA
    Strategy3_WickSweepAfter_Assistant.mq5 Strategy 3 - Trade Assistant EA
    Combined_Assistant.mq5                 All 3 strategies - Trade Assistant EA
    Strategy1_SweepWick_AutoTrade.mq5      Strategy 1 - Auto Trade EA
    Strategy2_BOS_FVG_AutoTrade.mq5        Strategy 2 - Auto Trade EA
    Strategy3_WickSweepAfter_AutoTrade.mq5 Strategy 3 - Auto Trade EA
    Combined_AutoTrade.mq5                 All 3 strategies - Auto Trade EA
    RiskGate.mqh                           Shared reboot rules, used by the 4 Auto Trade EAs above
```

**Trade Assistant** = watches the chart, marks the setup, sends an
alert. Never places a trade - you click Buy/Sell yourself.
**Auto Trade** = does everything the Assistant does, then places the
trade itself, sets stop-loss/take-profit, and waits for it to close
before watching again (the "reboot").

## Part 1 - Running the Python tools

**Requirements:** Python 3.9 or newer. Nothing else to install for the
Assistant/Auto/backtest/tune scripts - they only use Python's own
standard library. (`Mt5Broker` inside `broker.py`, used for placing
real MT5 orders, additionally needs `pip install MetaTrader5` - but
you only need that once you're ready to actually connect to a live
MetaTrader terminal.)

### Try a strategy's detector on its own

Each strategy file has a small built-in example and can just be run
directly:

```
cd trading-assistant/python
python3 strategy1_sweep_wick.py
python3 strategy2_bos_fvg.py
python3 strategy3_wick_sweep_after.py
python3 combined_assistant.py
```

Each prints the alert(s) it found in its built-in sample data - this
is just a demo, not real market data.

### Try the Auto Trade versions (safely, no real orders)

```
python3 auto_strategy1.py
python3 auto_strategy2.py
python3 auto_strategy3.py
python3 combined_auto.py
```

These also run on built-in sample data, using `FakeBroker` (a pretend
broker that only exists for testing) - no real orders are ever placed
by running these files directly.

### Test against real market data

`backtest.py`, `tune.py`, `trend_filter_test.py`, and `risk_gate_test.py`
can each run two ways:

**A) Quick check, no setup** - just run it with no arguments. It
fetches Gold futures (GC=F) candles from Yahoo Finance as a stand-in
for XAUUSD (Yahoo has no real XAUUSD feed):

```
python3 backtest.py
```

**B) Real XAUUSD data (recommended)** - export your own broker's
actual XAUUSD price history from MetaTrader 5, then point any of these
scripts at the file:

1. In MetaTrader 5: open an XAUUSD chart -> right-click -> "Save As"
   (or View menu -> History Center) -> save as a `.csv` file.
2. Run:
   ```
   python3 backtest.py path/to/your_export.csv
   python3 tune.py path/to/your_export.csv
   python3 trend_filter_test.py path/to/your_export.csv
   python3 risk_gate_test.py path/to/your_export.csv
   ```

### Check the reboot rules on their own

```
python3 risk_gate.py
```

Runs a short self-check of the cooldown and circuit-breaker rules and
prints OK/FAIL for each one.

## Part 2 - Running the MQL5 tools (MetaTrader 5)

1. Open MetaTrader 5 -> File -> Open Data Folder.
2. Go into `MQL5/Experts/` and make a new folder, e.g. `TradingAssistant`.
3. Copy **all 9 files** from `trading-assistant/mql5/` into that folder
   - **including `RiskGate.mqh`**, which the 4 Auto Trade EAs need to
   compile (they `#include "RiskGate.mqh"`, which only works if it's
   sitting in the same folder as the `.mq5` file).
4. Open MetaEditor (F4 inside MetaTrader, or the icon in your Experts
   folder), open one of the `.mq5` files, and press **F7** to compile.
   Fix any errors it reports (these files have not been compiled in
   the environment they were written in - see the warning below).
5. Back in MetaTrader, find the compiled EA in the Navigator panel
   under Expert Advisors, and drag it onto an XAUUSD chart.
6. A settings window opens - check the "Inputs" tab to see/change
   things like lot size, stop distance, cooldown bars, etc.
7. Make sure "Algo Trading" is enabled (the button in the toolbar) and
   that you are on a **demo account**, not live.

Every input has a short comment next to it in MetaEditor explaining
what it does.

## Which strategy is which

- **Strategy 1 - Sweep + Equal-Wick:** waits for price to sweep a
  recent high/low (grab liquidity) and reverse, then checks if the
  very next candle has equal-length wicks top and bottom.
- **Strategy 2 - BOS + FVG Retest:** waits for a Break of Structure,
  finds the price gap (Fair Value Gap) that move left behind, and
  alerts when price comes back to retest it.
- **Strategy 3 - Equal-Wick + Sweep After:** the same equal-wick
  candle as Strategy 1, but confirmed by a liquidity sweep that
  happens *afterward* instead of before.
- **Combined:** runs all three at once and reacts to whichever fires.

## The reboot settings (Auto Trade only)

Two extra rules control when an Auto Trade script/EA is allowed to
trade again after a trade closes:

- **Cooldown bars** - after a **losing** trade, wait this many candles
  before trading again. A winning trade does not trigger a cooldown.
- **Max consecutive losses** - after this many losses in a row, stop
  completely. It does **not** turn back on by itself - someone has to
  restart it (call `.reset()` in Python, or reload the EA in MT5)
  after reviewing what happened.

**Current honest recommendation** (from testing on real data - see
`risk_gate_test.py`): the cooldown helps and is worth keeping close to
its default. The circuit breaker's default (`max_consecutive_losses=3`,
2 in one MQL5 file) is too sensitive for how often these strategies
currently lose 2-3 times in a row just from normal variance - consider
raising it, e.g. to 5-6, unless you specifically want it to stop very
easily.

## What's NOT verified - read this before trusting any of it

- **The MQL5 files have never been compiled.** This environment has no
  MetaEditor. Compile every `.mq5` file yourself (F7) before running
  it, and fix anything the compiler flags.
- **Nothing has been tested on a live or demo MetaTrader account.**
  Every "Auto Trade" file is implemented and logically tested (in
  Python) or carefully re-read by hand (in MQL5), but never run
  against a real order book.
- **Backtests use a small amount of data** (days to weeks). That is
  enough to sanity-check an idea, nowhere near enough to prove a
  strategy has a real edge.
- **`GC=F` (Gold futures) is a proxy for XAUUSD**, not the same feed a
  retail broker gives you. Use your own MT5-exported CSV (Part 1,
  option B) for anything you actually want to trust.
- As tested so far, none of the three strategies has shown a
  consistently positive result on unseen data. That's a finding about
  the current rules, not a reason the code is broken - see this
  project's chat history for the full backtest/tuning results.
