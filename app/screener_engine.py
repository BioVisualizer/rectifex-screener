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
import json

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

def get_global_top_tickers():
    # This list is a combination of the original tickers and a sample of new tickers from major indices.
    tickers = [
        "0001.HK", "0002.HK", "0003.HK", "0005.HK", "0011.HK", "0012.HK", "0016.HK", "0017.HK", "005380.KS",
        "005490.KS", "005930.KS", "0066.HK", "00660.KS", "0267.HK", "035420.KS", "0386.HK", "0388.HK",
        "051910.KS", "068270.KS", "0700.HK", "0857.HK", "0883.HK", "0939.HK", "0941.HK", "1044.HK", "1299.HK",
        "1332.T", "1605.T", "1721.T", "1801.T", "1802.T", "1803.T", "1808.T", "1812.T", "1925.T", "1928.T", "1963.T", "1COV.DE", "1U1.DE", "2002.T",
        "207940.KS", "2269.T", "2282.T", "2303.TW", "2308.TW", "2317.TW", "2318.HK", "2330.TW", "2382.TW", "2412.TW", "2413.T", "2432.T", "2454.TW", "2501.T", "2502.T", "2503.T",
        "2531.T", "2628.HK", "2768.T", "2801.T", "2802.T", "2871.T", "2881.TW", "2882.TW", "2914.T", "3086.T",
        "3099.T", "3289.T", "3382.T", "3401.T", "3402.T", "3405.T", "3407.T", "3436.T", "3659.T", "3861.T",
        "3863.T", "3988.HK", "4004.T", "4005.T", "4021.T", "4042.T", "4043.T", "4061.T", "4063.T", "4151.T",
        "4183.T", "4188.T", "4208.T", "4324.T", "4385.T", "4452.T", "4502.T", "4503.T", "4506.T", "4507.T",
        "4519.T", "4523.T", "4543.T", "4568.T", "4578.T", "4631.T", "4661.T", "4689.T", "4704.T", "4751.T",
        "4755.T", "4901.T", "4902.T", "4911.T", "5019.T", "5020.T", "5101.T", "5108.T", "5201.T", "5202.T",
        "5214.T", "5232.T", "5233.T", "5301.T", "5332.T", "5333.T", "5401.T", "5406.T", "5411.T", "5541.T",
        "5631.T", "5706.T", "5711.T", "5713.T", "5714.T", "5801.T", "5802.T", "5803.T", "5831.T", "6098.T",
        "6103.T", "6113.T", "6178.T", "6273.T", "6301.T", "6302.T", "6305.T", "6326.T", "6361.T", "6367.T",
        "6471.T", "6472.T", "6473.T", "6479.T", "6501.T", "6503.T", "6504.T", "6506.T", "6594.T", "6645.T",
        "6674.T", "6701.T", "6702.T", "6703.T", "6723.T", "6724.T", "6752.T", "6753.T", "6758.T", "6762.T",
        "6770.T", "6841.T", "6857.T", "6861.T", "6902.T", "6920.T", "6952.T", "6954.T", "6971.T", "6976.T",
        "6981.T", "6988.T", "7004.T", "7011.T", "7012.T", "7013.T", "7186.T", "7201.T", "7202.T", "7203.T",
        "7205.T", "7211.T", "7261.T", "7267.T", "7269.T", "7270.T", "7272.T", "7731.T", "7733.T", "7735.T",
        "7741.T", "7751.T", "7752.T", "7762.T", "7832.T", "7911.T", "7912.T", "7951.T", "7974.T", "8001.T",
        "8002.T", "8015.T", "8031.T", "8035.T", "8053.T", "8058.T", "8233.T", "8252.T", "8253.T", "8267.T",
        "8304.T", "8306.T", "8308.T", "8309.T", "8316.T", "8331.T", "8354.T", "8411.T", "8591.T", "8601.T",
        "8604.T", "8630.T", "8697.T", "8725.T", "8750.T", "8766.T", "8795.T", "8801.T", "8802.T", "8804.T",
        "8830.T", "9001.T", "9005.T", "9007.T", "9008.T", "9009.T", "9020.T", "9021.T", "9022.T", "9064.T",
        "9101.T", "9104.T", "9107.T", "9147.T", "9201.T", "9202.T", "9301.T", "9432.T", "9433.T", "9434.T",
        "9501.T", "9502.T", "9503.T", "9531.T", "9532.T", "9602.T", "9613.T", "9735.T", "9766.T", "9843.T",
        "9983.T", "9984.T", "9988.HK", "A", "A2A.MI", "AAK.ST", "AAL", "AAL.L", "AALB.AS", "AAP", "AAPL",
        "ABBN.SW", "ABBV", "ABDN.L", "ABEV", "ABI.BR", "ABN.AS", "ABNB", "ABT", "AC.PA", "ACA.PA", "ACKB.BR", "ACN",
        "ACS.MC", "AD.AS", "ADANIENT.NS", "ADBE", "ADEN.SW", "ADI", "ADM.L", "ADP", "ADP.PA", "ADS.DE",
        "ADYEN.AS", "AENA.MC", "AEP", "AF.PA", "AFRM", "AGN.AS", "AGS.BR", "AI.PA", "AIBG.IR", "AIG",
        "AIR.DE", "AIR.PA", "AKAM", "AKE.PA", "AKRBP.OL", "AKZA.AS", "ALC.SW", "ALFA.ST", "ALL.AX", "ALO.PA",
        "ALV.DE", "AMAT", "AMC.AX", "AMD", "AMGN", "AMP.AX", "AMSS.MC", "AMT", "AMZN", "AN.PA", "ANDR.VI",
        "ANIM.PA", "ANSS", "ANTO.L", "ANZ.AX", "AON", "APA", "APA.AX", "APD", "APH", "APT.AX", "ARL.DE", "ARW",
        "ASIANPAINT.NS", "ASML", "ASML.AS", "ASRNL.AS", "ASX.AX", "ATCO-A.ST", "ATD.TO", "ATE.PA", "ATO.PA",
        "ATOS.PA", "AU.PA", "AV.L", "AVB", "AVGO", "AVV.L", "AVY", "AWK", "AXISBANK.NS", "AXP", "AY.PA",
        "AZN", "AZN.L", "BA", "BA.L", "BABA", "BAC", "BAFN.SW", "BAJFINANCE.NS", "BARC.L", "BAS.DE",
        "BATS.L", "BAX", "BAYN.DE", "BBDC4.SA", "BBOX.PA", "BBVA.MC", "BBY", "BCE", "BDEV.L", "BDX",
        "BEI.DE", "BEN", "BEN.PA", "BESI.AS", "BHARTIARTL.NS", "BHP.AX", "BHP.L", "BIG.PA", "BILL", "BIM.PA",
        "BION.SW", "BIRG.IR", "BK", "BKNG", "BKT.L", "BLK", "BMO", "BMW.DE", "BMY", "BN.PA", "BNP.PA", "BNS",
        "BNS.TO", "BNZL.L", "BOL.ST", "BOSS.DE", "BP", "BP.L", "BPOST.BR", "BRBY.L", "BRE.MI", "BRK-A",
        "BRK-B", "BT-A.L", "BVI.L", "BXB.AX", "C", "CA.PA", "CABK.MC", "CAP.PA", "CARL-B.CO", "CARR", "CAT",
        "CATE.MI", "CBA.AX", "CCH.L", "CDNS", "CE", "CFR.SW", "CGG.PA", "CHR.CO", "CHTR", "CI", "CINE.L",
        "CL", "CLNX.MC", "CLNX.PA", "CM.TO", "CMCSA", "CME", "CMG", "CMI", "CNE.L", "CNP", "CNQ", "CNR.TO",
        "CO.PA", "COB.DE", "COF", "COIN", "COL.AX", "COLN.SW", "COLOP-B.CO", "CON.DE", "COO", "COP", "COST",
        "CP.TO", "CPG.L", "CPI.L", "CPR.MI", "CPRT", "CPT", "CRH.L", "CRM", "CRWD", "CS.PA", "CSCO", "CSGN.SW",
        "CSL.AX", "CSU.TO", "CSX", "CTAS", "CTSH", "CVS", "CVX", "D", "DAB.DE", "DAI.DE", "DAL", "DAL.L",
        "DAN.PA", "DASH", "DB1.DE", "DBK.DE", "DCC.L", "DD", "DDOG", "DE", "DE.PA", "DEC.PA", "DEL.L", "DEMANT.CO",
        "DFS", "DG", "DG.PA", "DGE.L", "DGX", "DHER.DE", "DHI", "DHL.DE", "DHR", "DIA.MI", "DIS", "DLR",
        "DLTR", "DNB.OL", "DNO.OL", "DOC.L", "DOV", "DOW", "DPW.DE", "DSM.AS", "DSV.CO", "DTE.DE", "DTG.DE",
        "DUK", "DVN", "DXCM", "EA", "EBAY", "EBS.VI", "EC.PA", "EDEN.PA", "EDF.PA", "EDP.LS", "EDPR.LS", "EIX",
        "EKT.L", "EL", "EL.PA", "ELE.MC", "ELISA.HE", "ELN.PA", "EMN", "EN.PA", "ENB", "ENB.TO", "ENEL.MI",
        "ENG.MC", "ENGI.PA", "ENI.MI", "ENPH", "ENR.DE", "ENR.PA", "EOAN.DE", "EOG", "EQNR.OL", "EQR", "ERF.PA",
        "ERIC-B.ST", "ES", "ES.PA", "ESS", "ESSILORLUX.PA", "ETL.L", "ETN", "ETSY", "EVK.DE", "EVO.ST", "EVT.DE",
        "EW", "EXC", "EXO.PA", "EXPD", "EXPE", "EXPN.L", "F", "FAST", "FDX", "FE", "FER.MC", "FFIV", "FGR.PA",
        "FIS", "FISV", "FITB", "FLG.MC", "FLTR.L", "FME.DE", "FMG.AX", "FNAC.PA", "FP.PA", "FRE.DE", "FRES.L",
        "FSLR", "G.L", "GALP.LS", "GBL.BR", "GBLB.BR", "GD", "GE", "GE.PA", "GEC.L", "GETI-B.ST", "GFK.L",
        "GGB", "GGBR4.SA", "GIB-A.TO", "GILD", "GIS", "GIVN.SW", "GKN.L", "GLE.PA", "GLEN.L", "GLW", "GM",
        "GMG.AX", "GN.CO", "GOOG", "GOOGL", "GPN", "GRF.MC", "GRMN", "GS", "GSK", "GSK.L", "GTO.L", "GVC.L",
        "GWW", "HAL", "HAM.L", "HAS", "HAS.L", "HBAN", "HBG.DE", "HBH.L", "HCA", "HCLTECH.NS", "HD",
        "HDFCBANK.NS", "HEI.DE", "HEIA.AS", "HEIO.AS", "HEN3.DE", "HES", "HES.AS", "HEX.PA", "HIK.L",
        "HINDUNILVR.NS", "HL.L", "HLT", "HMSO.L", "HNN.L", "HNR1.DE", "HO.PA", "HOLN.SW", "HON", "HRL",
        "HSBA.L", "HSBC", "HSBC.L", "HST", "HUM", "IAG.AX", "IAG.L", "IBE.MC", "IBM", "ICE", "ICICIBANK.NS",
        "IDR.MC", "IDXX", "IEX", "IFX.DE", "IGG.L", "IHG.L", "IHP.L", "III.L", "ILMN", "IMB.L", "IMCD.AS",
        "IMI.L", "IMO.TO", "IMP.L", "INCH.L", "INF.L", "INF.PA", "INFY.NS", "INGA.AS", "INPP.L", "INTC",
        "INTU", "INTU.L", "IP", "IPF.L", "IPG", "IPS.PA", "IQV", "IR", "IRM", "ISP.MI", "ISRG", "ITRK.L",
        "ITUB", "ITUB4.SA", "ITV.L", "ITW", "ITX.MC", "IVZ", "JCI", "JD.L", "JDEP.AS", "JMAT.L", "JNJ",
        "JPM", "K", "KBC.BR", "KER.PA", "KEY", "KGF.L", "KHC", "KIM", "KMB", "KMI", "KNE.PA", "KO", "KOTAKBANK.NS",
        "KPN.AS", "KPN.L-i.in", "KR", "KSP.DE", "L", "L.TO", "LAND.L", "LDO.L", "LE.PA", "LEG", "LEO.MI",
        "LGEN.L", "LH", "LHA.DE", "LHX", "LI.PA", "LIN", "LIN.DE", "LIV.L", "LLC.AX", "LLD.L", "LLOY.L",
        "LLY", "LMIN.SW", "LMT", "LMT.L", "LNE.L", "LNT", "LOGN.SW", "LOH.DE", "LOND.L", "LORE.PA", "LOW",
        "LR.PA", "LSE.L", "LT.NS", "LUG.L", "LUV", "LVMH.PA", "LXS.DE", "LYB", "LYV", "M&G.L", "M&M.NS",
        "MA", "MAB.L", "MAP.MC", "MAR", "MARUTI.NS", "MAS", "MB.MI", "MBG.de", "MC.PA", "MCD", "MCD.L",
        "MCHP", "MCK", "MCO", "MCRO.L", "MDB", "MDC.L", "MDI.L", "MDLZ", "MDT", "MEL.MC", "MERK.DE", "META",
        "MFC", "MG.TO", "MGF.L", "MGGT.L", "MKS.L", "ML.PA", "MMC", "MMM", "MNDI.L", "MNG.L", "MNST", "MO",
        "MONC.IT", "MOS", "MOW.DE", "MPC", "MPI.L", "MQG.AX", "MRK", "MRK.DE", "MRL.MC", "MRO", "MRO.L",
        "MRW.L", "MS", "MS.PA", "MSCI", "MSFT", "MSI", "MT.AS", "MTB", "MTD", "MTO.L", "MTX.DE", "MU",
        "MUV2.DE", "NA.IT", "NAB.AX", "NCLH", "NCM.AX", "NDA-SE.ST", "NDAQ", "NEE", "NEM", "NESN.SW", "NET",
        "NEX.DE", "NEXI.MI", "NFLX", "NG.L", "NI", "NKE", "NLG.L", "NMC.L", "NN.AS", "NOC", "NOKIA.HE",
        "NOVN.SW", "NOVO-B.CO", "NOW", "NRG", "NRG.L", "NSC", "NST.AX", "NTAP", "NTGY.MC", "NTR.L", "NTR.TO",
        "NTRS", "NVDA", "NVR", "NWG.L", "NWL", "NWSA", "NXT.L", "O", "O2D.DE", "OCADO.L", "ODD.L", "OKE",
        "OKTA", "OML.L", "OR.PA", "ORA.PA", "ORCL", "ORNBV.HE", "ORSTED.CO", "OSB.L", "OXY", "P911.DE",
        "PAH3.DE", "PANW", "PART.SW", "PATH", "PAYC", "PAYX", "PBR", "PCAR", "PDD", "PEG", "PEP", "PETR4.SA",
        "PFE", "PFE.L", "PFG", "PFG.L", "PG", "PGR", "PH", "PHIA.AS", "PHM", "PHNX.L", "PIL.L", "PINS",
        "PKG", "PKN.L", "PLD", "PLP.L", "PLTR", "PM", "PNC", "PNN.L", "PNR", "PNW", "POLY.L", "PON.L",
        "POOL", "PPG", "PPL", "PRU", "PRU.L", "PRX.AS", "PSA", "PSN.L", "PSON.L", "PSX", "PUB.PA", "PUM.DE",
        "PVH", "PWR", "PXD", "PYPL", "PZC.L", "QAN.AX", "QBE.AX", "QCOM", "QIA.DE", "QRVO", "RACE.MI",
        "RAND.AS", "RAT.L", "RB.L", "RBLX", "RBS.L", "RCH.L", "RCI.L", "RCL", "RCP.L", "RDSA.AS", "REG",
        "REGN", "REL.L", "RELIANCE.NS", "REN.AS", "RENA.PA", "REP.MC", "REX.L", "RF", "RGRO.L", "RHI",
        "RHM.DE", "RI.PA", "RIO.AX", "RIO.L", "RL", "RMD", "RMG.L", "RMS.PA", "RNO.PA", "ROG.SW", "ROK",
        "ROKU", "ROL", "ROP", "ROST", "RR.L", "RSE.L", "RSG", "RSL.L", "RSW.L", "RTO.L", "RTX", "RWE.DE",
        "RY", "RY.TO", "SAB.L", "SAF.PA", "SAN.MC", "SAN.PA", "SAP", "SAP.DE", "SBAC", "SBIN.NS", "SBRY.L",
        "SBUX", "SCCO", "SCG.AX", "SCHW", "SCMN.SW", "SEDG", "SEE", "SGE.L", "SGE.PA", "SGO.PA", "SGP.AX",
        "SGRO.L", "SGSN.SW", "SHEL", "SHEL.L", "SHELL.AS", "SHL.DE", "SHOP.TO", "SHP.L", "SHW", "SIE.DE",
        "SJM", "SKG.L", "SLA.L", "SLB", "SLF.TO", "SLHN.SW", "SMDS.L", "SMIN.L", "SMT.L", "SN.L", "SNA",
        "SNA.PA", "SNN.L", "SNOW", "SO", "SO.PA", "SOFI", "SOLB.BR", "SOW.DE", "SPG", "SPGI", "SPOT", "SPX.L",
        "SQ", "SR.PA", "SRE", "SRE.L", "SREN.SW", "SRP.L", "SRT3.DE", "SSE.L", "STAN.L", "STE", "STJ.L",
        "STLA", "STM.MI", "STM.PA", "STO.AX", "STT", "STX", "STZ", "SU", "SU.PA", "SU.TO", "SUN.AX",
        "SUNPHARMA.NS", "SVT.L", "SW.L", "SWK", "SWKS", "SWRD.L", "SXS.DE", "SY1.DE", "SYK", "T", "T.TO",
        "TAP", "TATASTEEL.NS", "TATE.L", "TCG.L", "TCL.AX", "TCS.NS", "TD", "TD.TO", "TDG", "TE.PA", "TEF.MC",
        "TEL", "TEN.MI", "TEP.PA", "TFC", "TFG.L", "TFX", "TGS.OL", "TGT", "TITAN.NS", "TJX", "TLS.AX",
        "TLW.L", "TMO", "TMO.L", "TMUS", "TNK.L", "TRMB", "TRP", "TRP.TO", "TRV", "TSCO", "TSCO.L", "TSLA",
        "TSN", "TT", "TTD", "TTE", "TTE.PA", "TUI.L", "TW.L", "TWLO", "TXN", "TXT", "U", "UAL", "UBI.MI",
        "UBSG.SW", "UCB.BR", "UCG.MI", "UDR", "UGI", "UHR.SW", "UL", "ULVR.L", "UMG.AS", "UMG.PA", "UMPQ",
        "UNA.AS", "UNH", "UNI.PA", "UNP", "UPS", "UPST", "URI", "USB", "UTG.L", "UU.L", "V", "VALE", "VALE3.SA",
        "VDPF.DE", "VED.L", "VFC", "VICI", "VIE.PA", "VIV.PA", "VLO", "VMC", "VNA.DE", "VNO", "VOD.L",
        "VOLV-B.ST", "VOW3.DE", "VPC.L", "VRSK", "VRSN", "VRTX", "VTR", "VZ", "WBA", "WBC.AX", "WBD",
        "WCN.TO", "WDAY", "WDC", "WDI.DE", "WDS.AX", "WEC", "WEGE3.SA", "WEIR.L", "WELL", "WES.AX", "WFC",
        "WHR", "WIE.VI", "WIN.DE", "WIPRO.NS", "WKL.AS", "WM", "WMB", "WMT", "WOW.AX", "WPM", "WPP.L", "WRB",
        "WRK", "WST", "WTB.L", "WW.L", "WWD.L", "WY", "WYNN", "XEL", "XOM", "XRX", "XYL", "YUM", "ZAL.DE",
        "ZBH", "ZBRA", "ZION", "ZM", "ZS", "ZTS", "ZURN.SW"
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
