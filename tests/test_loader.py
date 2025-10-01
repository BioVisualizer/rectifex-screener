import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

# Adjust path to import from the core directory
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.data.loader import fetch_live_ohlcv, fetch_live_metadata

@pytest.fixture
def mock_yfinance_ticker():
    """Fixture to mock the yfinance.Ticker object."""
    with patch('yfinance.Ticker') as mock_ticker_class:
        mock_ticker_instance = MagicMock()
        mock_ticker_class.return_value = mock_ticker_instance
        yield mock_ticker_instance

def test_fetch_live_ohlcv_success(mock_yfinance_ticker):
    """Test successful fetching of OHLCV data."""
    # Arrange: Mock the history method to return a valid DataFrame
    mock_df = pd.DataFrame({'Close': [100, 101, 102]})
    mock_yfinance_ticker.history.return_value = mock_df

    # Act
    df = fetch_live_ohlcv("AAPL")

    # Assert
    assert not df.empty
    assert df.equals(mock_df)
    mock_yfinance_ticker.history.assert_called_once()

def test_fetch_live_ohlcv_failure_with_retry(mock_yfinance_ticker):
    """Test that fetch_live_ohlcv retries on failure and eventually succeeds."""
    # Arrange: Fail twice, then succeed
    mock_yfinance_ticker.history.side_effect = [Exception("Network Error"), Exception("Throttled"), pd.DataFrame({'Close': [100]})]

    # Act
    df = fetch_live_ohlcv("AAPL", retries=3, backoff_factor=0.01) # Use small backoff for speed

    # Assert
    assert not df.empty
    assert mock_yfinance_ticker.history.call_count == 3

def test_fetch_live_ohlcv_hard_failure(mock_yfinance_ticker):
    """Test that fetch_live_ohlcv raises an IOError after all retries fail."""
    # Arrange: Always fail
    mock_yfinance_ticker.history.side_effect = Exception("Permanent Failure")

    # Act & Assert
    with pytest.raises(IOError, match="Failed to fetch OHLCV data for AAPL after 3 retries."):
        fetch_live_ohlcv("AAPL", retries=3, backoff_factor=0.01)
    assert mock_yfinance_ticker.history.call_count == 3

def test_fetch_live_metadata_success(mock_yfinance_ticker):
    """Test successful fetching of metadata."""
    # Arrange
    mock_yfinance_ticker.fast_info = {'lastPrice': 150, 'currency': 'USD'}
    mock_yfinance_ticker.info = {'longName': 'Apple Inc.', 'exchange': 'NMS'}

    # Act
    metadata = fetch_live_metadata("AAPL")

    # Assert
    assert metadata['longName'] == 'Apple Inc.'
    assert metadata['lastPrice'] == 150
    assert metadata['exchange'] == 'NMS'
    assert 'debtToEquity' not in metadata # Test that None values are filtered

def test_fetch_live_metadata_failure(mock_yfinance_ticker):
    """Test that fetch_live_metadata raises an IOError after all retries fail."""
    # Arrange
    # Make .info a mock that returns None for any .get() call, forcing the failure
    mock_yfinance_ticker.fast_info = {}
    mock_info = MagicMock()
    mock_info.get.return_value = None
    mock_yfinance_ticker.info = mock_info

    # Act & Assert
    with pytest.raises(IOError, match="Failed to fetch metadata for AAPL after 3 retries."):
        fetch_live_metadata("AAPL", retries=3, backoff_factor=0.01)

    # Assert that .get was called on the info object (e.g., for 'longName')
    mock_yfinance_ticker.info.get.assert_any_call('longName', None)