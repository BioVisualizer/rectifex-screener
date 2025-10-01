import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List

from core.signals.engine import Signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def export_single_stock_to_excel(
    symbol: str,
    metadata: Dict,
    ohlcv_df: pd.DataFrame,
    indicators: Dict[str, pd.Series],
    signals: List[Signal],
    fib_data: Dict,
    chart_path: str
) -> str | None:
    """
    Exports all analysis data for a single stock to a multi-sheet Excel file.

    Args:
        symbol: The stock ticker.
        metadata: The stock's metadata.
        ohlcv_df: The OHLCV data.
        indicators: Computed indicators.
        signals: Generated signals.
        fib_data: Fibonacci analysis data.
        chart_path: Path to the saved chart image.

    Returns:
        The path to the saved Excel file, or None on failure.
    """
    export_dir = Path.home() / ".cache" / "com.rectifex.GlobalScreener" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    filepath = export_dir / f"{symbol.lower()}_analysis.xlsx"

    try:
        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            # --- 1. Summary Sheet ---
            summary_data = {
                "Property": [
                    "Symbol", "Name", "Exchange", "Market Cap",
                    "Chart Snapshot", "Fib Anchor High", "Fib Anchor Low"
                ],
                "Value": [
                    symbol,
                    metadata.get('longName', 'N/A'),
                    metadata.get('exchange', 'N/A'),
                    f"{metadata.get('marketCap', 0) / 1e9:.2f}B" if metadata.get('marketCap') else "N/A",
                    chart_path,
                    f"{fib_data['anchor_high']['price']:.2f} on {fib_data['anchor_high']['date'].date()}" if fib_data else "N/A",
                    f"{fib_data['anchor_low']['price']:.2f} on {fib_data['anchor_low']['date'].date()}" if fib_data else "N/A"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # --- 2. OHLCV Sheet ---
            ohlcv_df.to_excel(writer, sheet_name='OHLCV')

            # --- 3. Indicators Sheet ---
            indicators_df = pd.DataFrame(indicators)
            indicators_df.to_excel(writer, sheet_name='Indicators')

            # --- 4. Signals Sheet ---
            if signals:
                signals_df = pd.DataFrame([s.__dict__ for s in signals])
                signals_df['ts'] = signals_df['ts'].dt.date # Make timestamp more readable
                signals_df = signals_df[['ts', 'label', 'direction', 'confidence', 'reason']] # Reorder cols
            else:
                signals_df = pd.DataFrame(columns=['ts', 'label', 'direction', 'confidence', 'reason'])
            signals_df.to_excel(writer, sheet_name='Signals', index=False)

        logging.info(f"Successfully exported analysis for {symbol} to {filepath}")
        return str(filepath)
    except Exception as e:
        logging.error(f"Failed to export analysis for {symbol} to Excel: {e}")
        return None