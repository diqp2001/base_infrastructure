"""
Configuration settings for Market Making SPX Call Spread Project
"""

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.derivatives.option.index_future_option import IndexFutureOption
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.entities.finance.financial_assets.index.index import Index
from src.application.services.data.entities.factor.factor_library.factor_definition_config import FACTOR_LIBRARY
# Base configuration
BASE_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
DATA_PATH = BASE_PROJECT_ROOT / "data"
# Database Configuration
CONFIG_TEST = {
    'DB_TYPE': 'sql_server',
    
    'DB_PATH': BASE_PROJECT_ROOT / 'base_infrastructure.db',
    'CONNECTION_STRING': f'sqlite:///{BASE_PROJECT_ROOT}/base_infrastructure.db'
}

# Default configuration for market making SPX call spread project


DEFAULT_CONFIG = {
    # Project settings
    'project_name': 'market_making_spx_call_spread',
    'version': '1.0.0',
    'universe' : {
        CompanyShare: ["AAPL","IBM"],
        IndexFutureOption: ["ESZ6 C6850","ESZ6 P6850"
            # # ES future options - use underlying root 'ES' for options, not future symbol 'ESZ6'
            # {"symbol": "ESZ6 C6850"},#, "strike_price": 6850.0, "expiry": "20261218", "option_type": "C"},  # ATM Call (December expiry for ES options)
            # {"symbol": "ESZ6 P6850"},#, "strike_price": 6850.0, "expiry": "20261218", "option_type": "P"},  # ATM Put
            #   # ITM Call 'future: ESZ6 option type: C strike:6850'
        ],
        Index: ["SPX"],
        IndexFuture: ["ESZ6"]
    },
    'target_factor': {
        IndexFutureOption: [
            {"symbol": "ESZ6 C6850"},#, "strike_price": 6850.0, "expiry": "20261218", "option_type": "C"},  # ATM Call
            {"symbol": "ESZ6 P6850"},#, "strike_price": 6850.0, "expiry": "20261218", "option_type": "P"},  # ATM Put
        ],
        Index: ["SPX"],
        IndexFuture: ["ESZ6"]
    },
    # SPX Configuration
    'underlying_symbol': 'SPX',
    'underlying_exchange': 'CBOE',
    'underlying_currency': 'USD',
    
    # Call Spread Configuration
    'spread_type': 'bull_call_spread',  # or 'bear_call_spread'
    'default_dte_range': (7, 45),  # Days to expiration range
    'default_delta_range': (0.15, 0.45),  # Delta range for strikes
    'max_spread_width': 50,  # Maximum spread width in points
    
    # Market Data Configuration
    'historical_data_duration': '6 M',  # 6 months of historical data
    'bar_size_setting': '5 mins',
    'option_data_duration': '30 D',  # 30 days of option data
    
    # Risk Management
    'max_position_size': 10,  # Maximum number of spreads
    'max_daily_loss': 5000,  # Maximum daily loss in USD
    'max_gamma_exposure': 1000,  # Maximum gamma exposure
    'min_time_to_expiry': 7,  # Minimum days to expiry before closing
    
    # Pricing Configuration
    'volatility_model': 'implied',  # 'implied' or 'historical'
    'interest_rate': 0.05,  # Risk-free rate
    'dividend_yield': 0.015,  # SPX dividend yield
    
    # Trading Configuration
    'trading_hours': {
        'start': '09:30',
        'end': '16:00',
        'timezone': 'US/Eastern'
    },
    
    # Backtesting Configuration
    'backtest_start': '2026-02-02 09:30:00',
    'backtest_end': '2026-02-04 14:30:00',
    # frequence
    'config_interval' : {'custom_interval_minutes': 5},
    'initial_capital': 100000,
    'commission_per_contract': 0.65,
    
    # Model Training
    'model_type' : "pricing",
    'training_window': 252,  # 1 year of trading days
    'validation_split': 0.2,
    'test_split': 0.2,
    
    # Factors for modeling - only future_index_library and index_library factors
    'factors': [
        # Price factors from future_index_library
        FACTOR_LIBRARY["future_index_library"]["open"],
        FACTOR_LIBRARY["future_index_library"]["high"],
        FACTOR_LIBRARY["future_index_library"]["low"],
        FACTOR_LIBRARY["future_index_library"]["close"],
        FACTOR_LIBRARY["future_index_library"]["volume"],
        
        # Future return factors (daily, weekly, monthly)
        FACTOR_LIBRARY["future_index_library"]["return_daily"],
        
        # Index return factors (daily, weekly, monthly)
        FACTOR_LIBRARY["index_library"]["return_daily"],
        FACTOR_LIBRARY["future_index_option_library"]["return_daily"],
        FACTOR_LIBRARY["company_share_library"]["return_daily"]
    ],

    
    
    # MLflow tracking
    'mlflow_experiment_name': 'market_making_spx_call_spread',
    'mlflow_tracking_uri': './mlruns',
    
    # Web interface
    'web_interface_port': 5001,
    'enable_web_interface': True,
}

