import argparse
import json
import logging
import pandas as pd
import sys
from pathlib import Path

# Adjust path to import from the core directory
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.data.universe import resolve_symbol, search_symbol
from core.data.loader import fetch_live_ohlcv
from core.indicators.engine import IndicatorEngine
from core.signals.engine import SignalsEngine
from core.chart.service import ChartService

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

def handle_single_stock(args):
    """Handler for the 'single' subcommand."""
    print(f"Fetching live data for ticker: {args.ticker}")

    try:
        # --- Data Fetching ---
        ohlcv_df = fetch_live_ohlcv(args.ticker, period=args.period)
        if ohlcv_df.empty:
            print(f"Error: No data returned for {args.ticker}. It may be an invalid ticker.", file=sys.stderr)
            return

        results = {'ticker': args.ticker, 'ohlcv_head': ohlcv_df.head().to_dict()}

        # --- Analysis ---
        if args.include_signals:
            print("Computing indicators and signals...")
            indicator_engine = IndicatorEngine()
            indicators = indicator_engine.compute(ohlcv_df)

            signal_engine = SignalsEngine()
            signals = signal_engine.generate(ohlcv_df, indicators)

            # Convert signals to a serializable format
            results['signals'] = [s.__dict__ for s in signals]
            # Convert timestamps to strings
            for s in results['signals']:
                s['ts'] = s['ts'].isoformat()

        # --- Charting ---
        if args.chart:
            print("Generating chart...")
            chart_service = ChartService()
            chart_path = chart_service.draw(args.ticker, ohlcv_df.tail(252), indicators if args.include_signals else {}, None, {'show_ema_ribbon': True})
            if chart_path:
                results['chart_path'] = chart_path
                print(f"Chart saved to: {chart_path}")
            else:
                print("Warning: Failed to generate chart.", file=sys.stderr)

        # --- Output ---
        if args.out:
            output_path = Path(args.out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Results saved to {output_path}")
        else:
            # Print a summary to stdout if not saving to a file
            print(json.dumps(results, indent=2, default=str))

    except IOError as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.no_fallback:
            sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


def handle_search(args):
    """Handler for the 'search' subcommand."""
    print(f"Searching for query: '{args.query}'")
    results = search_symbol(args.query, topk=args.topk)
    if not results:
        print("No matches found.")
        return

    print(json.dumps(results, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Rectifex Global Screener - Command-Line Interface")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # --- Single Stock Subcommand ---
    parser_single = subparsers.add_parser('single', help='Fetch and analyze a single stock.')
    parser_single.add_argument('--ticker', type=str, required=True, help='The ticker symbol to analyze.')
    parser_single.add_argument('--period', type=str, default='5y', help='The historical data period (e.g., 1y, 5y, max).')
    parser_single.add_argument('--include-signals', action='store_true', help='Compute and include signals in the output.')
    parser_single.add_argument('--chart', action='store_true', help='Generate and save a chart snapshot.')
    parser_single.add_argument('--out', type=str, help='Path to save the output JSON file.')
    parser_single.add_argument('--no-fallback', action='store_true', help='Exit with an error if live fetch fails (no cache fallback).')
    parser_single.set_defaults(func=handle_single_stock)

    # --- Search Subcommand ---
    parser_search = subparsers.add_parser('search', help='Fuzzy search for a stock symbol by name.')
    parser_search.add_argument('--query', type=str, required=True, help='The company name or part of it to search for.')
    parser_search.add_argument('--topk', type=int, default=5, help='The number of top results to return.')
    parser_search.set_defaults(func=handle_search)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()