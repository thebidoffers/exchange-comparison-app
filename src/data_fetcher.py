"""
Data Fetcher Module - Using Twelve Data API
Reliable market data for global and GCC indices.
"""

import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time


@dataclass
class IndexData:
    """Data class for index information."""
    symbol: str
    name: str
    region: str
    exchange: str
    local_currency: str
    current_price: Optional[float] = None
    year_start_price: Optional[float] = None
    ytd_percent: Optional[float] = None
    market_cap: Optional[float] = None
    avg_volume: Optional[float] = None
    adtv_estimate: Optional[float] = None
    last_updated: Optional[datetime] = None
    fetch_status: str = "pending"
    error_message: Optional[str] = None


# Twelve Data symbols for indices
INDEX_CONFIGS = {
    "DFM": {
        "symbol": "DFMGI",
        "exchange": "DFM",
        "twelve_data_symbol": "DFMGI:DFM",
        "name": "DFM General Index",
        "region": "Middle East",
        "exchange_display": "DFM (Dubai)",
        "local_currency": "AED",
        "estimated_market_cap_usd": 244_000_000_000,
    },
    "ADX": {
        "symbol": "FADGI",
        "exchange": "ADX",
        "twelve_data_symbol": "FADGI:ADX",
        "name": "ADX General Index",
        "region": "Middle East",
        "exchange_display": "ADX (Abu Dhabi)",
        "local_currency": "AED",
        "estimated_market_cap_usd": 844_000_000_000,
    },
    "TASI": {
        "symbol": "TASI",
        "exchange": "Tadawul",
        "twelve_data_symbol": "TASI:TADAWUL",
        "name": "TASI",
        "region": "Middle East",
        "exchange_display": "Tadawul (Saudi)",
        "local_currency": "SAR",
        "estimated_market_cap_usd": 2_700_000_000_000,
    },
    "S&P500": {
        "symbol": "SPX",
        "exchange": "NYSE",
        "twelve_data_symbol": "SPX",
        "name": "S&P 500",
        "region": "USA",
        "exchange_display": "NYSE",
        "local_currency": "USD",
        "estimated_market_cap_usd": 50_000_000_000_000,
    },
    "NASDAQ": {
        "symbol": "IXIC",
        "exchange": "NASDAQ",
        "twelve_data_symbol": "IXIC",
        "name": "NASDAQ Composite",
        "region": "USA",
        "exchange_display": "NASDAQ",
        "local_currency": "USD",
        "estimated_market_cap_usd": 28_000_000_000_000,
    },
    "FTSE100": {
        "symbol": "FTSE",
        "exchange": "LSE",
        "twelve_data_symbol": "FTSE",
        "name": "FTSE 100",
        "region": "Europe",
        "exchange_display": "LSE (UK)",
        "local_currency": "GBP",
        "estimated_market_cap_usd": 3_300_000_000_000,
    },
    "DAX": {
        "symbol": "DAX",
        "exchange": "XETRA",
        "twelve_data_symbol": "DAX",
        "name": "DAX 40",
        "region": "Europe",
        "exchange_display": "XETRA (Germany)",
        "local_currency": "EUR",
        "estimated_market_cap_usd": 2_270_000_000_000,
    },
    "CAC40": {
        "symbol": "CAC",
        "exchange": "Euronext",
        "twelve_data_symbol": "CAC",
        "name": "CAC 40",
        "region": "Europe",
        "exchange_display": "Euronext (France)",
        "local_currency": "EUR",
        "estimated_market_cap_usd": 2_160_000_000_000,
    },
    "NIKKEI": {
        "symbol": "NI225",
        "exchange": "TSE",
        "twelve_data_symbol": "NI225",
        "name": "Nikkei 225",
        "region": "Asia",
        "exchange_display": "TSE (Japan)",
        "local_currency": "JPY",
        "estimated_market_cap_usd": 6_330_000_000_000,
    },
    "HANGSENG": {
        "symbol": "HSI",
        "exchange": "HKEX",
        "twelve_data_symbol": "HSI",
        "name": "Hang Seng",
        "region": "Asia",
        "exchange_display": "HKEX (Hong Kong)",
        "local_currency": "HKD",
        "estimated_market_cap_usd": 5_130_000_000_000,
    },
}

