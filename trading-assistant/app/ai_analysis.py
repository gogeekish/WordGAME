"""AI chart analysis - the only file in this app that talks to the
Anthropic API.

Lets you point the app at a chart screenshot and get an honest read on
whether Strategy 1, 2, or 3's specific rules (not just "the market
moved") appear to be present, using Claude's vision.

Requires your own Anthropic API key from console.anthropic.com - that
is separate from a claude.ai subscription, and every call made here is
billed to that key, not to Anthropic or to whoever built this app.
"""

import base64
import mimetypes

STRATEGY_RULES = """\
Three trading strategies this app implements, for reference. Only call
one of these a match if you can actually see the specific condition in
the image - not just "the market moved" in some direction.

Strategy 1 (Sweep + Equal-Wick): a candle wicks past a recent swing
high or low and closes back on the other side (a liquidity sweep), and
the VERY NEXT candle has a top wick and bottom wick of about equal
length.

Strategy 2 (BOS + FVG Retest): price breaks a recent swing high/low (a
Break of Structure), leaving a 3-candle price gap behind (a Fair Value
Gap - candle 1's high/low doesn't overlap candle 3's low/high). Price
later comes back and touches that gap zone.

Strategy 3 (Equal-Wick + Sweep After): the same equal-wick candle as
Strategy 1, but the liquidity sweep happens on a LATER candle instead
of the one right before it.
"""

ANALYSIS_PROMPT = f"""You are analyzing a trading chart screenshot for someone new to
programming and trading. Use short, plain sentences - explain things
the way you would to a 10 year old.

{STRATEGY_RULES}

Look at the attached chart and:
1. Describe what you actually see (trend direction, notable candles,
   any sharp reversals) in plain language.
2. Say whether Strategy 1, 2, or 3's SPECIFIC conditions appear to be
   present, and roughly where on the chart (left/middle/right, near
   the top/bottom). Only say yes if you can really see the condition
   (comparable wick lengths, an actual price gap, a candle closing
   back past a level) - don't guess from a vague shape.
3. If the image is too blurry, low-resolution, or small to measure
   something precisely (like comparing two wick lengths), say so
   plainly instead of guessing. Recommend running backtest.py on real
   exported MT5 data for a precise, unambiguous answer instead.
4. If none of the three strategies clearly match, just name the
   general type of price action you see (e.g. "a reversal at
   resistance", "a breakout continuation") instead of forcing a match.

Keep the whole answer under 200 words."""


def analyze_chart(image_path: str, api_key: str, model: str = "claude-sonnet-5") -> str:
    """Sends the image at image_path to Claude and returns its analysis
    as plain text. Raises on any failure (missing key, package not
    installed, bad key, no network, etc) - the caller shows that to
    the user rather than this module trying to hide or retry it."""
    if not api_key.strip():
        raise ValueError("Enter your Anthropic API key first (get one at console.anthropic.com).")

    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "The 'anthropic' package is not installed. Run: pip install anthropic"
        ) from exc

    media_type = mimetypes.guess_type(image_path)[0] or "image/png"
    if media_type not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        raise ValueError(f"Unsupported image type: {media_type}. Use a PNG, JPEG, GIF, or WEBP file.")

    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.standard_b64encode(image_bytes).decode("ascii")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                {"type": "text", "text": ANALYSIS_PROMPT},
            ],
        }],
    )
    return "".join(block.text for block in response.content if block.type == "text")
