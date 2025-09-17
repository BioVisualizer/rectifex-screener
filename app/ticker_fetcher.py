import requests
import pandas as pd
import json
from pathlib import Path
import datetime
import logging
import io
import time

# --- Configuration ---
CACHE_FILE = Path.home() / ".config" / "rectifex" / "tickers.json"
CACHE_DURATION_DAYS = 7

# Wikipedia URLs
URL_DAX = "https://en.wikipedia.org/wiki/DAX"
URL_MDAX = "https://en.wikipedia.org/wiki/MDAX"
URL_TECDAX_DE = "https://de.wikipedia.org/wiki/TecDAX"
URL_SDAX_DE = "https://de.wikipedia.org/wiki/SDAX"
URL_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# --- Global Session ---
session = requests.Session()
session.headers.update({'User-Agent': 'RectifexStockScreener/1.0'})


def _fetch_html(url):
    """Fetches HTML content from a URL."""
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logging.error(f"Failed to fetch HTML from {url}: {e}")
        return None

def get_sp500_tickers():
    """Fetches S&P 500 tickers from Wikipedia."""
    html = _fetch_html(URL_SP500)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        sp500_table = tables[0]
        # The symbol column sometimes has dots, which yfinance expects as dashes
        return sp500_table['Symbol'].str.replace('.', '-', regex=False).tolist()
    except Exception as e:
        logging.error(f"Could not parse S&P 500 table: {e}")
        return []

def get_dax_tickers():
    """Fetches DAX tickers from Wikipedia."""
    html = _fetch_html(URL_DAX)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        # This index can change, it's a risk of this method
        dax_table = tables[4]
        return dax_table['Ticker'].tolist()
    except Exception as e:
        logging.error(f"Could not parse DAX table: {e}")
        return []

def get_mdax_tickers():
    """Fetches MDAX tickers from Wikipedia."""
    html = _fetch_html(URL_MDAX)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        mdax_table = tables[2]
        tickers = mdax_table['Symbol'].dropna().tolist()
        # Add .DE suffix if missing, as is common for German listings
        processed_tickers = []
        for ticker in tickers:
            if isinstance(ticker, str):
                if not any(ticker.endswith(suffix) for suffix in ['.DE', '.LU', '.PA', '.AS']):
                    processed_tickers.append(f"{ticker}.DE")
                else:
                    processed_tickers.append(ticker)
        return processed_tickers
    except Exception as e:
        logging.error(f"Could not parse MDAX table: {e}")
        return []

def get_companies_from_german_wiki(url):
    """Helper to get company names from German Wikipedia index pages."""
    html = _fetch_html(url)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        for table in tables:
            # Look for a table with these specific columns
            if 'Name' in table.columns and 'Branche' in table.columns:
                # Remove citations like [2] from names
                return table['Name'].str.replace(r'\[.*?\]', '', regex=True).str.strip().tolist()
        logging.error(f"Could not find a valid company table in {url}")
        return []
    except Exception as e:
        logging.error(f"Could not parse table from {url}: {e}")
        return []

def _search_ticker_yahoo(company_name):
    """Searches Yahoo Finance for a ticker symbol for a given company name."""
    search_url = f"https://query1.finance.yahoo.com/v1/finance/search"
    params = {'q': company_name, 'quotesCount': 1, 'newsCount': 0}
    try:
        # Add a delay to avoid getting rate-limited
        time.sleep(0.5)
        response = session.get(search_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get('quotes'):
            ticker = data['quotes'][0]['symbol']
            logging.info(f"Found ticker '{ticker}' for company '{company_name}'")
            return ticker
        else:
            logging.warning(f"No ticker found for company '{company_name}' on Yahoo Finance.")
            return None
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        logging.error(f"Yahoo Finance search failed for '{company_name}': {e}")
        return None

def get_tecdax_tickers():
    """Fetches TecDAX tickers by looking up company names."""
    companies = get_companies_from_german_wiki(URL_TECDAX_DE)
    tickers = set()
    for company in companies:
        ticker = _search_ticker_yahoo(company)
        if ticker:
            tickers.add(ticker)
    return sorted(list(tickers))

def get_sdax_tickers():
    """Fetches SDAX tickers by looking up company names."""
    companies = get_companies_from_german_wiki(URL_SDAX_DE)
    tickers = set()
    for company in companies:
        ticker = _search_ticker_yahoo(company)
        if ticker:
            tickers.add(ticker)
    return sorted(list(tickers))


def get_all_tickers(force_refresh=False):
    """
    Aggregates tickers from all Wikipedia sources, using a cache file.
    This function does NOT require an API key.
    """
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not force_refresh and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                cache_date = datetime.datetime.fromisoformat(data['date'])
                if datetime.datetime.now() - cache_date < datetime.timedelta(days=CACHE_DURATION_DAYS):
                    logging.info("Loading tickers from cache.")
                    return data['tickers']
        except (json.JSONDecodeError, KeyError, ValueError):
             logging.warning("Ticker cache file is invalid or corrupt. Fetching fresh data.")

    logging.info("Fetching fresh ticker data from Wikipedia and Yahoo Finance.")
    all_tickers = set()

    all_tickers.update(get_sp500_tickers())
    all_tickers.update(get_dax_tickers())
    all_tickers.update(get_mdax_tickers())
    all_tickers.update(get_tecdax_tickers())
    all_tickers.update(get_sdax_tickers())

    # Add back the small, static list of important tickers
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
