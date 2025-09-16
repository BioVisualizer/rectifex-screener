import unittest
import sys
sys.path.append('.')
from app import screener_engine

class TestScreenerEngine(unittest.TestCase):

    def test_get_default_tickers(self):
        """
        Tests that get_default_tickers returns a list of tickers
        and that it includes the specifically requested stocks.
        """
        # Force a refresh to ensure we are not using a stale cache
        tickers = screener_engine.get_default_tickers(force_refresh=True)

        # Check that it returns a list
        self.assertIsInstance(tickers, list)

        # Check that the list is not empty
        self.assertGreater(len(tickers), 0)

        # Check for the presence of the requested stocks
        required_stocks = ["NVDA", "PLTR", "GOOGL", "GOOG", "MSFT", "SRT3.DE", "SRT.DE", "HYQ.DE"]
        ticker_set = set(tickers)
        for stock in required_stocks:
            self.assertIn(stock, ticker_set)

if __name__ == '__main__':
    unittest.main()
