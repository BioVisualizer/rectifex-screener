import requests
import pandas as pd
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import configparser
from pathlib import Path
import os
import time
import json
import ticker_fetcher

# --- Global Configuration ---
APPROX_RATES = {
    'EUR': 1.08, 'JPY': 0.0064, 'GBP': 1.27, 'CAD': 0.73, 'CHF': 1.12,
    'AUD': 0.66, 'HKD': 0.13, 'BRL': 0.18, 'DKK': 0.14, 'SEK': 0.096,
    'NOK': 0.094, 'INR': 0.012, 'KRW': 0.00072, 'CNY': 0.14, 'GBp': 0.0127
}

CONFIG_DIR = Path.home() / ".config" / "rectifex"
STRATEGIES_FILE = CONFIG_DIR / "strategies.json"

def get_strategy_definitions():
    """
    Loads strategy definitions from strategies.json.
    If the file doesn't exist, it creates a default one.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not STRATEGIES_FILE.exists():
        default_strategies = {
          "Balanced": {
            "weights": {"Quality_Score": 0.30, "Value_Score": 0.25, "Growth_Score": 0.20, "Momentum_Score": 0.10, "Yield_Score": 0.10, "Safety_Score": 0.05},
            "predefined": True
          },
          "Deep Value": {
            "weights": {"Value_Score": 0.70, "Safety_Score": 0.20, "Yield_Score": 0.10},
            "predefined": True
          },
          "High Growth": {
            "weights": {"Growth_Score": 0.60, "Quality_Score": 0.30, "Momentum_Score": 0.10},
            "predefined": True
          },
          "Quality Dividend": {
            "weights": {"Yield_Score": 0.50, "Quality_Score": 0.30, "Safety_Score": 0.20},
            "predefined": True
          }
        }
        save_strategy_definitions(default_strategies)
        return default_strategies
    else:
        with open(STRATEGIES_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logging.error("Could not decode strategies.json. Returning empty dict.")
                return {}

def save_strategy_definitions(strategies):
    """Saves the strategy definitions to strategies.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(STRATEGIES_FILE, 'w') as f:
        json.dump(strategies, f, indent=4)

def get_default_tickers(force_refresh=False):
    """
    Returns a comprehensive list of tickers from multiple major indices,
    fetched and cached by the ticker_fetcher module.
    """
    logging.info("Using ticker_fetcher to get default tickers.")
    return ticker_fetcher.get_all_tickers(force_refresh=force_refresh)

def get_tickers_from_index(index_name, api_key):
    """
    Fetches the list of tickers for a given index from the FMP API.
    Returns a list of tickers or None if an error occurs.
    """
    if not api_key:
        logging.error("API key is required to fetch index constituents.")
        return None

    index_map = {
        "S&P 500": "sp500-constituent",
        "Nasdaq 100": "nasdaq-constituent",
        "Dow Jones": "dowjones-constituent"
    }

    endpoint = index_map.get(index_name)
    if not endpoint:
        logging.error(f"Invalid index name specified: {index_name}")
        return None

    url = f"https://financialmodelingprep.com/api/v3/{endpoint}?apikey={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()

        # The response is a list of dictionaries, each with a 'symbol' key.
        tickers = [item['symbol'] for item in data]
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


def safe_float(value, default=np.nan):
    try: return float(value) if pd.notna(value) else default
    except (ValueError, TypeError): return default

