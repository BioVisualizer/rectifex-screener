import yfinance as yf
import pandas as pd
import numpy as np
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import configparser
from pathlib import Path
import os
import time

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

def get_global_top_tickers():
    # This list is a combination of the original tickers and a sample of new tickers from major indices.
    tickers = [
        "0001.HK", "0002.HK", "0003.HK", "0005.HK", "0011.HK", "0012.HK", "0016.HK", "0017.HK", "005380.KS",
        "005490.KS", "005930.KS", "0066.HK", "00660.KS", "0267.HK", "035420.KS", "0386.HK", "0388.HK",
        "051910.KS", "068270.KS", "0700.HK", "0857.HK", "0883.HK", "0939.HK", "0941.HK", "1044.HK", "1299.HK",
        "1721.T", "1801.T", "1802.T", "1803.T", "1808.T", "1812.T", "1925.T", "1928.T", "1963.T", "1COV.DE",
        "207940.KS", "2303.TW", "2308.TW", "2317.TW", "2318.HK", "2330.TW", "2382.TW", "2412.TW", "2454.TW",
        "2628.HK", "2881.TW", "2882.TW", "3405.T", "3407.T", "3988.HK", "4004.T", "4005.T", "4021.T", "4042.T",
        "4043.T", "4061.T", "4063.T", "4183.T", "4188.T", "4208.T", "4452.T", "4631.T", "4901.T", "4911.T",
        "5831.T", "6752.T", "6758.T", "6988.T", "7186.T", "7201.T", "7202.T", "7203.T", "7205.T", "7211.T",
        "7261.T", "7267.T", "7269.T", "7270.T", "7272.T", "7974.T", "8031.T", "8058.T", "8304.T", "8306.T",
        "8308.T", "8309.T", "8316.T", "8331.T", "8354.T", "8411.T", "9202.T", "9432.T", "9433.T", "9434.T",
        "9613.T", "9983.T", "9984.T", "9988.HK", "A", "AAL", "AAL.L", "AAP", "AAPL", "ABBN.SW", "ABBV", "ABEV",
        "ABI.BR", "ABNB", "ABT", "AC.PA", "ACA.PA", "ACN", "AD.AS", "ADANIENT.NS", "ADBE", "ADI", "ADP",
        "ADS.DE", "ADYEN.AS", "AENA.MC", "AEP", "AFRM", "AGN.AS", "AI.PA", "AIG", "AIR.DE", "AIR.PA", "AKAM",
        "ALL.AX", "ALO.PA", "ALV.DE", "AMAT", "AMC.AX", "AMD", "AMGN", "AMP.AX", "AMT", "AMZN", "ANSS",
        "ANTO.L", "ANZ.AX", "AON", "APA", "APA.AX", "APD", "APH", "APT.AX", "ARW", "ASIANPAINT.NS", "ASML.AS",
        "ASRNL.AS", "ASX.AX", "ATD.TO", "ATO.PA", "AV.L", "AVB", "AVGO", "AVY", "AWK", "AXISBANK.NS", "AXP",
        "AZN", "AZN.L", "BA", "BA.L", "BABA", "BAC", "BAFN.SW", "BAJFINANCE.NS", "BAS.DE", "BATS.L", "BAX",
        "BAYN.DE", "BBDC4.SA", "BBY", "BCE", "BDX", "BEI.DE", "BEN", "BHARTIARTL.NS", "BHP.AX", "BILL", "BK",
        "BKNG", "BLK", "BMO", "BMW.DE", "BMY", "BNP.PA", "BNS", "BNS.TO", "BP", "BP.L", "BRK-A", "BRK-B",
        "BT-A.L", "BXB.AX", "C", "CA.PA", "CABK.MC", "CAP.PA", "CARR", "CAT", "CBA.AX", "CCH.L", "CDNS", "CE",
        "CFR.SW", "CHTR", "CI", "CL", "CLNX.MC", "CM.TO", "CME", "CMG", "CMI", "CMCSA", "CNP", "CNQ", "CNR.TO",
        "COF", "COIN", "COL.AX", "CON.DE", "COO", "COP", "COST", "CP.TO", "CPG.L", "CPRT", "CPT", "CRM", "CRWD",
        "CS.PA", "CSCO", "CSGN.SW", "CSL.AX", "CSU.TO", "CSX", "CTAS", "CTSH", "CVS", "CVX", "D", "DAI.DE",
        "DAL", "DASH", "DB1.DE", "DBK.DE", "DD", "DDOG", "DE", "DFS", "DG", "DGX", "DHER.DE", "DHI", "DHR",
        "DHL.DE", "DIS", "DLR", "DLTR", "DOV", "DOW", "DPW.DE", "DSM.AS", "DTE.DE", "DTG.DE", "DUK", "DVN",
        "DXCM", "EA", "EBAY", "EIX", "EL", "EMN", "EN.PA", "ENB", "ENB.TO", "ENEL.MI", "ENG.MC", "ENGI.PA",
        "ENI.MI", "ENPH", "ENR.DE", "EOAN.DE", "EOG", "EQNR.OL", "EQR", "ERF.PA", "ES", "ESS", "ETN", "ETSY",
        "EW", "EXC", "EXPD", "EXPE", "F", "FAST", "FDX", "FE", "FER.MC", "FFIV", "FIS", "FISV", "FITB", "FLG.MC",
        "FLTR.L", "FME.DE", "FMG.AX", "FRE.DE", "FRES.L", "FSLR", "GD", "GE", "GGB", "GGBR4.SA", "GIB-A.TO",
        "GILD", "GIS", "GIVN.SW", "GLE.PA", "GLW", "GM", "GMG.AX", "GOOGL", "GPN", "GRF.MC", "GRMN", "GS",
        "GSK", "GSK.L", "GWW", "HAL", "HAS", "HBAN", "HCA", "HCLTECH.NS", "HD", "HDFCBANK.NS", "HEI.DE",
        "HEIA.AS", "HEN3.DE", "HES", "HIK.L", "HINDUNILVR.NS", "HLT", "HNR1.DE", "HOLN.SW", "HON", "HRL",
        "HSBC", "HSBC.L", "HST", "HUM", "IAG.AX", "IAG.L", "IBE.MC", "IBM", "ICE", "ICICIBANK.NS", "IDR.MC",
        "IDXX", "IEX", "IFX.DE", "IHG.L", "III.L", "ILMN", "IMCD.AS", "IMO.TO", "IMP.L", "INF.L", "INFY.NS",
        "INGA.AS", "INTC", "INTU", "IP", "IPG", "IQV", "IR", "IRM", "ISRG", "ISP.MI", "ITRK.L", "ITUB",
        "ITUB4.SA", "ITW", "ITX.MC", "IVZ", "JCI", "JD.L", "JNJ", "JPM", "K", "KER.PA", "KEY", "KHC", "KIM",
        "KMB", "KMI", "KO", "KOTAKBANK.NS", "KPN.AS", "KR", "L", "L.TO", "LAND.L", "LEG", "LGEN.L", "LH",
        "LHX", "LIN", "LIN.DE", "LLC.AX", "LLOY.L", "LLY", "LMT", "LNT", "LOGN.SW", "LOW", "LR.PA", "LT.NS",
        "LUV", "LVMH.PA", "LYB", "LYV", "M&M.NS", "MA", "MAP.MC", "MAR", "MARUTI.NS", "MAS", "MB.MI", "MBG.DE",
        "MC.PA", "MCD", "MCHP", "MCK", "MCO", "MDB", "MDLZ", "MDT", "MEL.MC", "META", "MFC", "MG.TO", "ML.PA",
        "MMC", "MMM", "MNG.L", "MNST", "MO", "MOS", "MPC", "MQG.AX", "MRK", "MRK.DE", "MRL.MC", "MRO",
        "MRO.L", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTD", "MTX.DE", "MU", "MUV2.DE", "NAB.AX", "NCLH",
        "NCM.AX", "NDAQ", "NEE", "NEM", "NESN.SW", "NET", "NFLX", "NG.L", "NI", "NKE", "NN.AS", "NOC",
        "NOVN.SW", "NOVO-B.CO", "NOW", "NRG", "NSC", "NST.AX", "NTAP", "NTGY.MC", "NTR.TO", "NTRS", "NVR",
        "NWG.L", "NWL", "NWSA", "O", "OCADO.L", "OKE", "OKTA", "OR.PA", "ORA.PA", "ORCL", "OXY", "P911.DE",
        "PAH3.DE", "PANW", "PART.SW", "PATH", "PAYC", "PAYX", "PBR", "PCAR", "PDD", "PEG", "PEP", "PETR4.SA",
        "PFE", "PFG", "PG", "PGR", "PH", "PHIA.AS", "PHM", "PHNX.L", "PINS", "PKG", "PLD", "PLTR", "PM",
        "PNC", "PNR", "PNW", "POOL", "PPG", "PPL", "PRU", "PRU.L", "PRX.AS", "PSA", "PSN.L", "PSON.L", "PSX",
        "PUB.PA", "PUM.DE", "PVH", "PWR", "PXD", "PYPL", "QAN.AX", "QBE.AX", "QCOM", "QIA.DE", "QRVO",
        "RACE.MI", "RAND.AS", "RBLX", "RCL", "REG", "REGN", "RELIANCE.NS", "REN.AS", "REP.MC", "RF", "RHM.DE",
        "RHI", "RI.PA", "RIO.AX", "RIO.L", "RL", "RMD", "RNO.PA", "ROG.SW", "ROK", "ROKU", "ROL", "ROP",
        "ROST", "RR.L", "RSG", "RTO.L", "RTX", "RWE.DE", "RY", "RY.TO", "SAF.PA", "SAN.MC", "SAN.PA", "SAP",
        "SAP.DE", "SBAC", "SBIN.NS", "SBRY.L", "SBUX", "SCCO", "SCG.AX", "SCHW", "SCMN.SW", "SEDG", "SEE",
        "SGE.L", "SGO.PA", "SGP.AX", "SGSN.SW", "SHEL", "SHEL.L", "SHELL.AS", "SHL.DE", "SHOP.TO", "SHW",
        "SIE.DE", "SJM", "SLB", "SLF.TO", "SLHN.SW", "SMIN.L", "SMT.L", "SNA", "SN.L", "SNOW", "SO", "SOFI",
        "SPOT", "SPG", "SPGI", "SQ", "SRE", "SREN.SW", "SRT3.DE", "SSE.L", "STAN.L", "STE", "STLA", "STM.MI",
        "STO.AX", "STT", "STX", "STZ", "SU", "SU.PA", "SU.TO", "SUN.AX", "SUNPHARMA.NS", "SWK", "SWKS",
        "SY1.DE", "SYK", "T", "T.TO", "TAP", "TATASTEEL.NS", "TCL.AX", "TCS.NS", "TD", "TD.TO", "TDG", "TE.PA",
        "TEF.MC", "TEL", "TEN.MI", "TFC", "TFX", "TGT", "TITAN.NS", "TJX", "TLS.AX", "TMO", "TMUS", "TRMB",
        "TRP", "TRP.TO", "TRV", "TSCO", "TSCO.L", "TSLA", "TSN", "TT", "TTD", "TTE", "TTE.PA", "TWLO", "TXT",
        "U", "UAL", "UBSG.SW", "UCG.MI", "UDR", "UGI", "UHR.SW", "UL", "ULVR.L", "UMG.AS", "UMG.PA", "UMPQ",
        "UNA.AS", "UNH", "UNP", "UPS", "UPST", "URI", "USB", "V", "VALE", "VALE3.SA", "VFC", "VICI", "VIE.PA",
        "VIV.PA", "VLO", "VMC", "VNA.DE", "VNO", "VOD.L", "VOLV-B.ST", "VOW3.DE", "VRSK", "VRSN", "VRTX",
        "VTR", "VZ", "WBA", "WBC.AX", "WBD", "WCN.TO", "WDC", "WDAY", "WDS.AX", "WEC", "WEGE3.SA", "WELL",
        "WES.AX", "WFC", "WHR", "WIPRO.NS", "WKL.AS", "WM", "WMB", "WMT", "WOW.AX", "WPM", "WRB", "WRK",
        "WST", "WTB.L", "WY", "WYNN", "XEL", "XOM", "XRX", "XYL", "YUM", "ZAL.DE", "ZBH", "ZBRA", "ZION",
        "ZM", "ZS", "ZTS", "ZURN.SW"
    ]
    return sorted(list(set(tickers)))

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

