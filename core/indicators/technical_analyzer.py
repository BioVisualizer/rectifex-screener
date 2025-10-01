import yfinance as yf
import pandas as pd
import mplfinance as mpf
import matplotlib.figure

def _calculate_technical_indicators(ticker_symbol: str, period: str = "1y"):
    """
    Internal function to fetch historical data and calculate indicators.
    """
    try:
        # Fetch historical data using yfinance, hide progress bar
        data = yf.download(ticker_symbol, period=period, auto_adjust=True, progress=False, timeout=30)

        if data.empty:
            print(f"Error: No data downloaded for {ticker_symbol}. It might be an invalid ticker.")
            return None

        # Handle potential MultiIndex columns and standardize to Title Case
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data.columns = [str(col).title() for col in data.columns]

        # --- Calculate Indicators ---
        data['SMA50'] = data['Close'].rolling(window=50).mean()
        data['SMA200'] = data['Close'].rolling(window=200).mean()

        delta = data['Close'].diff(1)
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 0.01)
        data['RSI'] = 100 - (100 / (1 + rs))

        exp12 = data['Close'].ewm(span=12, adjust=False).mean()
        exp26 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp12 - exp26
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['MACD_Hist'] = data['MACD'] - data['MACD_Signal']

        return data

    except Exception as e:
        print(f"An error occurred in _calculate_technical_indicators for {ticker_symbol}: {e}")
        return None

def generate_analysis_figure(ticker_symbol: str, period: str = "1y") -> matplotlib.figure.Figure | None:
    """
    Fetches data, calculates indicators, and generates a technical analysis chart.

    Args:
        ticker_symbol (str): The stock ticker symbol.
        period (str): The period for the data (e.g., "1y").

    Returns:
        matplotlib.figure.Figure: The figure object containing the plot, or None on failure.
    """
    data = _calculate_technical_indicators(ticker_symbol, period)
    if data is None:
        return None

    # Ensure OHLCV columns are numeric
    ohlcv_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    cols_to_convert = [col for col in ohlcv_cols if col in data.columns]

    if cols_to_convert:
        data[cols_to_convert] = data[cols_to_convert].apply(pd.to_numeric, errors='coerce')

    # Drop rows with NaN in essential columns for plotting
    data.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'], inplace=True)

    if data.empty:
        print(f"Error: No valid plot data for {ticker_symbol} after cleaning.")
        return None

    # Define additional plots for RSI and MACD
    add_plots = [
        # Panel 2: RSI
        mpf.make_addplot(data['RSI'], panel=2, color='orange', ylabel='RSI', ylim=(10, 90)),
        mpf.make_addplot(pd.Series(70, index=data.index), panel=2, color='r', linestyle='--', secondary_y=False),
        mpf.make_addplot(pd.Series(30, index=data.index), panel=2, color='g', linestyle='--', secondary_y=False),

        # Panel 3: MACD
        mpf.make_addplot(data['MACD_Hist'], type='bar', panel=3, color='dimgray', ylabel='MACD'),
        mpf.make_addplot(data['MACD'], panel=3, color='blue'),
        mpf.make_addplot(data['MACD_Signal'], panel=3, color='red'),
    ]

    # Create the plot using mplfinance
    try:
        fig, axlist = mpf.plot(
            data,
            type='candle',
            style='yahoo',
            title=f'\n{ticker_symbol} Technical Analysis',
            ylabel='Price',
            volume=True,
            mav=(50, 200),
            addplot=add_plots,
            panel_ratios=(6, 1, 2, 2),  # Ratios for main, volume, RSI, MACD
            figscale=1.2,
            returnfig=True
        )
        # Improve layout
        fig.tight_layout()
        return fig
    except Exception as e:
        print(f"Error during mplfinance plot generation for {ticker_symbol}: {e}")
        return None

if __name__ == '__main__':
    # This block allows for standalone testing of this module
    test_ticker = 'MSFT'
    print(f"--- Testing chart generation for ticker: {test_ticker} ---")

    figure = generate_analysis_figure(test_ticker)

    if figure is not None:
        try:
            output_path = "test_chart.png"
            figure.savefig(output_path, bbox_inches='tight')
            print(f"Chart generation successful. Figure saved to '{output_path}'")
        except Exception as e:
            print(f"--- Test failed: Could not save figure. Error: {e} ---")
    else:
        print(f"--- Test failed: Could not generate chart for {test_ticker} ---")
