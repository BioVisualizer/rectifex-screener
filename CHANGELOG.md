# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-10-01

### Added

*   **Single-Stock Quick Search:** A new prominent search bar in the UI to instantly analyze any stock by its ticker or name.
*   **Advanced Charting Indicators:** A comprehensive suite of new technical indicators has been added:
    *   **Fibonacci Retracements & Extensions:** Automatically calculated and drawn on the chart.
    *   **EMA Ribbon:** (8, 13, 21, 34, 55) for trend visualization.
    *   **Bollinger Bands (BBands)**
    *   **Keltner Channels (KC)**
    *   **Volume-Weighted Average Price (VWAP)**
    *   **Volatility Squeeze Indicator:** Highlights periods where BBands width is less than KC width.
    *   **Additional Oscillators:** Stochastic, On-Balance Volume (OBV), and Money Flow Index (MFI).
*   **Modern UI Theme:** The entire application has been redesigned with a modern, clean aesthetic, including both Dark (default) and Light themes.
*   **New CLI Commands:**
    *   `rectifex-cli single`: To fetch and analyze a single stock from the command line.
    *   `rectifex-cli search`: To perform a fuzzy search for tickers by company name.
*   **Multi-Sheet Excel Export:** A new feature to export the complete analysis of a single stock to an `.xlsx` file with separate sheets for a summary, OHLCV data, indicators, and signals.
*   **Local Symbol Index:** A local SQLite database is now used to cache ticker names and support fast, fuzzy searching.

### Changed

*   **BREAKING: Single-Search is Always Live:** When using the new Quick Search bar, the application will **always perform a live fetch** from yfinance for the requested ticker. It does not use stale data from the cache for the primary display. If the live fetch fails, it will attempt to fall back to the cache and will display a "Stale Cache" badge.
*   **Project Architecture:** The entire codebase has been refactored from a monolithic structure into a modern, service-oriented architecture, separating UI (`app/`), core logic (`core/`), and command-line interface (`cli/`).
*   **Data Source Constraint:** The application now exclusively uses `yfinance` as its data source, removing the previous dependency on FMP.
*   **Asynchronous Data Loading:** All data fetching and analysis for the single-stock view is now done in a background thread to ensure the UI remains responsive at all times.

### Removed

*   **FMP API Integration:** All code related to the Financial Modeling Prep (FMP) API has been removed. `yfinance` is now the sole data provider.
*   **Old UI Dialogs:** The previous, separate dialogs for charts have been replaced by the integrated `ChartPanel`.