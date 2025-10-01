import pandas as pd
import pandas_ta as ta
import logging
from dataclasses import dataclass, field
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class IndicatorConfig:
    """Configuration for technical indicators."""
    # Overlays
    enable_sma: bool = True
    sma_lengths: list[int] = field(default_factory=lambda: [50, 200])

    enable_ema_ribbon: bool = True
    ema_ribbon_lengths: list[int] = field(default_factory=lambda: [8, 13, 21, 34, 55])

    enable_bbands: bool = True
    bbands_length: int = 20
    bbands_std_dev: float = 2.0

    enable_kc: bool = True
    kc_length: int = 20
    kc_atr_multiplier: float = 2.0

    enable_vwap: bool = True
    vwap_anchor: str = 'D' # 'D' for daily, 'W' for weekly, 'M' for monthly reset

    # Panes
    enable_rsi: bool = True
    rsi_length: int = 14

    enable_macd: bool = True
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    enable_stoch: bool = True
    stoch_k: int = 14
    stoch_d: int = 3
    stoch_smooth_k: int = 3

    enable_atr: bool = True
    atr_length: int = 14

    enable_obv: bool = True
    enable_mfi: bool = True
    mfi_length: int = 14

class IndicatorEngine:
    """Computes a wide range of technical indicators on OHLCV data."""

    def compute(self, df_ohlcv: pd.DataFrame, config: IndicatorConfig = IndicatorConfig()) -> Dict[str, pd.Series]:
        """
        Computes all configured technical indicators.

        Args:
            df_ohlcv: DataFrame with columns 'Open', 'High', 'Low', 'Close', 'Volume'.
            config: An IndicatorConfig object specifying which indicators to run.

        Returns:
            A dictionary where keys are indicator names and values are pandas Series or DataFrames.
        """
        if df_ohlcv.empty:
            logging.warning("Input DataFrame is empty. Cannot compute indicators.")
            return {}

        indicators = {}
        df = df_ohlcv.copy()

        # Custom strategy for pandas-ta
        strategy = ta.Strategy(
            name="Rectifex Advanced",
            description="A comprehensive set of indicators for the Rectifex Global Screener.",
            ta=[]
        )

        # Overlays
        if config.enable_sma:
            for length in config.sma_lengths:
                strategy.ta.append({"kind": "sma", "length": length})

        if config.enable_ema_ribbon:
            for length in config.ema_ribbon_lengths:
                 strategy.ta.append({"kind": "ema", "length": length})

        if config.enable_bbands:
            strategy.ta.append({"kind": "bbands", "length": config.bbands_length, "std": config.bbands_std_dev, "append": True})

        if config.enable_kc:
            strategy.ta.append({"kind": "kc", "length": config.kc_length, "scalar": config.kc_atr_multiplier, "append": True})

        if config.enable_vwap:
            strategy.ta.append({"kind": "vwap", "anchor": config.vwap_anchor})

        # Panes
        if config.enable_rsi:
            strategy.ta.append({"kind": "rsi", "length": config.rsi_length})

        if config.enable_macd:
            strategy.ta.append({"kind": "macd", "fast": config.macd_fast, "slow": config.macd_slow, "signal": config.macd_signal})

        if config.enable_stoch:
            strategy.ta.append({"kind": "stoch", "k": config.stoch_k, "d": config.stoch_d, "smooth_k": config.stoch_smooth_k})

        if config.enable_atr:
            strategy.ta.append({"kind": "atr", "length": config.atr_length})

        if config.enable_obv:
            strategy.ta.append({"kind": "obv"})

        if config.enable_mfi:
            strategy.ta.append({"kind": "mfi", "length": config.mfi_length})

        # Run the strategy
        df.ta.strategy(strategy)

        # Volatility Squeeze
        bb_upper_col = f'BBU_{config.bbands_length}_{config.bbands_std_dev}'
        bb_lower_col = f'BBL_{config.bbands_length}_{config.bbands_std_dev}'
        kc_upper_col = f'KCUe_{config.kc_length}_{config.kc_atr_multiplier}'
        kc_lower_col = f'KCLe_{config.kc_length}_{config.kc_atr_multiplier}'

        if all(col in df.columns for col in [bb_upper_col, bb_lower_col, kc_upper_col, kc_lower_col]):
            bb_width = df[bb_upper_col] - df[bb_lower_col]
            kc_width = df[kc_upper_col] - df[kc_lower_col]
            df['VOLATILITY_SQUEEZE'] = bb_width < kc_width

        # Convert the resulting DataFrame columns into a dictionary
        for col in df.columns:
            if col not in df_ohlcv.columns: # Avoid duplicating original data
                indicators[col] = df[col]

        logging.info(f"Computed {len(indicators)} indicator series.")
        return indicators