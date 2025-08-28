# =============================================================================
# Rectifex - Screener Engine
# VERSION 57.0: "Gold Standard Ticker List"
# =============================================================================

import yfinance as yf
import pandas as pd
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Global Configuration ---
APPROX_RATES = {
    'EUR': 1.08, 'JPY': 0.0064, 'GBP': 1.27, 'CAD': 0.73, 'CHF': 1.12,
    'AUD': 0.66, 'HKD': 0.13, 'BRL': 0.18, 'DKK': 0.14, 'SEK': 0.096,
    'NOK': 0.094, 'INR': 0.012, 'KRW': 0.00072, 'CNY': 0.14, 'GBp': 0.0127
}

STRATEGY_DEFINITIONS = {
    "Balanced": {'Quality_Score': 0.30, 'Value_Score': 0.25, 'Growth_Score': 0.20, 'Momentum_Score': 0.10, 'Yield_Score': 0.10, 'Safety_Score': 0.05},
    "Deep_Value": {'Value_Score': 0.70, 'Safety_Score': 0.20, 'Yield_Score': 0.10},
    "High_Growth": {'Growth_Score': 0.60, 'Quality_Score': 0.30, 'Momentum_Score': 0.10},
    "Quality_Dividend": {'Yield_Score': 0.50, 'Quality_Score': 0.30, 'Safety_Score': 0.20}
}

def get_strategy_definitions():
    return STRATEGY_DEFINITIONS

