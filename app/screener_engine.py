# =============================================================================
# Aethelon - Screener Engine
# VERSION 55.0: "Universe Expansion & Code Clarity"
#
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

# --- Data Acquisition & Auxiliary Functions ---

def get_global_top_tickers():

    blue_chip_us = [
        'AAPL', 'ABBV', 'ACN', 'ADBE', 'AMD', 'AMGN', 'AMZN', 'AVGO', 'AXP', 'BA', 'BAC', 'BLK', 'BRK-B',
        'C', 'CAT', 'COST', 'CRM', 'CSCO', 'CVX', 'DE', 'DIS', 'DOW', 'GE', 'GILD',
        'GOOGL', 'GS', 'HD', 'HON', 'IBM', 'INTC', 'ISRG', 'JNJ', 'JPM', 'KO', 'LLY', 'LIN', 'LMT',
        'MA', 'MCD', 'META', 'MRK', 'MS', 'MSFT', 'NEE', 'NFLX', 'NKE', 'NVDA', 'ORCL',
        'PEP', 'PFE', 'PG', 'PNC', 'PYPL', 'QCOM', 'RTX', 'SBUX', 'SPGI', 'SQ',
        'TGT', 'TMO', 'TSLA', 'TXN', 'UBER', 'UNH', 'UPS', 'V', 'WFC', 'WMT', 'XOM'
    ]
    blue_chip_eu = [
        'ABBN.SW', 'AIR.PA', 'ALV.DE', 'ASML.AS', 'AZN', 'BAS.DE', 'BAYN.DE',
        'BHP', 'BMW.DE', 'BN.PA', 'BNP.PA', 'BP', 'DGE.L', 'DTE.DE', 'ENEL.MI',
        'ENI.MI', 'EQNR.OL', 'ERIC-B.ST', 'GIVN.SW', 'GSK', 'HEN3.DE', 'HSBC',
        'IBE.MC', 'INGA.AS', 'INVE-B.ST', 'ITX.MC', 'KER.PA', 'LVMUY', 'MBG.DE',
        'MUV2.DE', 'NESN.SW', 'NG.L', 'NOVN.SW', 'NOVO-B.CO', 'NVO', 'OR.PA', 'PRU.L',
        'RIO', 'ROG.SW', 'RMS.PA', 'SAN.MC', 'SAN.PA', 'SAP', 'SHEL', 'SIE.DE',
        'STLA', 'SU.PA', 'TTE', 'UBS', 'UL', 'VOLV-B.ST', 'VOW3.DE', 'ZURN.SW'
    ]
    blue_chip_asia = [
        '000660.KS', '005930.KS', '0700.HK', '0883.HK', '1299.HK', '2454.TW', '601398.SS',
        '6758.T', '7203.T', '8058.T', '9432.T', 'BABA', 'BHP.AX', 'HDB', 'HDFCBANK.NS',
        'HINDUNILVR.NS', 'INFY', 'MUFG', 'PDD', 'PINGY', 'RELIANCE.NS', 'SMFG', 'SONY',
        'TCEHY', 'TCS.NS', 'TM', 'TSM'
    ]
    blue_chip_row = [
        'BMO', 'BNS', 'CBA.AX', 'ENB', 'ITUB', 'PBR', 'RY', 'SHOP', 'TD', 'TLS.AX',
        'VALE', 'WES.AX'
    ]
    growth_tech_tickers = [
        'CRWD', 'ENPH', 'FSLR', 'PANW', 'PLTR', 'ROKU', 'SEDG', 'SNOW', 'U', 'ZS'
    ]
    all_tickers = set(blue_chip_us + blue_chip_eu + blue_chip_asia + blue_chip_row + growth_tech_tickers)
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

def run_complete_screener(strategy, progress_callback):
    all_tickers = get_global_top_tickers(); total_tickers = len(all_tickers); results = []; failed_tickers = 0
    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_ticker = {executor.submit(calculate_metrics, ticker): ticker for ticker in all_tickers}
        for i, future in enumerate(as_completed(future_to_ticker)):
            progress_callback.emit(int((i + 1) * (100 / total_tickers)))
            try:
                result = future.result(timeout=15)
                if result: results.append(result)
                else: failed_tickers += 1
            except Exception as e:
                failed_tickers += 1; logging.warning(f"Ticker {future_to_ticker[future]} hat einen Fehler verursacht: {e}")
    if not results:
        summary = f"<b>Scan fehlgeschlagen.</b><br><br>0 von {total_tickers} Tickers konnten verarbeitet werden.<br>Bitte überprüfe deine Internetverbindung."
        return (pd.DataFrame(), summary)
    df = pd.DataFrame(results); initial_count = len(df)
    df['MarketCapUSD'] = df['MarketCap'] * df['Currency'].map(APPROX_RATES).fillna(1.0)
    df['NormalizedName'] = df['Name'].str.lower().str.replace(r' inc| corporation| corp| plc| se| sa| ag| ltd| limited| group| holdings| n\.v\.', '', regex=True).str.strip()
    df = df.sort_values('MarketCapUSD', ascending=False).drop_duplicates(subset=['NormalizedName'], keep='first')
    df = df[df['PE'].isnull() | (df['PE'] > 0)].copy(); final_count = len(df)
    summary = (f"<b>Scan-Zusammenfassung</b><br><br>"
        f"Ticker im Universum: {total_tickers}<br>"
        f"Datenabruf erfolgreich: {initial_count}<br>"
        f"Datenabruf fehlgeschlagen: {failed_tickers}<br><hr>"
        f"<b>Finales Ergebnis nach Qualitätsfilterung: {final_count} Aktien in der Tabelle.</b>")
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
    strategy_definitions = {"Balanced": {'Quality_Score': 0.30, 'Value_Score': 0.25, 'Growth_Score': 0.20, 'Momentum_Score': 0.10, 'Yield_Score': 0.10, 'Safety_Score': 0.05},"Deep_Value": {'Value_Score': 0.70, 'Safety_Score': 0.20, 'Yield_Score': 0.10},"High_Growth": {'Growth_Score': 0.60, 'Quality_Score': 0.30, 'Momentum_Score': 0.10},"Quality_Dividend": {'Yield_Score': 0.50, 'Quality_Score': 0.30, 'Safety_Score': 0.20}}
    for strat_name, weights in strategy_definitions.items():
        score_sum = pd.Series(0, index=df.index)
        for score, weight in weights.items():
            if score in df.columns: score_sum += df[score].fillna(50) * weight
        df[strat_name] = score_sum
    for col in df.columns:
        if '_Score' in col or col in strategy_definitions: df[col] = df[col].round(1)
    display_columns = ['Name','Ticker','Country','Sector',strategy,'Quality_Score','Value_Score','Growth_Score','Momentum_Score','Yield_Score','Safety_Score','MarketCapUSD','PE','PB','ROE_Avg3Y','RevGrowth3YCAGR','DivYield']
    final_df = df.sort_values(by=strategy, ascending=False)
    final_df = final_df[[col for col in display_columns if col in final_df.columns]]
    return (final_df, summary)
