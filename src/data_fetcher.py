"""
Data Fetcher Module - Using Investpy (Investing.com)
FREE data source with NO rate limits for global indices including GCC markets.
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time

# Try to import investpy
try:
    import investpy
    INVESTPY_AVAILABLE = True
except ImportError:
    INVESTPY_AVAILABLE = False


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


# Index configurations for Investing.com via investpy
# Format: investpy uses index name and country
INDEX_CONFIGS = {
    "DFM": {
        "investpy_name": "DFM General",
        "country": "dubai",
        "name": "DFM General Index",
        "region": "Middle East",
        "exchange_display": "DFM (Dubai)",
        "local_currency": "AED",
        "estimated_market_cap_usd": 244_000_000_000,
    },
    "ADX": {
        "investpy_name": "ADX General",
        "country": "abu dhabi",
        "name": "ADX General Index",
        "region": "Middle East",
        "exchange_display": "ADX (Abu Dhabi)",
        "local_currency": "AED",
        "estimated_market_cap_usd": 844_000_000_000,
    },
    "TASI": {
        "investpy_name": "Tadawul All Share",
        "country": "saudi arabia",
        "name": "TASI",
        "region": "Middle East",
        "exchange_display": "Tadawul (Saudi)",
        "local_currency": "SAR",
        "estimated_market_cap_usd": 2_700_000_000_000,
    },
    "S&P500": {
        "investpy_name": "S&P 500",
        "country": "united states",
        "name": "S&P 500",
        "region": "USA",
        "exchange_display": "NYSE",
        "local_currency": "USD",
        "estimated_market_cap_usd": 50_000_000_000_000,
    },
    "NASDAQ": {
        "investpy_name": "Nasdaq",
        "country": "united states",
        "name": "NASDAQ Composite",
        "region": "USA",
        "exchange_display": "NASDAQ",
        "local_currency": "USD",
        "estimated_market_cap_usd": 28_000_000_000_000,
    },
    "FTSE100": {
        "investpy_name": "FTSE 100",
        "country": "united kingdom",
        "name": "FTSE 100",
        "region": "Europe",
        "exchange_display": "LSE (UK)",
        "local_currency": "GBP",
        "estimated_market_cap_usd": 3_300_000_000_000,
    },
    "DAX": {
        "investpy_name": "DAX",
        "country": "germany",
        "name": "DAX 40",
        "region": "Europe",
        "exchange_display": "XETRA (Germany)",
        "local_currency": "EUR",
        "estimated_market_cap_usd": 2_270_000_000_000,
    },
    "CAC40": {
        "investpy_name": "CAC 40",
        "country": "france",
        "name": "CAC 40",
        "region": "Europe",
        "exchange_display": "Euronext (France)",
        "local_currency": "EUR",
        "estimated_market_cap_usd": 2_160_000_000_000,
    },
    "NIKKEI": {
        "investpy_name": "Nikkei 225",
        "country": "japan",
        "name": "Nikkei 225",
        "region": "Asia",
        "exchange_display": "TSE (Japan)",
        "local_currency": "JPY",
        "estimated_market_cap_usd": 6_330_000_000_000,
    },
    "HANGSENG": {
        "investpy_name": "Hang Seng",
        "country": "hong kong",
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


def calculate_ytd_investpy(index_name: str, country: str, year: int) -> Tuple[Optional[Dict], str]:
    """
    Calculate YTD performance using investpy (Investing.com data).
    """
    if not INVESTPY_AVAILABLE:
        return None, "investpy library not installed. Run: pip install investpy"
    
    try:
        # Get date range
        start_date = f"01/01/{year}"
        end_date = datetime.now().strftime("%d/%m/%Y")
        
        # Fetch historical data from Investing.com
        df = investpy.get_index_historical_data(
            index=index_name,
            country=country,
            from_date=start_date,
            to_date=end_date
        )
        
        if df.empty:
            return None, f"No data returned for {index_name}"
        
        # Get year start and current prices
        year_start_price = df['Close'].iloc[0]
        current_price = df['Close'].iloc[-1]
        
        # Calculate YTD percentage
        ytd_percent = ((current_price - year_start_price) / year_start_price) * 100
        
        # Calculate average volume if available
        avg_volume = None
        if 'Volume' in df.columns:
            volumes = df['Volume'].dropna()
            if len(volumes) > 0 and volumes.sum() > 0:
                avg_volume = volumes.mean()
        
        result = {
            "current_price": float(current_price),
            "year_start_price": float(year_start_price),
            "ytd_percent": round(ytd_percent, 2),
            "avg_volume": avg_volume,
            "data_points": len(df),
            "start_date": df.index[0].strftime("%Y-%m-%d"),
            "end_date": df.index[-1].strftime("%Y-%m-%d"),
        }
        
        return result, "Success"
        
    except Exception as e:
        error_msg = str(e)
        # Check for common errors
        if "not found" in error_msg.lower() or "ERR#0045" in error_msg:
            return None, f"Index '{index_name}' not found in {country}. Check index name."
        elif "connection" in error_msg.lower():
            return None, "Connection error - check internet connection"
        else:
            return None, f"Error: {error_msg}"


def fetch_all_indices(selected_indices: List[str] = None, year: int = None) -> Tuple[List[Dict], Dict]:
    """
    Fetch data for all selected indices using investpy (Investing.com).
    FREE and NO rate limits!
    """
    if not INVESTPY_AVAILABLE:
        return [], {
            "success": [], 
            "failed": [{"index": "ALL", "error": "investpy not installed. Add 'investpy' to requirements.txt"}], 
            "timestamp": datetime.now().isoformat()
        }
    
    if selected_indices is None:
        selected_indices = list(INDEX_CONFIGS.keys())
    
    if year is None:
        year = datetime.now().year
    
    results = []
    status = {"success": [], "failed": [], "timestamp": datetime.now().isoformat()}
    
    for index_key in selected_indices:
        if index_key not in INDEX_CONFIGS:
            status["failed"].append({"index": index_key, "error": "Unknown index"})
            continue
        
        config = INDEX_CONFIGS[index_key]
        investpy_name = config["investpy_name"]
        country = config["country"]
        
        # Small delay to be polite to Investing.com servers
        time.sleep(0.3)
        
        data, msg = calculate_ytd_investpy(investpy_name, country, year)
        
        if data:
            # Calculate ADTV in USD if volume data available
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
                "data_source": f"Investing.com ({investpy_name})",
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
            "investpy_name": config["investpy_name"],
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


def search_available_indices(country: str = None) -> List[Dict]:
    """
    Search for available indices on Investing.com.
    Useful for finding correct index names.
    """
    if not INVESTPY_AVAILABLE:
        return []
    
    try:
        if country:
            indices = investpy.get_indices(country=country)
        else:
            indices = investpy.get_indices_list(country="united states")
        return indices.to_dict('records') if hasattr(indices, 'to_dict') else []
    except Exception as e:
        return []
