import pandas as pd
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Signal:
    """Represents a trading signal at a specific point in time."""
    ts: pd.Timestamp
    label: str
    direction: str # 'bullish' or 'bearish'
    confidence: float # A score from 0 to 100
    reason: str

class SignalsEngine:
    """
    Generates trading signals based on technical indicators and price action,
    assigning a confidence score to each signal.
    """

    def generate(self, df_ohlcv: pd.DataFrame, indicators: Dict[str, pd.Series]) -> List[Signal]:
        """
        Analyzes the data and indicators to generate a list of signals.

        Args:
            df_ohlcv: DataFrame with columns 'Open', 'High', 'Low', 'Close', 'Volume'.
            indicators: A dictionary of computed indicator series.

        Returns:
            A list of Signal objects.
        """
        signals = []
        if df_ohlcv.empty:
            return signals

        # Combine all data into a single DataFrame for easier analysis
        df = df_ohlcv.join(pd.DataFrame(indicators))

        # --- Signal Logic ---
        # Iterate over the last N days to generate recent signals
        for i in range(len(df) - 30, len(df)): # Look at last 30 days for signals
            if i < 1: continue

            row = df.iloc[i]
            prev_row = df.iloc[i-1]

            # 1. EMA Ribbon Flip
            ema_short = row.get('EMA_8')
            ema_long = row.get('EMA_55')
            prev_ema_short = prev_row.get('EMA_8')
            prev_ema_long = prev_row.get('EMA_55')
            if all([ema_short, ema_long, prev_ema_short, prev_ema_long]):
                if ema_short > ema_long and prev_ema_short <= prev_ema_long:
                    signals.append(Signal(row.name, "EMA Ribbon Flip", "bullish", 30, "Short EMA crossed above Long EMA"))
                elif ema_short < ema_long and prev_ema_short >= prev_ema_long:
                    signals.append(Signal(row.name, "EMA Ribbon Flip", "bearish", 30, "Short EMA crossed below Long EMA"))

            # 2. Volatility Squeeze Breakout
            in_squeeze = row.get('VOLATILITY_SQUEEZE')
            prev_in_squeeze = prev_row.get('VOLATILITY_SQUEEZE')
            bb_upper = row.get('BBU_20_2.0')
            if prev_in_squeeze and not in_squeeze and bb_upper:
                if row['Close'] > bb_upper:
                     signals.append(Signal(row.name, "Squeeze Breakout", "bullish", 25, "Price broke above Bollinger Band after a squeeze"))

            # 3. Pullback to VWAP
            vwap = row.get('VWAP_D')
            ema_200 = row.get('SMA_200')
            if all([vwap, ema_200]):
                is_uptrend = row['Close'] > ema_200 # Simple trend filter
                is_near_vwap = abs(row['Close'] - vwap) / vwap < 0.01 # Within 1% of VWAP
                is_bullish_candle = row['Close'] > row['Open']
                if is_uptrend and is_near_vwap and is_bullish_candle:
                    signals.append(Signal(row.name, "Pullback to VWAP", "bullish", 20, "Bounced off VWAP in an uptrend"))

            # 4. RSI Range Shift
            rsi = row.get('RSI_14')
            prev_rsi = prev_row.get('RSI_14')
            if all([rsi, prev_rsi]):
                if prev_rsi < 40 and rsi >= 40:
                    signals.append(Signal(row.name, "RSI Range Shift", "bullish", 15, "RSI crossed above 40 (Bear to Neutral)"))
                elif prev_rsi > 60 and rsi <= 60:
                     signals.append(Signal(row.name, "RSI Range Shift", "bearish", 15, "RSI crossed below 60 (Bull to Neutral)"))

        # Note: Fib Retest signal requires Fib levels, which are calculated separately.
        # This can be integrated in a higher-level service that has access to both.

        # Simple aggregation: combine signals on the same day
        if not signals:
            return []

        final_signals = {}
        for s in sorted(signals, key=lambda x: x.confidence, reverse=True):
            if s.ts not in final_signals:
                final_signals[s.ts] = s
            else:
                # Append reason and average confidence if multiple signals on same day
                existing_signal = final_signals[s.ts]
                if s.direction == existing_signal.direction:
                     existing_signal.reason += f"; {s.reason}"
                     existing_signal.confidence = (existing_signal.confidence + s.confidence) / 2

        return list(final_signals.values())