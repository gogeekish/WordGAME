"""RiskGate - the two reboot upgrades: a cooldown after a loss, and a
hard stop after too many losses in a row.

This has no idea what a candle, a broker, or a strategy is - it just
answers one question, "can I trade right now?", based on outcomes it's
told about. That keeps it usable from the Python auto-trade scripts,
the backtester, and (as the same three rules, hand-translated) the
MQL5 Auto Trade EAs.

Rules:
  - After a LOSING trade closes, no new trade is allowed for
    `cooldown_bars` bars (a winning trade does not trigger a cooldown -
    only losses do, since the goal is to stop revenge-trading into bad
    conditions, not to slow down a strategy that's working).
  - After `max_consecutive_losses` losses in a row, the gate halts
    completely and stays halted until reset() is called - deliberately
    requiring a human to look at what happened, not something that
    clears itself on a timer.
"""

from dataclasses import dataclass


@dataclass
class RiskGate:
    cooldown_bars: int = 5
    max_consecutive_losses: int = 3

    def __post_init__(self) -> None:
        if self.cooldown_bars < 0:
            raise ValueError("cooldown_bars must not be negative")
        if self.max_consecutive_losses < 1:
            raise ValueError("max_consecutive_losses must be at least 1")
        self._consecutive_losses = 0
        self._bars_since_loss = None  # None = no cooldown in progress
        self._halted = False
        self._halted_reason = ""

    @property
    def halted(self) -> bool:
        return self._halted

    @property
    def halted_reason(self) -> str:
        return self._halted_reason

    @property
    def consecutive_losses(self) -> int:
        return self._consecutive_losses

    def can_trade(self) -> bool:
        """Whether a new trade is allowed right now."""
        if self._halted:
            return False
        if self._bars_since_loss is not None and self._bars_since_loss < self.cooldown_bars:
            return False
        return True

    def advance_bar(self) -> None:
        """Call once per candle/bar processed, whether or not a trade
        happens on it - this is what makes the cooldown count down."""
        if self._bars_since_loss is not None:
            self._bars_since_loss += 1

    def record_outcome(self, outcome: str) -> None:
        """Tell the gate a trade just closed. outcome must be "win" or
        "loss"."""
        if outcome == "loss":
            self._consecutive_losses += 1
            self._bars_since_loss = 0
            if self._consecutive_losses >= self.max_consecutive_losses:
                self._halted = True
                self._halted_reason = (
                    f"{self._consecutive_losses} losses in a row "
                    f"(limit {self.max_consecutive_losses})"
                )
        elif outcome == "win":
            self._consecutive_losses = 0
            self._bars_since_loss = None
        else:
            raise ValueError(f"outcome must be 'win' or 'loss', got {outcome!r}")

    def reset(self) -> None:
        """Manually clear a halt (and the cooldown) - the human-in-the-
        loop step after a losing streak trips the circuit breaker."""
        self._consecutive_losses = 0
        self._bars_since_loss = None
        self._halted = False
        self._halted_reason = ""


if __name__ == "__main__":
    gate = RiskGate(cooldown_bars=3, max_consecutive_losses=3)

    assert gate.can_trade()
    print("OK: a fresh gate allows trading")

    gate.record_outcome("loss")
    assert not gate.can_trade()
    print("OK: a loss starts a cooldown, blocking the very next bar")

    for _ in range(3):
        gate.advance_bar()
    assert gate.can_trade()
    print("OK: after cooldown_bars elapse, trading is allowed again")

    gate.record_outcome("win")
    assert gate.consecutive_losses == 0
    gate.record_outcome("loss")
    assert gate.consecutive_losses == 1 and not gate.halted
    print("OK: a win in between resets the consecutive-loss count")

    for _ in range(gate.cooldown_bars):
        gate.advance_bar()
    gate.record_outcome("loss")
    assert gate.consecutive_losses == 2 and not gate.halted

    for _ in range(gate.cooldown_bars):
        gate.advance_bar()
    gate.record_outcome("loss")
    assert gate.consecutive_losses == 3
    assert not gate.can_trade()
    assert gate.halted
    print(f"OK: {gate.consecutive_losses} losses in a row (max is {gate.max_consecutive_losses}) halts the gate ({gate.halted_reason})")

    for _ in range(100):
        gate.advance_bar()
    assert not gate.can_trade(), "a halt must not clear itself just by waiting"
    print("OK: a halt does not clear on its own, no matter how many bars pass")

    gate.reset()
    assert gate.can_trade()
    print("OK: reset() clears the halt")
