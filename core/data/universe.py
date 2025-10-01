import sqlite3
import pandas as pd
import re
import logging
from rapidfuzz import process, fuzz
from typing import List, Dict, Optional

from core.config import DEFAULT_UNIVERSE
from core.data.loader import fetch_live_metadata

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TICKER_REGEX = re.compile(r'^[A-Z]{1,5}$|[0-9.\-]')

class SymbolIndex:
    """Manages the local SQLite database of ticker symbols and their names."""
    def __init__(self, db_path=None):
        if db_path:
            self.db_path = db_path
        else:
            from core.config import DB_PATH
            self.db_path = DB_PATH
        self._conn = None

    def __enter__(self):
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self.create_table()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            if exc_type is None:
                self._conn.commit()
            self._conn.close()

    def create_table(self):
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    exchange TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def upsert_symbol(self, metadata: dict):
        with self._conn:
            self._conn.execute("""
                INSERT INTO symbols (symbol, name, exchange, updated_at)
                VALUES (:symbol, :name, :exchange, CURRENT_TIMESTAMP)
                ON CONFLICT(symbol) DO UPDATE SET
                    name = excluded.name,
                    exchange = excluded.exchange,
                    updated_at = CURRENT_TIMESTAMP
            """, {'symbol': metadata['symbol'], 'name': metadata.get('longName') or metadata.get('shortName'), 'exchange': metadata.get('exchange')})
        logging.info(f"Upserted {metadata['symbol']} into the symbol index.")

    def get_all_symbols(self) -> List[Dict]:
        with self._conn:
            cursor = self._conn.execute("SELECT symbol, name FROM symbols")
            return [{'symbol': row['symbol'], 'name': row['name']} for row in cursor.fetchall()]

def search_symbol(query: str, top_k: int = 5, score_cutoff: int = 70, index: SymbolIndex = None) -> List[Dict]:
    """Performs a fuzzy search, optionally on a provided index instance."""
    def _search(idx):
        symbols = idx.get_all_symbols()
        if not symbols: return []
        choices = {item['symbol']: item['name'] for item in symbols}
        results = process.extract(query, choices, scorer=fuzz.token_sort_ratio, limit=top_k, score_cutoff=score_cutoff)
        return [{'symbol': r[2], 'name': r[0], 'score': r[1]} for r in results]

    if index:
        return _search(index)
    else:
        with SymbolIndex() as new_index:
            return _search(new_index)

def resolve_symbol(query: str, index: SymbolIndex = None) -> Optional[Dict]:
    """Resolves a query, optionally using a provided index instance."""
    query = query.strip().upper()
    if TICKER_REGEX.search(query):
        logging.info(f"Query '{query}' matches ticker format. Attempting direct live fetch.")
        try:
            metadata = fetch_live_metadata(query)
            # Use the provided index or create a new one to upsert
            if index:
                index.upsert_symbol(metadata)
            else:
                with SymbolIndex() as new_index:
                    new_index.upsert_symbol(metadata)
            return {'symbol': metadata['symbol'], 'name': metadata.get('longName'), 'source': 'exact_live'}
        except IOError as e:
            logging.warning(f"Live fetch for '{query}' failed: {e}. Falling back to search.")
            pass

    logging.info(f"Performing fuzzy search for '{query}'.")
    search_results = search_symbol(query, top_k=1, index=index)
    if search_results:
        resolved = search_results[0]
        logging.info(f"Resolved '{query}' to '{resolved['symbol']}' via fuzzy search with score {resolved['score']}.")
        return {'symbol': resolved['symbol'], 'name': resolved['name'], 'source': 'fuzzy_cache'}

    logging.error(f"Could not resolve query: '{query}'. No exact match or confident fuzzy result.")
    return None

def build_or_refresh_universe(universe_list: List[str] = DEFAULT_UNIVERSE, index: SymbolIndex = None):
    """Populates the index, optionally using a provided instance."""
    def _build(idx):
        for symbol in universe_list:
            try:
                metadata = fetch_live_metadata(symbol)
                idx.upsert_symbol(metadata)
            except IOError as e:
                logging.error(f"Could not fetch metadata for {symbol} during universe build: {e}")

    logging.info(f"Building or refreshing symbol index for {len(universe_list)} symbols.")
    if index:
        _build(index)
    else:
        with SymbolIndex() as new_index:
            _build(new_index)
    logging.info("Symbol index refresh complete.")