FX_RATES_TO_USD = {
    "USD": 1.0,
    "AED": 0.2723,
    "SAR": 0.2666,
    "GBP": 1.27,
    "EUR": 1.08,
    "JPY": 0.0067,
    "HKD": 0.128,
}

TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"


def get_api_key() -> str:
    """Get API key from Streamlit secrets or environment."""
    try:
        return st.secrets["TWELVE_DATA_API_KEY"]
    except:
        import os
        return os.environ.get("TWELVE_DATA_API_KEY", "")


def fetch_time_series(symbol: str, api_key: str, start_date: str, end_date: str) -> Tuple[Optional[List], str]:
    """
    Fetch historical time series data from Twelve Data.
    """
    try:
        url = f"{TWELVE_DATA_BASE_URL}/time_series"
        params = {
            "symbol": symbol,
            "interval": "1day",
            "start_date": start_date,
            "end_date": end_date,
            "apikey": api_key,
            "outputsize": 500,
        }
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if "code" in data and data["code"] != 200:
            return None, f"API Error: {data.get('message', 'Unknown error')}"
        
        if "values" not in data or len(data["values"]) == 0:
            return None, f"No historical data for {symbol}"
        
        return data["values"], "Success"
        
    except requests.exceptions.Timeout:
        return None, f"Timeout fetching {symbol}"
    except Exception as e:
        return None, f"Error: {str(e)}"


def calculate_ytd(symbol: str, api_key: str, year: int) -> Tuple[Optional[Dict], str]:
    """
    Calculate YTD performance for a symbol.
    """
    start_date = f"{year}-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    values, msg = fetch_time_series(symbol, api_key, start_date, end_date)
    
    if values is None:
        return None, msg
    
    try:
        # Values are returned newest first, so:
        # values[0] = most recent (current)
        # values[-1] = oldest (year start)
        current_price = float(values[0]["close"])
        year_start_price = float(values[-1]["close"])
        
        ytd_percent = ((current_price - year_start_price) / year_start_price) * 100
        
        avg_volume = None
        volumes = [float(v.get("volume", 0)) for v in values if v.get("volume")]
        if volumes and sum(volumes) > 0:
            avg_volume = sum(volumes) / len(volumes)
        
        result = {
            "current_price": current_price,
            "year_start_price": year_start_price,
            "ytd_percent": round(ytd_percent, 2),
            "avg_volume": avg_volume,
            "data_points": len(values),
            "start_date": values[-1]["datetime"],
            "end_date": values[0]["datetime"],
        }
        
        return result, "Success"
        
    except (KeyError, IndexError, ValueError) as e:
        return None, f"Error parsing data: {str(e)}"


