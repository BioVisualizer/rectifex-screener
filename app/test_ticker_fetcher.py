import pytest
import requests
from unittest.mock import MagicMock

# Import the function to be tested
from ticker_fetcher import get_tickers_from_index

# --- Test Data ---

@pytest.fixture
def mock_fmp_list_response():
    """Fixture for a successful response from an FMP list endpoint (e.g., S&P 500)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "MSFT", "name": "Microsoft Corporation"},
        {"symbol": "GOOG", "name": "Alphabet Inc."}
    ]
    return mock_resp

@pytest.fixture
def mock_fmp_index_response():
    """Fixture for a successful response from an FMP index endpoint (e.g., DAX)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"symbol": "SAP.DE", "name": "SAP SE"},
        {"symbol": "SIE.DE", "name": "Siemens AG"},
        {"symbol": "AIR.DE", "name": "Airbus SE"}
    ]
    return mock_resp

# --- Tests ---

def test_get_tickers_from_sp500(mocker, mock_fmp_list_response):
    """Test fetching from a named list endpoint like S&P 500."""
    mock_get = mocker.patch('requests.Session.get', return_value=mock_fmp_list_response)

    tickers = get_tickers_from_index("S&P 500", "dummy_api_key")

    # Check that the correct URL was called
    expected_url = "https://financialmodelingprep.com/api/v3/sp500-constituent?apikey=dummy_api_key"
    mock_get.assert_called_once_with(expected_url, timeout=15)

    # Check that the tickers were parsed correctly
    assert tickers is not None
    assert len(tickers) == 3
    assert "AAPL" in tickers
    assert "MSFT" in tickers

def test_get_tickers_from_dax(mocker, mock_fmp_index_response):
    """Test fetching from a symbol-based index endpoint like DAX."""
    mock_get = mocker.patch('requests.Session.get', return_value=mock_fmp_index_response)

    tickers = get_tickers_from_index("DAX", "dummy_api_key")

    # Check that the correct URL was called
    expected_url = "https://financialmodelingprep.com/api/v3/index_constituent/%5EGDAXI?apikey=dummy_api_key"
    mock_get.assert_called_once_with(expected_url, timeout=15)

    # Check that the tickers were parsed correctly
    assert tickers is not None
    assert len(tickers) == 3
    assert "SAP.DE" in tickers
    assert "SIE.DE" in tickers

def test_get_tickers_api_failure(mocker):
    """Test that the function returns None when the API call fails."""
    mocker.patch('requests.Session.get', side_effect=requests.exceptions.RequestException("API is down"))

    tickers = get_tickers_from_index("S&P 500", "dummy_api_key")

    assert tickers is None

def test_get_tickers_no_key():
    """Test that the function returns None if no API key is provided."""
    tickers = get_tickers_from_index("S&P 500", None)
    assert tickers is None

    tickers_empty = get_tickers_from_index("S&P 500", "")
    assert tickers_empty is None

def test_get_tickers_invalid_index():
    """Test that the function returns None for an unsupported index name."""
    tickers = get_tickers_from_index("Fake Index 999", "dummy_api_key")
    assert tickers is None
