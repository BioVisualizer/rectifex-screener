import pandas as pd
import mplfinance as mpf
import logging
from typing import Dict, Literal

from core.config import SNAPSHOT_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChartService:
    """
    Handles the rendering of financial charts with indicators and Fibonacci levels.
    """
    def __init__(self, theme: Literal['dark', 'light'] = 'dark'):
        self.theme = theme
        self.fig = None
        self.ax = None

    def set_theme(self, theme: Literal['dark', 'light']):
        """Sets the color theme for the charts."""
        self.theme = theme
        logging.info(f"Chart theme set to {theme}.")

    def _get_style(self):
        """Returns the mplfinance style based on the current theme."""
        if self.theme == 'dark':
            return mpf.make_marketcolors(
                up='#00b746', down='#ef403c',
                edge='inherit', wick='inherit', volume='inherit'
            ), mpf.make_mpf_style(
                base_mpf_style='nightclouds',
                marketcolors=mpf.make_marketcolors(up='#00b746', down='#ef403c'),
                gridstyle='--',
                y_on_right=True
            )
        else: # light theme
            return mpf.make_marketcolors(
                up='#00A640', down='#FF4A4A',
                edge='inherit', wick='inherit', volume='inherit'
            ), mpf.make_mpf_style(
                base_mpf_style='yahoo',
                marketcolors=mpf.make_marketcolors(up='#00A640', down='#FF4A4A'),
                gridstyle='--',
                y_on_right=True
            )

    def draw(self, symbol: str, df_ohlcv: pd.DataFrame, indicators: Dict, fib: Dict | None, options: Dict) -> str | None:
        """
        Draws the chart with all its components and saves it to a file.

        Args:
            symbol: The ticker symbol for titles and filenames.
            df_ohlcv: The main OHLCV data.
            indicators: A dictionary of indicator data.
            fib: A dictionary with Fibonacci levels and anchors.
            options: A dictionary of drawing options (e.g., which indicators to show).

        Returns:
            The filepath of the saved chart image, or None on failure.
        """
        if df_ohlcv.empty:
            logging.warning("Cannot draw chart, OHLCV data is empty.")
            return None

        mc, style = self._get_style()

        # Prepare additional plots (addplots)
        addplots = []

        # --- Overlays ---
        if options.get('show_ema_ribbon'):
            for key in indicators:
                if key.startswith('EMA_'):
                    addplots.append(mpf.make_addplot(indicators[key], panel=0))

        if options.get('show_bbands'):
            addplots.append(mpf.make_addplot(indicators[f'BBU_{options["bb_len"]}_{options["bb_std"]}'], panel=0, color='cyan'))
            addplots.append(mpf.make_addplot(indicators[f'BBL_{options["bb_len"]}_{options["bb_std"]}'], panel=0, color='cyan'))

        if options.get('show_vwap'):
             addplots.append(mpf.make_addplot(indicators['VWAP_D'], panel=0, color='magenta', linestyle='--'))

        # --- Panes ---
        panel_id = 1
        if options.get('show_rsi'):
            addplots.append(mpf.make_addplot(indicators['RSI_14'], panel=panel_id, ylabel='RSI', color='orange'))
            panel_id += 1

        if options.get('show_macd'):
            addplots.append(mpf.make_addplot(indicators['MACD_12_26_9'], panel=panel_id, ylabel='MACD', color='blue'))
            addplots.append(mpf.make_addplot(indicators['MACDs_12_26_9'], panel=panel_id, color='red', linestyle='--'))
            addplots.append(mpf.make_addplot(indicators['MACDh_12_26_9'], type='bar', panel=panel_id, color='gray', alpha=0.5))
            panel_id += 1

        # Chart configuration
        chart_title = f"{symbol} - Advanced Chart Analysis"
        figscale = 2.4

        # Dynamically construct panel_ratios based on the number of panels
        # The main panel gets a ratio of 3, each indicator panel gets a ratio of 1.
        ratios = [3]  # Start with the main panel
        if panel_id > 1:
            # Add a ratio for each additional panel
            ratios.extend([1] * (panel_id - 1))
        panel_ratios = tuple(ratios)


        # Limit data to the last year (approx. 252 trading days) to prevent compression
        df_plot = df_ohlcv.tail(252)

        try:
            self.fig, self.ax = mpf.plot(
                df_plot,
                type='candle',
                style=style,
                title=chart_title,
                ylabel='Price',
                volume=True,
                addplot=addplots,
                panel_ratios=panel_ratios,
                figscale=figscale,
                returnfig=True
            )

            # --- Fibonacci Lines ---
            if fib and options.get('show_fib'):
                ax_main = self.ax[0]
                y_transform = ax_main.get_yaxis_transform()
                for level_name, price in fib['levels'].items():
                    color = 'green' if 'Retrace' in level_name else 'purple'
                    label = f"{level_name.split('_')[0]} {level_name.split('_')[1]}%"
                    ax_main.axhline(y=price, color=color, linestyle='--', linewidth=0.7, alpha=0.8)
                    ax_main.text(
                        0.995,
                        price,
                        f" {label}",
                        va='center',
                        ha='right',
                        color=color,
                        fontsize=8,
                        transform=y_transform,
                    )

            # Save the figure
            filepath = SNAPSHOT_DIR / f"{symbol.lower()}_chart.png"
            self.fig.savefig(filepath, bbox_inches='tight')
            logging.info(f"Chart for {symbol} saved to {filepath}")
            return str(filepath)

        except Exception as e:
            logging.error(f"Failed to draw or save chart for {symbol}: {e}")
            return None
        finally:
            # Ensure figures are closed to avoid memory leaks and blank charts
            try:
                if self.fig:
                    import matplotlib.pyplot as plt
                    plt.close(self.fig)
            finally:
                self.fig = None
                self.ax = None
