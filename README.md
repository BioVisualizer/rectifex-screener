# Rectifex Global Screener v2

A modern, open-source stock analysis tool for Linux, redesigned for advanced charting and fast, single-stock analysis.

![Rectifex v2 Dark Mode UI](assets/rectifex-v2-dark-mode.png)

---

## What is Rectifex?

Rectifex is a desktop application designed for technical and quantitative stock analysis. Version 2 marks a significant evolution, focusing on a modernized user interface and powerful new tools for individual stock deep-dives, while maintaining its original screening capabilities. All data is sourced exclusively from **yfinance**, ensuring free and accessible market data.

*Built by Lukas Morcinek, Modernized by AI Agent Jules*

## Key Features in Version 2

*   **Modern UI with Dark/Light Themes:** A complete visual overhaul for a clean, modern, and productive user experience.
*   **Single-Stock Quick Search (Live Fetch):** Instantly analyze any stock by typing its ticker or name. This feature **always performs a live data fetch** from yfinance to ensure you get the most up-to-date information, which is then written back to the local cache.
*   **Advanced Chart Analysis:** Go beyond the basics with a suite of new professional-grade indicators:
    *   **Fibonacci Retracements & Extensions:** Automatically drawn on the chart to identify key support and resistance levels.
    *   **EMA Ribbons:** Visualize trend strength and direction with exponential moving average ribbons.
    *   **Volume-Weighted Average Price (VWAP):** A key benchmark for intraday analysis.
    *   **Bollinger Bands & Keltner Channels:** Identify volatility and potential breakouts, including a "Volatility Squeeze" indicator.
    *   **Additional Oscillators:** Stochastic, Money Flow Index (MFI), and On-Balance Volume (OBV).
*   **Enhanced CLI:** Programmatically access the new features:
    *   `rectifex-cli single --ticker AAPL`: Fetch live data for a single stock.
    *   `rectifex-cli search --query "Microsoft"`: Find stock tickers using a fuzzy name search.
*   **Multi-Sheet Excel Export:** Export a complete analysis for a single stock, including a summary, raw data, all computed indicators, and generated signals.

---

## Important Note: Data Source & Analysis

*   **YFinance Only:** Rectifex uses the `yfinance` library as its sole data provider. This data is generally reliable but can have inconsistencies.
*   **No Fair Value:** The tool performs quantitative and technical analysis. It does **not** calculate a "fair value" or provide investment advice. All analysis should be supplemented with your own qualitative research.

---

## Installation (for Linux via Flatpak)

This guide is for users who wish to build the application from source.

1.  **Install Flatpak & Build Dependencies:**
    ```bash
    sudo apt install flatpak flatpak-builder git
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
    flatpak install flathub org.kde.Sdk//6.7
    ```

2.  **Clone the Repository:**
    ```bash
    git clone https://github.com/BioVisualizer/rectifex-screener.git
    cd rectifex-screener
    ```

3.  **Build and Install the Flatpak:**
    ```bash
    flatpak-builder --force-clean build-dir io.github.BioVisualizer.Rectifex.yml
    flatpak-builder --user --install --force-clean build-dir io.github.BioVisualizer.Rectifex.yml
    ```
---

## For Developers

This section provides information for those who want to contribute to or modify the application.

### Project Structure (v2 Architecture)

The application has been refactored into a modern, service-oriented architecture:

*   `app/`: Contains the PyQt6 UI code.
    *   `widgets/`: Reusable UI components like `main_window.py`, `search_bar.py`, and `chart_panel.py`.
    *   `theming/`: The `palette.py` and `style.qss` for the dark/light themes.
*   `core/`: Contains the backend business logic, decoupled from the UI.
    *   `data/`: Handles data loading (`loader.py`), caching (`cache.py`), and symbol indexing/searching (`universe.py`).
    *   `indicators/`: Contains the `engine.py` for calculating technical indicators and `fib.py` for Fibonacci levels.
    *   `signals/`: The `engine.py` for generating trade signals.
    *   `chart/`: The `service.py` responsible for rendering charts with `mplfinance`.
*   `cli/`: The `rectifex_cli.py` for command-line access.
*   `tests/`: Unit and UI tests.

### Running from Source

1.  **Set up a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
2.  **Install dependencies:**
    The required packages are listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the application:**
    ```bash
    python app/main_window.py
    ```

### Running Tests

The project uses `pytest` for automated testing.
```bash
pytest -v
```

---

## Disclaimer

This program is for educational and informational purposes only. The results **do not constitute investment advice.** All data is sourced from `yfinance` and may contain errors. Any investment decision is made solely at your own risk.

## License

This project is licensed under the **MIT License**.