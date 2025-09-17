import pytest
import pandas as pd
import requests
from unittest.mock import MagicMock

# Import the functions to be tested
from screener_engine import get_exchange_rates, convert_to_usd

# --- Test Data ---

@pytest.fixture
def mock_rates_response():
    """Fixture to provide a mock successful response from the exchange rate API."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "amount": 1.0,
        "base": "USD",
        "date": "2024-01-01",
        "rates": {
            "EUR": 0.9,
            "GBP": 0.8,
            "JPY": 150.0
        }
    }
    return mock_resp

@pytest.fixture
def clean_cache():
    """A fixture to ensure the exchange rate cache is clean before and after a test."""
    from screener_engine import RATES_CACHE_FILE
    if RATES_CACHE_FILE.exists():
        RATES_CACHE_FILE.unlink()

    yield # This passes control to the test function

    if RATES_CACHE_FILE.exists():
        RATES_CACHE_FILE.unlink()

# --- Tests for get_exchange_rates ---

def test_get_exchange_rates_success(mocker, mock_rates_response, clean_cache):
    """Test that exchange rates are fetched and parsed correctly on a successful API call."""
    # Mock the requests.get call to return our mock response
    mocker.patch('requests.get', return_value=mock_rates_response)

    # Call the function
    rates = get_exchange_rates()

    # Assertions
    assert "EUR" in rates
    assert rates["EUR"] == 0.9
    assert rates["USD"] == 1.0  # Check that the base currency is added
    assert len(rates) == 4

def test_get_exchange_rates_api_failure(mocker, clean_cache):
    """Test that the function returns an empty dict when the API call fails."""
    # Mock requests.get to raise a RequestException
    mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("API is down"))

    rates = get_exchange_rates()

    assert rates == {}

def test_get_exchange_rates_caching(mocker, mock_rates_response, clean_cache):
    """Test that the API call is cached and not made on a second call."""
    mock_get = mocker.patch('requests.get', return_value=mock_rates_response)

    # First call - should call the API
    rates1 = get_exchange_rates()
    assert mock_get.call_count == 1
    assert "EUR" in rates1

    # Second call - should load from cache, not call the API again
    rates2 = get_exchange_rates()
    assert mock_get.call_count == 1  # Assert that the mock was NOT called again
    assert rates1 == rates2


# --- Tests for convert_to_usd ---

def test_convert_to_usd_with_eur():
    """Test conversion for a standard currency (EUR)."""
    sample_row = pd.Series({'MarketCap': 100_000_000, 'Currency': 'EUR'})
    exchange_rates = {'EUR': 0.9, 'USD': 1.0}

    result = convert_to_usd(sample_row, exchange_rates)

    assert result == 90_000_000

def test_convert_to_usd_with_gbp():
    """Test conversion for British Pence (GBp), which requires special handling."""
    sample_row = pd.Series({'MarketCap': 50_000_000, 'Currency': 'GBp'})
    exchange_rates = {'GBP': 0.8, 'USD': 1.0}

    # The function should convert 50M pence to 500k pounds, then apply the 0.8 rate
    result = convert_to_usd(sample_row, exchange_rates)

    assert result == (50_000_000 / 100.0) * 0.8
    assert result == 400_000

def test_convert_to_usd_with_missing_rate():
    """Test that if a currency is not in the rates dict, it defaults to a 1.0 rate."""
    sample_row = pd.Series({'MarketCap': 123_456, 'Currency': 'XYZ'})
    exchange_rates = {'EUR': 0.9, 'USD': 1.0}

    result = convert_to_usd(sample_row, exchange_rates)

    assert result == 123_456 # Should return the original market cap

def test_convert_to_usd_with_usd():
    """Test that USD is correctly handled (rate of 1.0)."""
    sample_row = pd.Series({'MarketCap': 987_654, 'Currency': 'USD'})
    exchange_rates = {'EUR': 0.9, 'USD': 1.0}

    result = convert_to_usd(sample_row, exchange_rates)

    assert result == 987_654
