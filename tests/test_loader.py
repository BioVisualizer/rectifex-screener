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
    # Arrange: Mock the history method to return a valid DataFrame with all required columns
    mock_df = pd.DataFrame({
        'Open': [99, 100, 101],
        'High': [101, 102, 103],
        'Low': [98, 99, 100],
        'Close': [100, 101, 102],
        'Volume': [1e6, 1.1e6, 1.2e6]
    }, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
    mock_yfinance_ticker.history.return_value = mock_df

    # Act
    df = fetch_live_ohlcv("AAPL")

    # Assert
    assert not df.empty
    # The function now returns a DataFrame with a DatetimeIndex, so we can do a full comparison
    pd.testing.assert_frame_equal(df, mock_df)
    mock_yfinance_ticker.history.assert_called_once()

def test_fetch_live_ohlcv_failure_with_retry(mock_yfinance_ticker):
    """Test that fetch_live_ohlcv retries on failure and eventually succeeds."""
    # Arrange: Fail twice, then succeed with a valid DataFrame
    mock_df_success = pd.DataFrame({
        'Open': [99], 'High': [101], 'Low': [98], 'Close': [100], 'Volume': [1e6]
    }, index=pd.to_datetime(['2023-01-01']))
    mock_yfinance_ticker.history.side_effect = [Exception("Network Error"), Exception("Throttled"), mock_df_success]

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
    # Arrange: Mock the .info attribute with a dictionary containing all expected keys
    mock_info_data = {
        'longName': 'Apple Inc.',
        'exchange': 'NMS',
        'marketCap': 2e12,
        'trailingPE': 30.5,
        'forwardPE': 25.5,
        'dividendYield': 0.005,
        'debtToEquity': 150.0,
        'currency': 'USD'
    }
    mock_yfinance_ticker.info = mock_info_data

    # Act
    metadata = fetch_live_metadata("AAPL")

    # Assert
    assert metadata['longName'] == 'Apple Inc.'
    assert metadata['marketCap'] == 2e12
    assert metadata['exchange'] == 'NMS'
    # Check that a key with a value is present
    assert 'debtToEquity' in metadata

def test_fetch_live_metadata_failure(mock_yfinance_ticker):
    """Test that fetch_live_metadata raises an IOError after all retries fail."""
    # Arrange: Mock the .info to raise an exception, simulating a network failure
    mock_yfinance_ticker.info = Exception("Network error")

    # Act & Assert
    with pytest.raises(IOError, match="Failed to fetch metadata for AAPL after 3 retries."):
        fetch_live_metadata("AAPL", retries=3, backoff_factor=0.01)