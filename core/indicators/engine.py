import pandas as pd
import logging
from dataclasses import dataclass, field
from typing import Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class IndicatorConfig:
    """Configuration for technical indicators."""
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
    enable_rsi: bool = True
    rsi_length: int = 14
    enable_macd: bool = True
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    enable_atr: bool = True
    atr_length: int = 14

class IndicatorEngine:
    """Computes a wide range of technical indicators on OHLCV data using pure pandas."""

    def compute(self, df_ohlcv: pd.DataFrame, config: IndicatorConfig = IndicatorConfig()) -> Dict[str, pd.Series]:
        if df_ohlcv.empty:
            logging.warning("Input DataFrame is empty. Cannot compute indicators.")
            return {}

        indicators = {}
        df = df_ohlcv.copy()

        # Overlays
        if config.enable_sma:
            for length in config.sma_lengths:
                indicators[f'SMA_{length}'] = df['Close'].rolling(window=length).mean()

        if config.enable_ema_ribbon:
            for length in config.ema_ribbon_lengths:
                indicators[f'EMA_{length}'] = df['Close'].ewm(span=length, adjust=False).mean()

        if config.enable_bbands:
            sma = df['Close'].rolling(window=config.bbands_length).mean()
            std_dev = df['Close'].rolling(window=config.bbands_length).std()
            indicators[f'BBU_{config.bbands_length}_{config.bbands_std_dev}'] = sma + (std_dev * config.bbands_std_dev)
            indicators[f'BBL_{config.bbands_length}_{config.bbands_std_dev}'] = sma - (std_dev * config.bbands_std_dev)

        if config.enable_atr:
            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.ewm(span=config.atr_length, adjust=False).mean()
            indicators[f'ATR_{config.atr_length}'] = atr

        if config.enable_kc:
            ema = df['Close'].ewm(span=config.kc_length, adjust=False).mean()
            atr = indicators.get(f'ATR_{config.atr_length}')
            if atr is not None:
                indicators[f'KCUe_{config.kc_length}_{config.kc_atr_multiplier}'] = ema + (atr * config.kc_atr_multiplier)
                indicators[f'KCLe_{config.kc_length}_{config.kc_atr_multiplier}'] = ema - (atr * config.kc_atr_multiplier)

        if config.enable_vwap:
            vp = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3)
            df['VWAP_D'] = vp.groupby(df.index.date).cumsum() / df['Volume'].groupby(df.index.date).cumsum()
            indicators['VWAP_D'] = df['VWAP_D']

        # Panes
        if config.enable_rsi:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/config.rsi_length, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/config.rsi_length, adjust=False).mean()
            rs = gain / loss
            indicators[f'RSI_{config.rsi_length}'] = 100 - (100 / (1 + rs))

        if config.enable_macd:
            ema_fast = df['Close'].ewm(span=config.macd_fast, adjust=False).mean()
            ema_slow = df['Close'].ewm(span=config.macd_slow, adjust=False).mean()
            indicators[f'MACD_{config.macd_fast}_{config.macd_slow}_{config.macd_signal}'] = ema_fast - ema_slow
            indicators[f'MACDs_{config.macd_fast}_{config.macd_slow}_{config.macd_signal}'] = indicators[f'MACD_{config.macd_fast}_{config.macd_slow}_{config.macd_signal}'].ewm(span=config.macd_signal, adjust=False).mean()
            indicators[f'MACDh_{config.macd_fast}_{config.macd_slow}_{config.macd_signal}'] = indicators[f'MACD_{config.macd_fast}_{config.macd_slow}_{config.macd_signal}'] - indicators[f'MACDs_{config.macd_fast}_{config.macd_slow}_{config.macd_signal}']

        # Volatility Squeeze
        bb_upper = indicators.get(f'BBU_{config.bbands_length}_{config.bbands_std_dev}')
        bb_lower = indicators.get(f'BBL_{config.bbands_length}_{config.bbands_std_dev}')
        kc_upper = indicators.get(f'KCUe_{config.kc_length}_{config.kc_atr_multiplier}')
        kc_lower = indicators.get(f'KCLe_{config.kc_length}_{config.kc_atr_multiplier}')
        if all(s is not None for s in [bb_upper, bb_lower, kc_upper, kc_lower]):
            bb_width = bb_upper - bb_lower
            kc_width = kc_upper - kc_lower
            indicators['VOLATILITY_SQUEEZE'] = bb_width < kc_width

        logging.info(f"Computed {len(indicators)} indicator series.")
        return indicators