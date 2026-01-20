"""
Data Fetcher Module - Auto-fetch exchange data from Yahoo Finance
This module retrieves real market data for global indices.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


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


INDEX_CONFIGS = {
    "DFM": {
        "symbol": "^DFMGI.AE",
        "name": "DFM General Index",
        "region": "Middle East",
        "exchange": "DFM (Dubai)",
        "local_currency": "AED",
        "market_cap_source": "manual",
        "estimated_market_cap_usd": 244_000_000_000,
        "avg_price_per_share": 5.0,
    },
    "ADX": {
        "symbol": "^FTFADGI",
        "alt_symbols": ["FADGI.AD", "^ADI"],
        "name": "ADX General Index",
        "region": "Middle East",
        "exchange": "ADX (Abu Dhabi)",
        "local_currency": "AED",
        "market_cap_source": "manual",
        "estimated_market_cap_usd": 844_000_000_000,
        "avg_price_per_share": 10.0,
    },
    "TASI": {
        "symbol": "^TASI.SR",
        "name": "TASI",
        "region": "Middle East",
        "exchange": "Tadawul (Saudi)",
        "local_currency": "SAR",
        "market_cap_source": "manual",
        "estimated_market_cap_usd": 2_700_000_000_000,
        "avg_price_per_share": 50.0,
    },
    "S&P500": {
        "symbol": "^GSPC",
        "name": "S&P 500",
        "region": "USA",
        "exchange": "NYSE",
        "local_currency": "USD",
        "market_cap_source": "estimate",
        "estimated_market_cap_usd": 50_000_000_000_000,
        "avg_price_per_share": 150.0,
    },
    "NASDAQ": {
        "symbol": "^IXIC",
        "name": "NASDAQ Composite",
        "region": "USA",
        "exchange": "NASDAQ",
        "local_currency": "USD",
        "market_cap_source": "estimate",
        "estimated_market_cap_usd": 28_000_000_000_000,
        "avg_price_per_share": 100.0,
    },
    "FTSE100": {
        "symbol": "^FTSE",
        "name": "FTSE 100",
        "region": "Europe",
        "exchange": "LSE (UK)",
        "local_currency": "GBP",
        "market_cap_source": "estimate",
        "estimated_market_cap_usd": 3_300_000_000_000,
        "avg_price_per_share": 1000.0,
    },
    "DAX": {
        "symbol": "^GDAXI",
        "name": "DAX 40",
        "region": "Europe",
        "exchange": "XETRA (Germany)",
        "local_currency": "EUR",
        "market_cap_source": "estimate",
        "estimated_market_cap_usd": 2_270_000_000_000,
        "avg_price_per_share": 200.0,
    },
    "CAC40": {
        "symbol": "^FCHI",
        "name": "CAC 40",
        "region": "Europe",
        "exchange": "Euronext (France)",
        "local_currency": "EUR",
        "market_cap_source": "estimate",
        "estimated_market_cap_usd": 2_160_000_000_000,
        "avg_price_per_share": 100.0,
    },
    "NIKKEI": {
        "symbol": "^N225",
        "name": "Nikkei 225",
        "region": "Asia",
        "exchange": "TSE (Japan)",
        "local_currency": "JPY",
        "market_cap_source": "estimate",
        "estimated_market_cap_usd": 6_330_000_000_000,
        "avg_price_per_share": 3000.0,
    },
    "HANGSENG": {
        "symbol": "^HSI",
        "name": "Hang Seng",
        "region": "Asia",
        "exchange": "HKEX (Hong Kong)",
        "local_currency": "HKD",
        "market_cap_source": "estimate",
        "estimated_market_cap_usd": 5_130_000_000_000,
        "avg_price_per_share": 50.0,
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


def fetch_index_data(symbol: str, year: int = None) -> Tuple[Optional[Dict], str]:
    """Fetch index data from Yahoo Finance."""
    if year is None:
        year = datetime.now().year
    
    try:
        ticker = yf.Ticker(symbol)
        start_date = f"{year}-01-01"
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            return None, f"No data available for {symbol}"
        
        year_start_price = hist['Close'].iloc[0]
        current_price = hist['Close'].iloc[-1]
        ytd_percent = ((current_price - year_start_price) / year_start_price) * 100
        avg_volume = hist['Volume'].mean() if 'Volume' in hist.columns else None
        
        data = {
            "current_price": current_price,
            "year_start_price": year_start_price,
            "ytd_percent": round(ytd_percent, 2),
            "avg_volume": avg_volume,
            "last_updated": datetime.now(),
            "data_points": len(hist),
            "start_date": hist.index[0].strftime("%Y-%m-%d"),
            "end_date": hist.index[-1].strftime("%Y-%m-%d"),
        }
        
        return data, "Success"
        
    except Exception as e:
        return None, f"Error fetching {symbol}: {str(e)}"


def fetch_all_indices(selected_indices: List[str] = None, year: int = None) -> Tuple[List[Dict], Dict]:
    """Fetch data for all selected indices."""
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
        symbol = config["symbol"]
        
        data, msg = fetch_index_data(symbol, year)
        
        if data is None and "alt_symbol" in config:
            data, msg = fetch_index_data(config["alt_symbol"], year)
        
        if data:
            adtv_local = None
            adtv_usd = None
            if data.get("avg_volume"):
                avg_price = config.get("avg_price_per_share", data["current_price"])
                adtv_local = data["avg_volume"] * avg_price
                fx_rate = FX_RATES_TO_USD.get(config["local_currency"], 1.0)
                adtv_usd = adtv_local * fx_rate
            
            market_cap_usd = config.get("estimated_market_cap_usd")
            
            result = {
                "key": index_key,
                "region": config["region"],
                "exchange": config["exchange"],
                "index_name": config["name"],
                "local_currency": config["local_currency"],
                "ytd_percent": data["ytd_percent"],
                "year_start_price": data["year_start_price"],
                "current_price": data["current_price"],
                "market_cap_usd": market_cap_usd,
                "adtv_local": adtv_local,
                "adtv_usd": adtv_usd,
                "avg_volume": data.get("avg_volume"),
                "last_updated": data["last_updated"].isoformat(),
                "data_source": f"Yahoo Finance ({symbol})",
                "fetch_status": "success",
            }
            results.append(result)
            status["success"].append(index_key)
        else:
            result = {
                "key": index_key,
                "region": config["region"],
                "exchange": config["exchange"],
                "index_name": config["name"],
                "local_currency": config["local_currency"],
                "ytd_percent": None,
                "market_cap_usd": config.get("estimated_market_cap_usd"),
                "adtv_usd": None,
                "last_updated": datetime.now().isoformat(),
                "data_source": "Manual (fetch failed)",
                "fetch_status": "failed",
                "error_message": msg,
            }
            results.append(result)
            status["failed"].append({"index": index_key, "error": msg})
    
    return results, status


def get_available_indices() -> List[Dict]:
    """Get list of available indices with their configurations."""
    return [
        {
            "key": key,
            "name": config["name"],
            "exchange": config["exchange"],
            "region": config["region"],
            "symbol": config["symbol"],
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
