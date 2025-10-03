import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fractal_pivots(series: pd.Series, left: int = 5, right: int = 5) -> Tuple[pd.Series, pd.Series]:
    """
    Identifies fractal pivot highs and lows in a series.
    A pivot high is a value with `left` lower values to its left and `right` lower values to its right.
    A pivot low is a value with `left` higher values to its left and `right` higher values to its right.

    Args:
        series: The pandas Series to analyze (e.g., 'High' or 'Low').
        left: The number of bars to the left of the pivot.
        right: The number of bars to the right of the pivot.

    Returns:
        A tuple of two Series: (pivot_highs, pivot_lows)
    """
    # Highs
    highs = series.rolling(window=left + right + 1, center=True).apply(lambda x: x[left] == np.max(x), raw=True)
    pivot_highs = series[highs == 1]

    # Lows
    lows = series.rolling(window=left + right + 1, center=True).apply(lambda x: x[left] == np.min(x), raw=True)
    pivot_lows = series[lows == 1]

    return pivot_highs, pivot_lows

def auto_fib_levels(high: pd.Series, low: pd.Series, close: pd.Series, mode: str = "last_swing", lookback: int = 252) -> Dict:
    """
    Calculates automatic Fibonacci retracement and extension levels.

    Args:
        high: Series of high prices.
        low: Series of low prices.
        close: Series of close prices (used to determine trend direction).
        mode: The method to find anchors ('last_swing' or 'fractal').
        lookback: The number of periods to look back for swings.

    Returns:
        A dictionary containing the calculated levels, anchors, and direction.
    """
    if high.empty or low.empty or close.empty:
        return {}

    lookback_high = high.iloc[-lookback:]
    lookback_low = low.iloc[-lookback:]

    if mode == "fractal":
        pivot_highs, pivot_lows = fractal_pivots(lookback_high, left=5, right=5)
        if pivot_highs.empty or pivot_lows.empty:
            # Fallback to last swing if no pivots are found
            mode = "last_swing"
        else:
            anchor_high_price = pivot_highs.iloc[-1]
            anchor_low_price = pivot_lows.iloc[-1]
            anchor_high_date = pivot_highs.index[-1]
            anchor_low_date = pivot_lows.index[-1]

            # Ensure high is after low for uptrend, and vice-versa
            if anchor_high_date < anchor_low_date: # Potential downtrend
                 # Find highest high before the low
                 anchor_high_price = lookback_high[lookback_high.index <= anchor_low_date].max()
                 anchor_high_date = lookback_high[lookback_high.index <= anchor_low_date].idxmax()
            else: # Potential uptrend
                 # Find lowest low before the high
                 anchor_low_price = lookback_low[lookback_low.index <= anchor_high_date].min()
                 anchor_low_date = lookback_low[lookback_low.index <= anchor_high_date].idxmin()


    if mode == "last_swing":
        anchor_high_price = lookback_high.max()
        anchor_high_date = lookback_high.idxmax()
        anchor_low_price = lookback_low.min()
        anchor_low_date = lookback_low.idxmin()

    # Determine trend direction
    is_uptrend = anchor_high_date > anchor_low_date
    price_range = anchor_high_price - anchor_low_price

    if price_range == 0:
        return {} # Avoid division by zero

    # Define Fibonacci ratios
    retracement_ratios = [0.236, 0.382, 0.50, 0.618, 0.786]
    extension_ratios = [1.272, 1.618, 2.618]

    levels = {}
    if is_uptrend:
        # Retracements are below the high
        for ratio in retracement_ratios:
            levels[f'Retrace_{ratio*100:.1f}'] = anchor_high_price - price_range * ratio
        # Extensions are above the high
        for ratio in extension_ratios:
            levels[f'Extend_{ratio*100:.1f}'] = anchor_high_price + price_range * (ratio - 1)
    else: # Downtrend
        # Retracements are above the low
        for ratio in retracement_ratios:
            levels[f'Retrace_{ratio*100:.1f}'] = anchor_low_price + price_range * ratio
        # Extensions are below the low
        for ratio in extension_ratios:
            levels[f'Extend_{ratio*100:.1f}'] = anchor_low_price - price_range * (ratio - 1)

    return {
        "levels": levels,
        "anchor_high": {"price": anchor_high_price, "date": anchor_high_date},
        "anchor_low": {"price": anchor_low_price, "date": anchor_low_date},
        "direction": "uptrend" if is_uptrend else "downtrend"
    }