def get_config() -> Dict[str, Any]:
    """Get the current configuration."""
    return DEFAULT_CONFIG.copy()

# def get_spx_contract_config() -> Dict[str, Any]:
#     """Get SPX-specific contract configuration."""
#     return {
#         'symbol': DEFAULT_CONFIG['underlying_symbol'],
#         'exchange': DEFAULT_CONFIG['underlying_exchange'],
#         'currency': DEFAULT_CONFIG['underlying_currency'],
#         'sec_type': 'IND',  # Index
#         'multiplier': 100,
#     }

# def get_option_chain_config() -> Dict[str, Any]:
#     """Get option chain configuration for SPX options."""
#     return {
#         'symbol': 'SPX',
#         'exchange': 'CBOE', 
#         'currency': 'USD',
#         'sec_type': 'OPT',
#         'multiplier': 100,
#         'dte_range': DEFAULT_CONFIG['default_dte_range'],
#         'delta_range': DEFAULT_CONFIG['default_delta_range'],
#     }

def get_trading_config() -> Dict[str, Any]:
    """Get trading configuration."""
    return {
        'max_position_size': DEFAULT_CONFIG['max_position_size'],
        'max_daily_loss': DEFAULT_CONFIG['max_daily_loss'],
        'max_gamma_exposure': DEFAULT_CONFIG['max_gamma_exposure'],
        'commission_per_contract': DEFAULT_CONFIG['commission_per_contract'],
        'trading_hours': DEFAULT_CONFIG['trading_hours'],
    }