def run_complete_screener(strategy, tickers, api_key, progress_callback):
    all_tickers = tickers; total_tickers = len(all_tickers); results = []; failed_list = []

    use_fmp = api_key is not None and len(api_key) > 10
    fetch_function = calculate_metrics_fmp if use_fmp else calculate_metrics_yfinance

    with ThreadPoolExecutor(max_workers=8) as executor:
        if use_fmp:
            future_to_ticker = {executor.submit(fetch_function, ticker, api_key): ticker for ticker in all_tickers}
        else:
            future_to_ticker = {executor.submit(fetch_function, ticker): ticker for ticker in all_tickers}

        for i, future in enumerate(as_completed(future_to_ticker)):
            ticker = future_to_ticker[future]
            progress_callback.emit(int((i + 1) * (100 / total_tickers)))
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

    for strat_name, weights in STRATEGY_DEFINITIONS.items():
        score_sum = pd.Series(0, index=df.index, dtype=float)
        for score, weight in weights.items():
            if score in df.columns:
                score_sum += df[score].fillna(50) * weight
        df[strat_name] = score_sum

    for col in df.columns:
        if '_Score' in col or col in STRATEGY_DEFINITIONS: df[col] = df[col].round(1)

    display_columns = ['Name','Ticker','Country','Sector',strategy,'Quality_Score','Value_Score','Growth_Score','Momentum_Score','Yield_Score','Safety_Score','MarketCapUSD','PE','PB','ROE_Avg3Y','RevGrowth3YCAGR','DivYield']
    final_df = df.sort_values(by=strategy, ascending=False)
    final_df = final_df[[col for col in display_columns if col in final_df.columns]]
    return (final_df, summary_details)