# --- Data Acquisition & Auxiliary Functions ---
def get_global_top_tickers():
    # Existing tickers from the original list
    original_tickers = [
        'AAPL', 'ABT', 'ABBV', 'ACN', 'ADBE', 'ADI', 'ADP', 'AMAT', 'AMD', 'AMGN', 'AMT', 'AMZN', 'AVGO', 'AXP',
        'BA', 'BAC', 'BLK', 'BMY', 'BRK-B', 'C', 'CAT', 'CMCSA', 'COP', 'COST', 'CRM', 'CSCO', 'CVS',
        'CVX', 'DE', 'DIS', 'DOW', 'DUK', 'GE', 'GILD', 'GOOGL', 'GS', 'HD', 'HON', 'IBM', 'INTC', 'INTU', 'ISRG',
        'JNJ', 'JPM', 'KO', 'LIN', 'LLY', 'LMT', 'LOW', 'MA', 'MCD', 'MDT', 'META', 'MMM', 'MO', 'MRK',
        'MS', 'MSFT', 'NEE', 'NFLX', 'NKE', 'NOW', 'NVDA', 'ORCL', 'PEP', 'PFE', 'PG', 'PM', 'PYPL', 'QCOM',
        'RTX', 'SBUX', 'SO', 'T', 'TMO', 'TSLA', 'TXN', 'UNH', 'UNP', 'UPS', 'V', 'VZ', 'WFC', 'WMT', 'XOM',
        'ABI.BR', 'ABBN.SW', 'ADS.DE', 'ADYEN.AS', 'AI.PA', 'AIR.PA', 'ALV.DE', 'ASML.AS', 'AZN',
        'BAS.DE', 'BAYN.DE', 'BMW.DE', 'BNP.PA', 'BP', 'DGE.L', 'DTE.DE', 'ENEL.MI',
        'ENI.MI', 'EQNR.OL', 'GSK', 'HSBC', 'IBE.MC', 'INGA.AS', 'ISP.MI', 'ITX.MC',
        'LVMH.PA', 'MBG.DE', 'MC.PA', 'MUV2.DE', 'NESN.SW', 'NOVN.SW', 'NOVO-B.CO', 'OR.PA',
        'RIO', 'ROG.SW', 'RWE.DE', 'SAF.PA', 'SAN.MC', 'SAP.DE', 'SHEL', 'SIE.DE',
        'STLA', 'TTE', 'UBSG.SW', 'UL', 'UNA.AS', 'VOD.L', 'VOLV-B.ST', 'VOW3.DE', 'ZURN.SW',
        '0005.HK', '005930.KS', '0700.HK', '0939.HK', '1299.HK', '2330.TW', '2454.TW', '3988.HK',
        '6758.T', '7203.T', '7974.T', '8058.T', '8306.T', '9432.T', '9433.T', '9984.T',
        '9988.HK', 'AXISBANK.NS', 'BABA', 'BHARTIARTL.NS', 'HCLTECH.NS', 'HDFCBANK.NS', 'ICICIBANK.NS',
        'INFY.NS', 'ITC.NS', 'KOTAKBANK.NS', 'LT.NS', 'PDD', 'RELIANCE.NS', 'SBIN.NS', 'TCS.NS',
        'ABEV', 'ANZ.AX', 'BCE', 'BHP.AX', 'BMO', 'BNS', 'CBA.AX', 'CNQ', 'ENB', 'GGB', 'ITUB',
        'MFC', 'MQG.AX', 'PBR', 'RY', 'SCCO', 'SHOP', 'SU', 'TD', 'TLS.AX', 'TRP', 'VALE',
        'WBC.AX', 'WDS.AX', 'WES.AX', 'WPM',
        'ABNB', 'AFRM', 'BILL', 'COIN', 'CRWD', 'DASH', 'DDOG', 'ENPH', 'ETSY', 'FSLR',
        'MDB', 'NET', 'OKTA', 'PANW', 'PATH', 'PINS', 'PLTR', 'RBLX', 'ROKU',
        'SEDG', 'SNOW', 'SOFI', 'SPOT', 'SQ', 'TTD', 'TWLO', 'U', 'UPST', 'WDAY', 'ZM', 'ZS'
    ]

    # DAX 40 Additional Tickers
    dax_tickers = [
        '1COV.DE', 'DTG.DE', 'DBK.DE', 'DB1.DE', 'DHL.DE', 'EOAN.DE', 'FRE.DE', 'FME.DE',
        'HNR1.DE', 'HEI.DE', 'HEN3.DE', 'IFX.DE', 'P911.DE', 'PAH3.DE', 'QIA.DE',
        'RHM.DE', 'SRT3.DE', 'ENR.DE', 'SHL.DE', 'SY1.DE', 'ZAL.DE'
    ]

    # Nikkei 225 Additional Tickers (sample)
    nikkei_tickers = [
        '9202.T', '7205.T', '7267.T', '7202.T', '7261.T', '7211.T', '7201.T', '7270.T',
        '7269.T', '7272.T', '8304.T', '8331.T', '7186.T', '8354.T', '8411.T', '8308.T',
        '5831.T', '8316.T', '8309.T', '3407.T', '4061.T', '4631.T', '4901.T', '4452.T',
        '3405.T', '4188.T', '4183.T', '4021.T', '6988.T', '4004.T', '4063.T', '4911.T',
        '4005.T', '4043.T', '4042.T', '4208.T', '9613.T', '9434.T', '1721.T', '1925.T',
        '1808.T', '1963.T', '1812.T', '1802.T', '1928.T', '1803.T', '1801.T'
    ]

    # S&P 500 and NASDAQ tickers are largely overlapping with the original US list,
    # but adding a few more for broader coverage.
    us_tickers = [
        'AOS', 'AES', 'AKAM', 'ARE', 'ALGN', 'ALLE', 'LNT', 'AEE', 'AWK', 'AMP', 'AME', 'APA', 'APO',
        'ACGL', 'ANET', 'AIZ', 'ATO', 'AVB', 'AVY', 'AXON', 'BKR', 'BALL', 'BAX', 'BDX', 'TECH',
        'BIIB', 'BX', 'BK', 'BSX', 'BR', 'BRO', 'BF.B', 'CHRW', 'CDNS', 'CZR', 'CPT', 'CPB', 'CAH',
        'KMX', 'CCL', 'CARR', 'CBOE', 'CBRE', 'CDW', 'COR', 'CNC', 'CNP', 'CF', 'CRL', 'SCHW',
        'CHTR', 'CMG', 'CB', 'CHD', 'CI', 'CINF', 'CTAS', 'CFG', 'CLX', 'CME', 'CMS', 'CTSH',
        'CAG', 'ED', 'STZ', 'CEG', 'COO', 'CPRT', 'GLW', 'CPAY', 'CTVA', 'CSGP', 'CTRA', 'CCI',
        'CSX', 'CMI', 'DHR', 'DRI', 'DVA', 'DAY', 'DECK', 'DELL', 'DAL', 'DVN', 'DXCM', 'FANG',
        'DLR', 'DG', 'D', 'DPZ', 'DOV', 'DHI', 'DD', 'EMN', 'ETN', 'EBAY', 'ECL', 'EIX', 'EW',
        'EA', 'ELV', 'EMR', 'ETR', 'EOG', 'EPAM', 'EQT', 'EFX', 'EQIX', 'EQR', 'ERIE', 'ESS',
        'EL', 'EG', 'EVRG', 'ES', 'EXC', 'EXE', 'EXPE', 'EXPD', 'EXR', 'FFIV', 'FDS', 'FICO',
        'FAST', 'FRT', 'FDX', 'FIS', 'FITB', 'FE', 'FI', 'F', 'FTNT', 'FTV', 'FOXA', 'FOX',
        'BEN', 'FCX', 'GRMN', 'IT', 'GEHC', 'GEV', 'GEN', 'GNRC', 'GD', 'GIS', 'GM', 'GPC',
        'GPN', 'GL', 'GDDY', 'HAL', 'HIG', 'HAS', 'HCA', 'DOC', 'HSIC', 'HSY', 'HPE', 'HLT',
        'HOLX', 'HRL', 'HST', 'HWM', 'HPQ', 'HUBB', 'HUM', 'HBAN', 'HII', 'IEX', 'IDXX', 'ITW',
        'INCY', 'IR', 'PODD', 'IBKR', 'ICE', 'IFF', 'IP', 'IPG', 'IVZ', 'INVH', 'IQV', 'IRM',
        'JBHT', 'JBL', 'JKHY', 'J', 'JCI', 'K', 'KVUE', 'KDP', 'KEY', 'KEYS', 'KMB', 'KIM',
        'KMI', 'KKR', 'KLAC', 'KHC', 'KR', 'LHX', 'LH', 'LRCX', 'LW', 'LVS', 'LDOS', 'LEN',
        'LII', 'LYV', 'LKQ', 'LULU', 'LYB', 'MTB', 'MPC', 'MKTX', 'MAR', 'MMC', 'MLM', 'MAS',
        'MTCH', 'MKC', 'MCK', 'MTD', 'MGM', 'MCHP', 'MU', 'MAA', 'MRNA', 'MHK', 'MOH', 'TAP',
        'MDLZ', 'MPWR', 'MNST', 'MCO', 'MOS', 'MSI', 'MSCI', 'NDAQ', 'NTAP', 'NEM', 'NWSA',
        'NWS', 'NI', 'NDSN', 'NSC', 'NTRS', 'NOC', 'NCLH', 'NRG', 'NUE', 'NVR', 'NXPI',
        'ORLY', 'OXY', 'ODFL', 'OMC', 'ON', 'OKE', 'OTIS', 'PCAR', 'PKG', 'PANW', 'PAYX',
        'PAYC', 'PNR', 'PCG', 'PNW', 'PNC', 'POOL', 'PPG', 'PPL', 'PFG', 'PGR', 'PLD',
        'PRU', 'PEG', 'PTC', 'PSA', 'PHM', 'QRVO', 'PWR', 'DGX', 'RL', 'RJF', 'O', 'REG',
        'REGN', 'RF', 'RSG', 'RMD', 'RVTY', 'ROK', 'ROL', 'ROP', 'RCL', 'SPGI', 'SBAC',
        'SLB', 'STX', 'SRE', 'SHW', 'SPG', 'SWKS', 'SJM', 'SNA', 'SOLV', 'LUV', 'SWK',
        'STT', 'STLD', 'STE', 'SYK', 'SMCI', 'SYF', 'SNPS', 'SYY', 'TMUS', 'TROW', 'TTWO',
        'TPR', 'TRGP', 'TGT', 'TEL', 'TDY', 'TER', 'TPL', 'TXT', 'TJX', 'TKO', 'TT', 'TDG',
        'TRV', 'TRMB', 'TFC', 'TYL', 'TSN', 'USB', 'UBER', 'UDR', 'ULTA', 'UAL', 'URI',
        'UHS', 'VLO', 'VTR', 'VLTO', 'VRSN', 'VRSK', 'VZ', 'VRTX', 'VTRS', 'VICI', 'VST',
        'VMC', 'WRB', 'GWW', 'WAB', 'WBA', 'WBD', 'WM', 'WAT', 'WEC', 'WELL', 'WST',
        'WDC', 'WY', 'WSM', 'WMB', 'WTW', 'WYNN', 'XEL', 'XYL', 'YUM', 'ZBRA', 'ZBH', 'ZTS'
    ]

    # Combine all lists and remove duplicates
    all_tickers = set(original_tickers + dax_tickers + nikkei_tickers + us_tickers)

    return sorted(list(all_tickers))