#sp500
# CompanyShare = [
# "AAPL","ABBV","ABNB","ABT","ACGL","ACN","ADBE","ADI","ADM","ADP","ADSK",
# "AEE","AEP","AES","AFL","AIG","AIZ","AJG","AKAM","ALB","ALGN","ALL","AMAT",
# "AMD","AME","AMGN","AMP","AMT","AMZN","ANET","ANSS","AON","APA","APD","APH",
# "APTV","ARE","ATO","AVB","AVGO","AVY","AXP","AZO","BA","BAC","BALL","BAX",
# "BBWI","BBY","BDX","BEN","BF.B","BG","BIIB","BK","BKNG","BKR","BLK","BMY",
# "BR","BRK.B","BSX","BWA","C","CAG","CAH","CARR","CAT","CB","CBOE","CBRE",
# "CCI","CCL","CDNS","CDW","CE","CEG","CF","CFG","CHD","CHRW","CHTR","CI",
# "CINF","CL","CLX","CMA","CMCSA","CME","CMG","CMI","CMS","CNC","CNP","COF",
# "COO","COP","COST","CPB","CPRT","CPT","CRL","CRM","CSCO","CSGP","CSX","CTAS",
# "CTLT","CTRA","CTSH","CTVA","CVS","CVX","D","DAL","DD","DE","DFS","DG",
# "DGX","DHI","DHR","DIS","DLR","DLTR","DOV","DOW","DPZ","DRI","DTE","DUK",
# "DVA","DVN","DXCM","EA","EBAY","ECL","ED","EFX","EG","EIX","EL","ELV","EMN",
# "EMR","ENPH","EOG","EPAM","EQIX","EQR","EQT","ES","ESS","ETN","ETR","EVRG",
# "EW","EXC","EXPD","EXPE","EXR","F","FANG","FAST","FCX","FDS","FDX","FE",
# "FFIV","FI","FICO","FIS","FITB","FLT","FMC","FOX","FOXA","FRT","FTNT","FTV",
# "GD","GE","GEHC","GEN","GILD","GIS","GL","GLW","GM","GNRC","GOOG","GOOGL",
# "GPC","GPN","GRMN","GS","GWW","HAL","HAS","HBAN","HCA","HD","HES","HIG",
# "HII","HLT","HOLX","HON","HPE","HPQ","HRL","HSIC","HST","HSY","HUM","HWM",
# "IBM","ICE","IDXX","IEX","IFF","ILMN","INCY","INTC","INTU","INVH","IP","IPG",
# "IQV","IR","IRM","ISRG","IT","ITW","IVZ","J","JBHT","JBL","JCI","JKHY","JNJ",
# "JNPR","JPM","K","KDP","KEY","KEYS","KHC","KIM","KLAC","KMB","KMI","KMX",
# "KO","KR","KVUE","L","LDOS","LEN","LH","LHX","LIN","LKQ","LLY","LMT","LNT",
# "LOW","LRCX","LULU","LVS","LW","LYB","LYV","MA","MAA","MAR","MAS","MCD",
# "MCHP","MCK","MCO","MDLZ","MDT","MET","META","MGM","MHK","MKC","MKTX","MLM",
# "MMC","MMM","MNST","MO","MOS","MPC","MPWR","MRK","MRNA","MRO","MS","MSCI",
# "MSFT","MSI","MTB","MTCH","MTD","MU","NCLH","NDAQ","NDSN","NEE","NEM","NFLX",
# "NI","NKE","NOC","NOW","NRG","NSC","NTAP","NTRS","NUE","NVDA","NVR","NWS",
# "NWSA","NXPI","O","ODFL","OKE","OMC","ON","ORCL","ORLY","OTIS","OXY","PANW",
# "PARA","PAYC","PAYX","PCAR","PCG","PEAK","PEG","PEP","PFE","PFG","PG","PGR",
# "PH","PHM","PKG","PLD","PM","PNC","PNR","PNW","PODD","POOL","PPG","PPL",
# "PRU","PSA","PSX","PTC","PWR","PYPL","QCOM","QRVO","RCL","REG","REGN","RF",
# "RHI","RJF","RL","RMD","ROK","ROL","ROP","ROST","RSG","RTX","RVTY","SBAC",
# "SBUX","SCHW","SHW","SJM","SLB","SNA","SNPS","SO","SPG","SPGI","SRE","STE",
# "STLD","STT","STX","STZ","SWK","SWKS","SYF","SYK","SYY","T","TAP","TDG","TDY",
# "TECH","TEL","TER","TFC","TFX","TGT","TJX","TMO","TMUS","TPR","TRGP","TRMB",
# "TROW","TRV","TSCO","TSLA","TSN","TT","TTWO","TXN","TXT","TYL","UAL","UBER",
# "UDR","UHS","ULTA","UNH","UNP","UPS","URI","USB","V","VICI","VLO","VMC","VRSK",
# "VRSN","VRTX","VTR","VTRS","VZ","WAB","WAT","WBA","WBD","WDAY","WDC","WEC",
# "WELL","WFC","WHR","WM","WMB","WMT","WRB","WRK","WST","WTW","WY","WYNN","XEL",
# "XOM","XRAY","XYL","YUM","ZBH","ZBRA","ZTS"
# ]
# #DOW
# CompanyShare = [
# "AAPL","AMGN","AXP","BA","CAT","CRM","CSCO","CVX","DIS","DOW",
# "GS","HD","HON","IBM","INTC","JNJ","JPM","KO","MCD","MMM",
# "MRK","MSFT","NKE","PG","TRV","UNH","V","VZ","WBA","WMT"
# ]