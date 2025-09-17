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

# Wikipedia URLs for various global indices
URL_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
URL_NASDAQ100 = "https://en.wikipedia.org/wiki/Nasdaq-100"
URL_DAX = "https://en.wikipedia.org/wiki/DAX"
URL_MDAX = "https://en.wikipedia.org/wiki/MDAX"
URL_TECDAX_DE = "https://de.wikipedia.org/wiki/TecDAX"
URL_SDAX_DE = "https://de.wikipedia.org/wiki/SDAX"
URL_FTSE100 = "https://en.wikipedia.org/wiki/FTSE_100_Index"
URL_CAC40 = "https://en.wikipedia.org/wiki/CAC_40"
URL_NIKKEI225 = "https://en.wikipedia.org/wiki/Nikkei_225"
URL_TSX_COMPOSITE = "https://en.wikipedia.org/wiki/List_of_companies_in_the_S%26P/TSX_Composite_Index"


# --- Global Session ---
session = requests.Session()
session.headers.update({'User-Agent': 'RectifexStockScreener/1.2'})


def _fetch_html(url):
    """Fetches HTML content from a URL."""
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logging.error(f"Failed to fetch HTML from {url}: {e}")
        return None

# --- Ticker Scraping Functions for Each Index ---

def get_sp500_tickers():
    html = _fetch_html(URL_SP500)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        sp500_table = tables[0]
        return sp500_table['Symbol'].str.replace('.', '-', regex=False).tolist()
    except Exception as e:
        logging.error(f"Could not parse S&P 500 table: {e}")
        return []

def get_nasdaq100_tickers():
    html = _fetch_html(URL_NASDAQ100)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        nasdaq_table = tables[4]
        return nasdaq_table['Ticker'].tolist()
    except Exception as e:
        logging.error(f"Could not parse Nasdaq 100 table: {e}")
        return []

def get_dax_tickers():
    html = _fetch_html(URL_DAX)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        dax_table = tables[4]
        return dax_table['Ticker'].tolist()
    except Exception as e:
        logging.error(f"Could not parse DAX table: {e}")
        return []

def get_mdax_tickers():
    html = _fetch_html(URL_MDAX)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        mdax_table = tables[2]
        tickers = mdax_table['Symbol'].dropna().tolist()
        processed_tickers = [f"{t}.DE" if not any(t.endswith(s) for s in ['.DE','.LU','.PA','.AS']) else t for t in tickers if isinstance(t, str)]
        return processed_tickers
    except Exception as e:
        logging.error(f"Could not parse MDAX table: {e}")
        return []

def get_ftse100_tickers():
    html = _fetch_html(URL_FTSE100)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        ftse_table = tables[3]
        return ftse_table['Ticker'].tolist()
    except Exception as e:
        logging.error(f"Could not parse FTSE 100 table: {e}")
        return []

def get_cac40_tickers():
    html = _fetch_html(URL_CAC40)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        cac_table = tables[4]
        return cac_table['Ticker'].tolist()
    except Exception as e:
        logging.error(f"Could not parse CAC 40 table: {e}")
        return []

def get_nikkei225_tickers():
    html = _fetch_html(URL_NIKKEI225)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        nikkei_table = tables[1]
        return (nikkei_table['Ticker symbol'].astype(str) + '.T').tolist()
    except Exception as e:
        logging.error(f"Could not parse Nikkei 225 table: {e}")
        return []

def get_tsx_composite_tickers():
    html = _fetch_html(URL_TSX_COMPOSITE)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        tsx_table = tables[0]
        return tsx_table['Symbol'].str.replace('.', '-', regex=False).tolist()
    except Exception as e:
        logging.error(f"Could not parse S&P/TSX Composite table: {e}")
        return []

# --- Functions requiring Yahoo Finance search (slower) ---

def _search_ticker_yahoo(company_name):
    search_url = f"https://query1.finance.yahoo.com/v1/finance/search"
    params = {'q': company_name, 'quotesCount': 1, 'newsCount': 0}
    try:
        time.sleep(0.5)
        response = session.get(search_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get('quotes'):
            return data['quotes'][0]['symbol']
    except Exception as e:
        logging.error(f"Yahoo Finance search failed for '{company_name}': {e}")
    return None

def get_companies_from_german_wiki(url):
    html = _fetch_html(url)
    if not html: return []
    try:
        tables = pd.read_html(io.StringIO(html))
        for table in tables:
            if 'Name' in table.columns and 'Branche' in table.columns:
                return table['Name'].str.replace(r'\[.*?\]', '', regex=True).str.strip().tolist()
    except Exception as e:
        logging.error(f"Could not parse table from {url}: {e}")
    return []

def get_tecdax_tickers():
    companies = get_companies_from_german_wiki(URL_TECDAX_DE)
    return [t for t in (_search_ticker_yahoo(c) for c in companies) if t]

def get_sdax_tickers():
    companies = get_companies_from_german_wiki(URL_SDAX_DE)
    return [t for t in (_search_ticker_yahoo(c) for c in companies) if t]

# --- Main Aggregator Function ---

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
                if datetime.datetime.now() - datetime.datetime.fromisoformat(data['date']) < datetime.timedelta(days=CACHE_DURATION_DAYS):
                    logging.info("Loading tickers from cache.")
                    return data['tickers']
        except (json.JSONDecodeError, KeyError, ValueError):
             logging.warning("Ticker cache file is invalid. Fetching fresh data.")

    logging.info("Fetching fresh global ticker data from Wikipedia and Yahoo Finance.")
    all_tickers = set()

    # Add tickers from all implemented scrapers
    all_tickers.update(get_sp500_tickers())
    all_tickers.update(get_nasdaq100_tickers())
    all_tickers.update(get_ftse100_tickers())
    all_tickers.update(get_cac40_tickers())
    all_tickers.update(get_nikkei225_tickers())
    all_tickers.update(get_tsx_composite_tickers())
    all_tickers.update(get_dax_tickers())
    all_tickers.update(get_mdax_tickers())
    all_tickers.update(get_tecdax_tickers())
    all_tickers.update(get_sdax_tickers())

    sorted_tickers = sorted(list(filter(None, all_tickers)))

    logging.info(f"Saving {len(sorted_tickers)} global tickers to cache.")
    with open(CACHE_FILE, 'w') as f:
        json.dump({'date': datetime.datetime.now().isoformat(), 'tickers': sorted_tickers}, f)

    return sorted_tickers