def fetch_all_indices(selected_indices: List[str] = None, year: int = None) -> Tuple[List[Dict], Dict]:
    """
    Fetch data for all selected indices using Twelve Data API.
    """
    if selected_indices is None:
        selected_indices = list(INDEX_CONFIGS.keys())
    
    if year is None:
        year = datetime.now().year
    
    api_key = get_api_key()
    
    if not api_key:
        return [], {"success": [], "failed": [{"index": "ALL", "error": "No API key configured. Add TWELVE_DATA_API_KEY to Streamlit secrets."}], "timestamp": datetime.now().isoformat()}
    
    results = []
    status = {"success": [], "failed": [], "timestamp": datetime.now().isoformat()}
    
    for index_key in selected_indices:
        if index_key not in INDEX_CONFIGS:
            status["failed"].append({"index": index_key, "error": "Unknown index"})
            continue
        
        config = INDEX_CONFIGS[index_key]
        symbol = config["twelve_data_symbol"]
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
        
        data, msg = calculate_ytd(symbol, api_key, year)
        
        if data:
            adtv_usd = None
            if data.get("avg_volume") and data["avg_volume"] > 0:
                avg_price = data["current_price"]
                adtv_local = data["avg_volume"] * avg_price
                fx_rate = FX_RATES_TO_USD.get(config["local_currency"], 1.0)
                adtv_usd = adtv_local * fx_rate
            
            result = {
                "key": index_key,
                "region": config["region"],
                "exchange": config["exchange_display"],
                "index_name": config["name"],
                "local_currency": config["local_currency"],
                "ytd_percent": data["ytd_percent"],
                "year_start_price": data["year_start_price"],
                "current_price": data["current_price"],
                "market_cap_usd": config.get("estimated_market_cap_usd"),
                "adtv_usd": adtv_usd,
                "avg_volume": data.get("avg_volume"),
                "last_updated": datetime.now().isoformat(),
                "data_source": f"Twelve Data ({symbol})",
                "data_range": f"{data.get('start_date', 'N/A')} to {data.get('end_date', 'N/A')}",
                "fetch_status": "success",
            }
            results.append(result)
            status["success"].append(index_key)
        else:
            result = {
                "key": index_key,
                "region": config["region"],
                "exchange": config["exchange_display"],
                "index_name": config["name"],
                "local_currency": config["local_currency"],
                "ytd_percent": None,
                "market_cap_usd": config.get("estimated_market_cap_usd"),
                "adtv_usd": None,
                "last_updated": datetime.now().isoformat(),
                "data_source": "Fetch failed",
                "fetch_status": "failed",
                "error_message": msg,
            }
            results.append(result)
            status["failed"].append({"index": index_key, "error": msg})
    
    return results, status


def get_available_indices() -> List[Dict]:
    """Get list of available indices."""
    return [
        {
            "key": key,
            "name": config["name"],
            "exchange": config["exchange_display"],
            "region": config["region"],
            "symbol": config["twelve_data_symbol"],
        }
        for key, config in INDEX_CONFIGS.items()
    ]


def create_comparison_df(results: List[Dict]) -> pd.DataFrame:
    """Create a formatted DataFrame from fetch results."""
    def format_market_cap(val):
        if val is None:
            return "N/A"
        if val >= 1e12:
            return f"${val/1e12:.2f}T"
        elif val >= 1e9:
            return f"${val/1e9:.1f}B"
        else:
            return f"${val/1e6:.0f}M"
    
    def format_adtv(val):
        if val is None:
            return "N/A"
        if val >= 1e9:
            return f"${val/1e9:.1f}B"
        elif val >= 1e6:
            return f"${val/1e6:.0f}M"
        else:
            return f"${val/1e3:.0f}K"
    
    def format_ytd(val):
        if val is None:
            return "N/A"
        sign = "+" if val >= 0 else ""
        return f"{sign}{val:.2f}%"
    
    data = []
    for r in results:
        data.append({
            "Region": r["region"],
            "Exchange": r["exchange"],
            "Index Name": r["index_name"],
            "YTD % Change": format_ytd(r.get("ytd_percent")),
            "Market Cap (USD)": format_market_cap(r.get("market_cap_usd")),
            "Avg Daily Value (USD)": format_adtv(r.get("adtv_usd")),
            "_ytd_raw": r.get("ytd_percent"),
            "_cap_raw": r.get("market_cap_usd"),
            "_adtv_raw": r.get("adtv_usd"),
        })
    
    return pd.DataFrame(data)


def update_market_caps(results: List[Dict], manual_caps: Dict[str, float]) -> List[Dict]:
    """Update market cap values with manual entries."""
    for r in results:
        if r["key"] in manual_caps:
            r["market_cap_usd"] = manual_caps[r["key"]]
            r["data_source"] = r.get("data_source", "") + " + Manual market cap"
    return results
