"""The ONLY file in this app that imports MetaTrader5.

Everything else (app_core.py, gui_app.py) works without that package
installed, so the app can start up and be used to review settings even
before MetaTrader5 is set up - it's only needed the moment you press
Start.

NOT verified against a real MT5 terminal - there is none in the
environment this was written in. Test on a demo account.
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import strategy1_sweep_wick as s1
import strategy2_bos_fvg as s2


class Mt5DataSource:
    def __init__(self):
        self._mt5 = None

    def connect(self) -> None:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            raise RuntimeError(f"MetaTrader5.initialize() failed: {mt5.last_error()}")
        self._mt5 = mt5

    def disconnect(self) -> None:
        if self._mt5 is not None:
            self._mt5.shutdown()
            self._mt5 = None

    def symbol_exists(self, symbol: str) -> bool:
        if self._mt5 is None:
            raise RuntimeError("Not connected - call connect() first")
        return self._mt5.symbol_info(symbol) is not None

    def fetch_recent_candles(self, which: str, symbol: str, timeframe_name: str, count: int) -> list:
        """which is "s1" or "s2" - selects which strategy module's
        Candle class to build, since Strategy 2 defines its own (see
        the module docstrings in trading-assistant/python)."""
        if self._mt5 is None:
            raise RuntimeError("Not connected - call connect() first")

        candle_cls = s1.Candle if which == "s1" else s2.Candle
        timeframe = getattr(self._mt5, f"TIMEFRAME_{timeframe_name}")
        rates = self._mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            return []

        candles = []
        for rate in rates:
            time_label = datetime.fromtimestamp(int(rate["time"]), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            try:
                candles.append(candle_cls(
                    time_label, float(rate["open"]), float(rate["high"]),
                    float(rate["low"]), float(rate["close"]),
                ))
            except ValueError:
                continue  # skip a bar with an invalid OHLC combination rather than crash the loop
        return candles