def calculate_metrics_fmp(ticker, api_key):
    try:
        metrics = {'Ticker': ticker}

        # 1. Profile for basic info
        profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={api_key}"
        profile_data = requests.get(profile_url).json()
        if not profile_data: return {"error": f"{ticker}: Not found on FMP."}
        profile = profile_data[0]

        metrics['Name'] = profile.get('companyName', '')[:40]
        metrics['Sector'] = profile.get('sector', 'N/A')
        metrics['Country'] = profile.get('country', 'N/A')
        metrics['MarketCap'] = profile.get('mktCap', 0)
        metrics['Currency'] = profile.get('currency', 'USD')

        # 2. Ratios for PE, PB, DivYield, Debt/Equity
        ratios_url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{ticker}?apikey={api_key}"
        ratios_data = requests.get(ratios_url).json()
        if not ratios_data: return {"error": f"{ticker}: Ratios not available."}
        ratios = ratios_data[0]

        metrics['PE'] = ratios.get('priceEarningsRatioTTM')
        metrics['PB'] = ratios.get('priceToBookRatioTTM')
        metrics['DivYield'] = ratios.get('dividendYieldTTM', 0) * 100 if ratios.get('dividendYieldTTM') else 0.0
        metrics['DebtEquity'] = ratios.get('debtEquityRatioTTM')

        # 3. Financial statements for ROE and Revenue Growth
        financials_url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?period=annual&limit=4&apikey={api_key}"
        financials_data = requests.get(financials_url).json()

        balance_sheet_url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?period=annual&limit=4&apikey={api_key}"
        balance_data = requests.get(balance_sheet_url).json()

        if financials_data and len(financials_data) >= 3:
            rev_now = safe_float(financials_data[0].get('revenue'))
            rev_3y_ago = safe_float(financials_data[2].get('revenue'))
            if rev_now > 0 and rev_3y_ago > 0:
                metrics['RevGrowth3YCAGR'] = ((rev_now / rev_3y_ago) ** (1/3) - 1) * 100

        if financials_data and balance_data:
            roes = []
            for i in range(min(3, len(financials_data), len(balance_data))):
                ni = safe_float(financials_data[i].get('netIncome'))
                equity = safe_float(balance_data[i].get('totalStockholdersEquity'))
                if ni is not None and equity is not None and equity > 0:
                    roes.append((ni / equity) * 100)
            if roes:
                metrics['ROE_Avg3Y'] = np.mean(roes)

        # 4. Historical prices for Momentum and Volatility
        hist_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?timeseries=252&apikey={api_key}"
        hist_data = requests.get(hist_url).json()
        if hist_data and 'historical' in hist_data and len(hist_data['historical']) >= 126:
            prices = pd.DataFrame(hist_data['historical'])['close']
            metrics['Momentum6M'] = ((prices.iloc[0] / prices.iloc[125]) - 1) * 100
            metrics['Volatility'] = prices.pct_change().std() * np.sqrt(252) * 100

        return metrics

    except Exception as e:
        logging.error(f"FMP data fetch failed for {ticker}: {e}")
        return {"error": f"{ticker}: {type(e).__name__}"}

def calculate_metrics_yfinance(ticker_symbol):
    try:
        time.sleep(0.1) # Add a delay to avoid throttling
        ticker = yf.Ticker(ticker_symbol); info = ticker.info
        if not info or info.get('quoteType') != 'EQUITY' or info.get('marketCap') is None: return None
        currency = info.get('currency', 'N/A')
        if currency == 'GBp': currency = 'GBP'
        metrics = {'Ticker': ticker_symbol, 'Name': info.get('longName', info.get('shortName', ''))[:40],'Sector': info.get('sector', 'N/A'), 'Country': info.get('country', 'N/A'),'MarketCap': safe_float(info.get('marketCap', 0)), 'Currency': currency}
        metrics['PE'] = safe_float(info.get('trailingPE')); metrics['PB'] = safe_float(info.get('priceToBook'))
        price = info.get('regularMarketPrice', info.get('currentPrice')); dividend_rate = info.get('dividendRate'); div_yield = 0.0
        if price and dividend_rate and price > 0:
            calculated_yield = (safe_float(dividend_rate) / price) * 100
            if 0 <= calculated_yield < 25.0: div_yield = calculated_yield
        metrics['DivYield'] = div_yield
        hist = ticker.history(period='1y', auto_adjust=True)
        if not hist.empty and len(hist) > 126:
            metrics['Momentum6M'] = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-126]) - 1) * 100
            metrics['Volatility'] = hist['Close'].pct_change().std() * np.sqrt(252) * 100
        financials = ticker.financials; balance_sheet = ticker.balance_sheet
        if not financials.empty and not balance_sheet.empty:
            if 'Total Revenue' in financials.index and len(financials.columns) >= 3:
                rev_now = safe_float(financials.loc['Total Revenue'].iloc[0]); rev_3y_ago = safe_float(financials.loc['Total Revenue'].iloc[2])
                if rev_now > 0 and rev_3y_ago > 0: metrics['RevGrowth3YCAGR'] = ((rev_now / rev_3y_ago) ** (1 / 3) - 1) * 100
            if 'Net Income' in financials.index and 'Stockholders Equity' in balance_sheet.index and len(balance_sheet.columns) >= 3:
                roes = []
                for i in range(min(3, len(financials.columns))):
                    ni = safe_float(financials.loc['Net Income'].iloc[i]); equity = safe_float(balance_sheet.loc['Stockholders Equity'].iloc[i])
                    if pd.notna(ni) and pd.notna(equity) and equity > 0: roes.append((ni / equity) * 100)
                if roes: metrics['ROE_Avg3Y'] = np.mean(roes)
            if 'Total Liab' in balance_sheet.index and 'Stockholders Equity' in balance_sheet.index:
                liabilities = safe_float(balance_sheet.loc['Total Liab'].iloc[0]); equity = safe_float(balance_sheet.loc['Stockholders Equity'].iloc[0])
                if pd.notna(liabilities) and pd.notna(equity) and equity > 0: metrics['DebtEquity'] = liabilities / equity
        return metrics
    except Exception as e: return None