def safe_float(value, default=np.nan):
    try: return float(value) if pd.notna(value) else default
    except (ValueError, TypeError): return default

def calculate_metrics(ticker_symbol):
    try:
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

def run_complete_screener(strategy, tickers, progress_callback):
    all_tickers = tickers; total_tickers = len(all_tickers); results = []; failed_list = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_ticker = {executor.submit(calculate_metrics, ticker): ticker for ticker in all_tickers}
        for i, future in enumerate(as_completed(future_to_ticker)):
            ticker = future_to_ticker[future]
            progress_callback.emit(int((i + 1) * (100 / total_tickers)))
            try:
                result = future.result(timeout=20)
                if result:
                    results.append(result)
                else:
                    failed_list.append(f"{ticker}: No data returned from API.")
            except Exception as e:
                failed_list.append(f"{ticker}: Data request failed ({type(e).__name__}).")
                logging.warning(f"Ticker {ticker} caused an exception: {e}")
    if not results:
        summary = {
            "total_tickers": total_tickers,
            "initial_count": 0,
            "failed_count": total_tickers,
            "final_count": 0,
            "failed_list": [f"{t}: Scan failed" for t in all_tickers]
        }
        return (pd.DataFrame(), summary)
    df = pd.DataFrame(results); initial_count = len(df)
    df['MarketCapUSD'] = df['MarketCap'] * df['Currency'].map(APPROX_RATES).fillna(1.0)
    df['NormalizedName'] = df['Name'].str.lower().str.replace(r' inc| corporation| corp| plc| se| sa| ag| ltd| limited| group| holdings| n\.v\.', '', regex=True).str.strip()
    df = df.sort_values('MarketCapUSD', ascending=False).drop_duplicates(subset=['NormalizedName'], keep='first')
    df = df[df['PE'].isnull() | (df['PE'] > 0)].copy(); final_count = len(df)
    summary_details = {
        "total_tickers": total_tickers,
        "initial_count": initial_count,
        "failed_count": len(failed_list),
        "final_count": final_count,
        "failed_list": failed_list
    }
    metrics_to_rank = {'ROE_Avg3Y': False, 'PE': True, 'PB': True, 'RevGrowth3YCAGR': False, 'Momentum6M': False, 'DivYield': False, 'Volatility': True, 'DebtEquity': True}
    for col, asc in metrics_to_rank.items():
        if col in df.columns:
            df[col] = df[col].clip(lower=df[col].quantile(0.02), upper=df[col].quantile(0.98))
            df[f'Rank_{col}'] = df[col].rank(ascending=asc, pct=True) * 100
    base_scores = {'Quality_Score': {'ROE_Avg3Y': 1.0},'Value_Score': {'PE': 0.5, 'PB': 0.5},'Growth_Score': {'RevGrowth3YCAGR': 1.0},'Momentum_Score': {'Momentum6M': 1.0},'Yield_Score': {'DivYield': 1.0},'Safety_Score': {'Volatility': 0.5, 'DebtEquity': 0.5}}
    for style, weights in base_scores.items():
        score_sum = pd.Series(0, index=df.index)
        for metric, weight in weights.items():
            rank_col = f'Rank_{metric}'
            if rank_col in df.columns: score_sum += df[rank_col].fillna(50) * weight
        df[style] = 100 - score_sum
    for strat_name, weights in STRATEGY_DEFINITIONS.items():
        score_sum = pd.Series(0, index=df.index)
        for score, weight in weights.items():
            if score in df.columns: score_sum += df[score].fillna(50) * weight
        df[strat_name] = score_sum
    for col in df.columns:
        if '_Score' in col or col in STRATEGY_DEFINITIONS: df[col] = df[col].round(1)
    display_columns = ['Name','Ticker','Country','Sector',strategy,'Quality_Score','Value_Score','Growth_Score','Momentum_Score','Yield_Score','Safety_Score','MarketCapUSD','PE','PB','ROE_Avg3Y','RevGrowth3YCAGR','DivYield']
    final_df = df.sort_values(by=strategy, ascending=False)
    final_df = final_df[[col for col in display_columns if col in final_df.columns]]
    return (final_df, summary_details)
