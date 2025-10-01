import pytest
from unittest.mock import patch, MagicMock

# Adjust path to import from the core directory
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.data.universe import SymbolIndex, search_symbol, resolve_symbol

@pytest.fixture
def populated_index(tmp_path):
    """
    Fixture to create and yield a populated SymbolIndex instance.
    The key is to explicitly commit the data before yielding so the test
    functions can access the committed state.
    """
    db_path = tmp_path / "test_universe.sqlite"
    with SymbolIndex(db_path=db_path) as index:
        index.upsert_symbol({'symbol': 'AAPL', 'longName': 'Apple Inc.', 'exchange': 'NASDAQ'})
        index.upsert_symbol({'symbol': 'MSFT', 'longName': 'Microsoft Corporation', 'exchange': 'NASDAQ'})
        index.upsert_symbol({'symbol': 'ASML', 'longName': 'ASML Holding N.V.', 'exchange': 'AMS'})

        # This is the critical step: commit the transaction before the test runs.
        index._conn.commit()

        yield index

def test_symbol_index_creation(populated_index):
    """Test that the SymbolIndex can be created and populated."""
    symbols = populated_index.get_all_symbols()
    assert len(symbols) == 3

def test_search_symbol_fuzzy_match(populated_index):
    """Test fuzzy search for symbols using the injected index."""
    results = search_symbol("Apple", index=populated_index)
    assert len(results) > 0
    assert results[0]['symbol'] == 'AAPL'
    assert results[0]['score'] > 90

def test_search_symbol_no_match(populated_index):
    """Test fuzzy search with a query that should not match."""
    results = search_symbol("NonExistentCompany", index=populated_index)
    assert len(results) == 0

@patch('core.data.universe.fetch_live_metadata')
def test_resolve_symbol_exact_ticker_live_fetch(mock_fetch_live_metadata, populated_index):
    """Test that resolve_symbol calls fetch_live_metadata for an exact ticker."""
    mock_fetch_live_metadata.return_value = {'symbol': 'NVDA', 'longName': 'NVIDIA Corporation'}

    result = resolve_symbol("NVDA", index=populated_index)

    mock_fetch_live_metadata.assert_called_once_with("NVDA")
    assert result['symbol'] == 'NVDA'
    assert result['source'] == 'exact_live'
    assert len(populated_index.get_all_symbols()) == 4

@patch('core.data.universe.fetch_live_metadata')
def test_resolve_symbol_live_fetch_fails_falls_back_to_fuzzy(mock_fetch_live_metadata, populated_index):
    """Test that if live fetch fails, it falls back to a fuzzy search."""
    mock_fetch_live_metadata.side_effect = IOError("Network error")

    result = resolve_symbol("ASML", index=populated_index)

    mock_fetch_live_metadata.assert_called_once_with("ASML")
    assert result is not None
    assert result['symbol'] == 'ASML'
    assert result['source'] == 'fuzzy_cache'

@patch('core.data.universe.fetch_live_metadata')
def test_resolve_symbol_non_ticker_query_uses_fuzzy(mock_fetch_live_metadata, populated_index):
    """
    Test that a non-ticker-like query skips live fetch and goes directly to fuzzy search.
    """
    result = resolve_symbol("Microsoft", index=populated_index)

    mock_fetch_live_metadata.assert_not_called()
    assert result is not None
    assert result['symbol'] == 'MSFT'
    assert result['source'] == 'fuzzy_cache'