def run_complete_screener(strategy, tickers, api_key, progress_callback, worker=None):
    all_tickers = tickers; total_tickers = len(all_tickers); results = []; failed_list = []

    use_fmp = api_key is not None and len(api_key) > 10
    fetch_function = calculate_metrics_fmp if use_fmp else calculate_metrics_yfinance

    with ThreadPoolExecutor(max_workers=8) as executor:
        if use_fmp:
            future_to_ticker = {executor.submit(fetch_function, ticker, api_key): ticker for ticker in all_tickers}
        else:
            future_to_ticker = {executor.submit(fetch_function, ticker): ticker for ticker in all_tickers}

        for i, future in enumerate(as_completed(future_to_ticker)):
            if worker and worker.is_stopped():
                # Cancel all pending futures
                for f in future_to_ticker:
                    f.cancel()
                # We need to drain the futures to avoid issues, but with a timeout
                for f in as_completed(future_to_ticker, timeout=0.5):
                    pass
                logging.info("Scan stopped by user.")
                return None # Indicate that the scan was stopped

            ticker = future_to_ticker[future]
            progress_callback.emit((i + 1, total_tickers, ticker))
            try:
                result = future.result(timeout=20)
                if result:
                    if "error" in result:
                        failed_list.append(result["error"])
                    else:
                        results.append(result)
                else:
                    failed_list.append(f"{ticker}: No data returned.")
            except Exception as e:
                failed_list.append(f"{ticker}: Data request failed ({type(e).__name__}).")
                logging.warning(f"Ticker {ticker} caused an exception: {e}")

    if worker and worker.is_stopped():
        return None

    if not results:
        summary = { "total_tickers": total_tickers, "initial_count": 0, "failed_count": len(failed_list), "final_count": 0, "failed_list": failed_list }
        return (pd.DataFrame(), summary)

    df = pd.DataFrame(results); initial_count = len(df)
    df['MarketCapUSD'] = df.apply(lambda row: row['MarketCap'] * APPROX_RATES.get(row['Currency'], 1.0) if row['Currency'] != 'USD' else row['MarketCap'], axis=1)
    df['NormalizedName'] = df['Name'].str.lower().str.replace(r' inc| corporation| corp| plc| se| sa| ag| ltd| limited| group| holdings| n\\.v\\.', '', regex=True).str.strip()
    df = df.sort_values('MarketCapUSD', ascending=False).drop_duplicates(subset=['NormalizedName'], keep='first')
    df = df[df['PE'].isnull() | (df['PE'] > 0)].copy(); final_count = len(df)

    summary_details = {
        "total_tickers": total_tickers, "initial_count": initial_count,
        "failed_count": len(failed_list), "final_count": final_count,
        "failed_list": failed_list
    }
    metrics_to_rank = {'ROE_Avg3Y': False, 'PE': True, 'PB': True, 'RevGrowth3YCAGR': False, 'Momentum6M': False, 'DivYield': False, 'Volatility': True, 'DebtEquity': True}
    for col, asc in metrics_to_rank.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.dropna(subset=[col])
            df[col] = df[col].clip(lower=df[col].quantile(0.02), upper=df[col].quantile(0.98))
            df[f'Rank_{col}'] = df[col].rank(ascending=asc, pct=True) * 100

    base_scores = {'Quality_Score': {'ROE_Avg3Y': 1.0},'Value_Score': {'PE': 0.5, 'PB': 0.5},'Growth_Score': {'RevGrowth3YCAGR': 1.0},'Momentum_Score': {'Momentum6M': 1.0},'Yield_Score': {'DivYield': 1.0},'Safety_Score': {'Volatility': 0.5, 'DebtEquity': 0.5}}
    for style, weights in base_scores.items():
        score_sum = pd.Series(0, index=df.index, dtype=float)
        for metric, weight in weights.items():
            rank_col = f'Rank_{metric}'
            if rank_col in df.columns:
                score_sum += df[rank_col].fillna(50) * weight
        df[style] = 100 - score_sum

    strategy_definitions = get_strategy_definitions()
    for strat_name, strat_data in strategy_definitions.items():
        score_sum = pd.Series(0, index=df.index, dtype=float)
        weights = strat_data.get('weights', {})
        for score, weight in weights.items():
            if score in df.columns:
                score_sum += df[score].fillna(50) * weight

        column_name = strat_name.replace(" ", "_")
        df[column_name] = score_sum

    # Create a set of strategy names with underscores for quick lookup
    strategy_column_names = {s.replace(" ", "_") for s in strategy_definitions.keys()}
    for col in df.columns:
        if '_Score' in col or col in strategy_column_names: df[col] = df[col].round(1)

    display_columns = ['Name','Ticker','Country','Sector',strategy,'Quality_Score','Value_Score','Growth_Score','Momentum_Score','Yield_Score','Safety_Score','MarketCapUSD','PE','PB','ROE_Avg3Y','RevGrowth3YCAGR','DivYield']
    final_df = df.sort_values(by=strategy, ascending=False)
    final_df = final_df[[col for col in display_columns if col in final_df.columns]]
    return (final_df, summary_details)
