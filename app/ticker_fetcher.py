import requests
import pandas as pd
import json
from pathlib import Path
import datetime
import logging
import urllib.parse

# --- Configuration ---
CACHE_FILE = Path.home() / ".config" / "rectifex" / "tickers.json"
CACHE_DURATION_DAYS = 7

# --- FMP Index Mapping ---
# Maps the user-facing name from the dropdown to the required FMP API symbol or list name
INDEX_MAP = {
    # US Indices (use list names)
    "S&P 500": "sp500-constituent",
    "Nasdaq 100": "nasdaq-constituent",
    "Dow Jones": "dowjones-constituent",
    # German Indices (use URL-encoded symbols)
    "DAX": "%5EGDAXI",    # ^GDAXI
    "MDAX": "%5EMDAXI",   # ^MDAXI
    "SDAX": "%5ESDAXI",   # ^SDAXI
    "TecDAX": "%5ETECDAX" # ^TECDAX
}

# List of indices to include in the "Default List"
DEFAULT_INDICES = ["S&P 500", "Nasdaq 100", "DAX", "MDAX"]

# --- Global Session ---
session = requests.Session()
session.headers.update({'User-Agent': 'RectifexStockScreener/1.1'})


def get_tickers_from_index(index_name: str, api_key: str):
    """
    Fetches the list of tickers for a given index from the FMP API.
    Handles both list-based endpoints and symbol-based index endpoints.
    Returns a list of tickers or None if an error occurs.
    """
    if not api_key:
        logging.error("API key is required to fetch index constituents.")
        return None

    identifier = INDEX_MAP.get(index_name)
    if not identifier:
        logging.error(f"Invalid or unsupported index name specified: {index_name}")
        return None

    # Determine the correct API endpoint to use
    if "-constituent" in identifier:
        # It's a named list like "sp500-constituent"
        url = f"https://financialmodelingprep.com/api/v3/{identifier}?apikey={api_key}"
    else:
        # It's a symbol like "%5EGDAXI"
        url = f"https://financialmodelingprep.com/api/v3/index_constituent/{identifier}?apikey={api_key}"

    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        # The response is a list of dictionaries. For index constituents, the key is 'symbol'.
        # For historical constituents (which some endpoints return), it's in a nested dict.
        tickers = []
        if data and isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'symbol' in item:
                    tickers.append(item['symbol'])

        if not tickers:
            logging.warning(f"API returned no tickers for {index_name}. The response might be empty or in an unexpected format.")
            return []

        logging.info(f"Successfully fetched {len(tickers)} tickers for {index_name}.")
        return sorted(list(set(tickers)))

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed for {index_name}: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON response for {index_name}.")
        return None
    except KeyError:
        logging.error(f"Unexpected JSON structure in response for {index_name}.")
        return None


def get_all_tickers(api_key: str, force_refresh=False):
    """
    Aggregates tickers from all default sources using the FMP API, with caching.
    Requires an API key.
    """
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not api_key:
        logging.error("API key is required to fetch the default ticker list.")
        return []

    # Check cache first
    if not force_refresh and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                cache_date = datetime.datetime.fromisoformat(data['date'])
                if datetime.datetime.now() - cache_date < datetime.timedelta(days=CACHE_DURATION_DAYS):
                    logging.info("Loading default tickers from cache.")
                    return data['tickers']
        except (json.JSONDecodeError, KeyError, ValueError):
             logging.warning("Ticker cache file is invalid or corrupt. Fetching fresh data.")

    logging.info("Fetching fresh default ticker data from FMP API.")
    all_tickers = set()

    for index_name in DEFAULT_INDICES:
        logging.info(f"Fetching constituents for {index_name}...")
        tickers = get_tickers_from_index(index_name, api_key)
        if tickers:
            all_tickers.update(tickers)
        else:
            logging.warning(f"Failed to get tickers for {index_name}, it will be excluded from the default list.")

    # Add a small, static list of important/popular tickers to ensure they are included
    supplementary_tickers = ["NVDA", "PLTR", "GOOGL", "GOOG", "MSFT", "SRT3.DE", "SRT.DE", "HYQ.DE"]
    all_tickers.update(supplementary_tickers)

    sorted_tickers = sorted(list(filter(None, all_tickers)))

    logging.info(f"Saving {len(sorted_tickers)} tickers to cache.")
    with open(CACHE_FILE, 'w') as f:
        json.dump({
            'date': datetime.datetime.now().isoformat(),
            'tickers': sorted_tickers
        }, f, indent=4)

    return sorted_tickers

if __name__ == '__main__':
    # For standalone testing. Requires an API key in a file named 'fmp_api.key'
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    try:
        with open('fmp_api.key', 'r') as f:
            test_api_key = f.read().strip()
        print("--- Testing Ticker Fetcher ---")
        dax_tickers = get_tickers_from_index("DAX", test_api_key)
        print(f"DAX Tickers: {dax_tickers[:5]}... ({len(dax_tickers)} total)")

        all_defaults = get_all_tickers(test_api_key, force_refresh=True)
        print(f"Default Tickers: {all_defaults[:5]}... ({len(all_defaults)} total)")

    except FileNotFoundError:
        print("Could not find fmp_api.key file for testing. Skipping standalone test.")
    except Exception as e:
        print(f"An error occurred during testing: {e}")
