"""Shared broker interface for the Auto Trade scripts.

Detection logic never touches a broker directly - each strategy module
only produces Signal objects. The auto_*.py scripts turn a Signal into
an OrderRequest and hand it to a Broker. Swapping FakeBroker for
Mt5Broker is the only thing that changes between "tested in this
sandbox" and "actually places trades in MetaTrader 5".
"""

from dataclasses import dataclass, field
from typing import List, Protocol


@dataclass
class OrderRequest:
    symbol: str
    direction: str  # "bullish" (buy) or "bearish" (sell)
    volume: float
    entry: float
    stop_loss: float
    take_profit: float
    comment: str = ""


@dataclass
class OrderResult:
    accepted: bool
    ticket: int = 0
    message: str = ""


class Broker(Protocol):
    def has_open_position(self, symbol: str) -> bool: ...
    def place_order(self, request: OrderRequest) -> OrderResult: ...


@dataclass
class FakeBroker:
    """In-memory broker for testing the auto-trade wiring without a real
    MetaTrader 5 connection. Records every order it was asked to place
    and tracks a simple open/closed flag per symbol."""

    orders: List[OrderRequest] = field(default_factory=list)
    _open_symbols: set = field(default_factory=set)

    def has_open_position(self, symbol: str) -> bool:
        return symbol in self._open_symbols

    def place_order(self, request: OrderRequest) -> OrderResult:
        if request.volume <= 0:
            return OrderResult(accepted=False, message="volume must be positive")
        self.orders.append(request)
        self._open_symbols.add(request.symbol)
        return OrderResult(accepted=True, ticket=len(self.orders), message="filled (fake)")

    def close_position(self, symbol: str) -> None:
        self._open_symbols.discard(symbol)


class Mt5Broker:
    """Real broker backed by the MetaTrader5 Python package.

    Requires the MetaTrader 5 terminal installed and running on this
    machine, plus `pip install MetaTrader5`. This class is implemented
    but NOT verified - this sandbox has no MT5 terminal to connect to,
    so it has never actually placed an order. Test it on a demo account
    before trusting it with anything else.
    """

    def __init__(self, magic_number: int = 20260001):
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise RuntimeError(
                "The MetaTrader5 package is not installed. Run: pip install MetaTrader5"
            ) from exc

        self._mt5 = mt5
        self.magic_number = magic_number

        if not self._mt5.initialize():
            raise RuntimeError(f"MetaTrader5.initialize() failed: {self._mt5.last_error()}")

    def has_open_position(self, symbol: str) -> bool:
        positions = self._mt5.positions_get(symbol=symbol)
        return positions is not None and len(positions) > 0

    def place_order(self, request: OrderRequest) -> OrderResult:
        if request.volume <= 0:
            return OrderResult(accepted=False, message="volume must be positive")

        order_type = (
            self._mt5.ORDER_TYPE_BUY if request.direction == "bullish" else self._mt5.ORDER_TYPE_SELL
        )
        mt5_request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.volume,
            "type": order_type,
            "price": request.entry,
            "sl": request.stop_loss,
            "tp": request.take_profit,
            "magic": self.magic_number,
            "comment": request.comment,
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
        }
        result = self._mt5.order_send(mt5_request)
        if result is None:
            return OrderResult(accepted=False, message=f"order_send returned None: {self._mt5.last_error()}")

        accepted = result.retcode == self._mt5.TRADE_RETCODE_DONE
        return OrderResult(accepted=accepted, ticket=result.order, message=result.comment)

    def shutdown(self) -> None:
        self._mt5.shutdown()
