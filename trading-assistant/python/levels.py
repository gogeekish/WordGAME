"""Shared entry/SL/TP math for strategies that use a fixed stop
distance and reward multiple (Strategy 1 and Strategy 3). Strategy 2
computes its own levels directly from the FVG zone, so it doesn't need
this - it's here so the auto-trade scripts and the backtester compute
Strategy 1 / Strategy 3 levels the exact same way instead of each
re-implementing the same if/else.
"""


def fixed_distance_levels(
    direction: str,
    entry_price: float,
    stop_distance: float,
    reward_multiple: float,
) -> tuple:
    """Returns (stop_loss, take_profit) for a trade in `direction`
    starting at `entry_price`, with the stop `stop_distance` away and
    the target `reward_multiple` times further in the other direction."""
    if stop_distance <= 0:
        raise ValueError("stop_distance must be positive")
    if reward_multiple <= 0:
        raise ValueError("reward_multiple must be positive")

    if direction == "bullish":
        stop_loss = entry_price - stop_distance
        take_profit = entry_price + stop_distance * reward_multiple
    elif direction == "bearish":
        stop_loss = entry_price + stop_distance
        take_profit = entry_price - stop_distance * reward_multiple
    else:
        raise ValueError(f"direction must be 'bullish' or 'bearish', got {direction!r}")

    return stop_loss, take_profit
