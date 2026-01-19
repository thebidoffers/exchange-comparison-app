"""
FX Rate retrieval and management module.
Supports live spot rates, manual entry, and average calculation.
"""

import requests
from datetime import datetime, date
from typing import Dict, Optional, Tuple
import pandas as pd
from .schemas import Currency, FXMode, FXRate, FXConfiguration


class FXError(Exception):
    """Custom exception for FX-related errors."""
    pass


def get_live_fx_rates(
    base_currencies: list[str],
    quote_currency: str = "USD",
    source: str = "exchangerate.host"
) -> Tuple[Dict[str, FXRate], str]:
    """
    Fetch live FX spot rates from a free API.
    
    Args:
        base_currencies: List of currency codes to get rates for
        quote_currency: Target currency (default USD)
        source: API source to use
    
    Returns:
        Tuple of (dict of currency->FXRate, status message)
    """
    rates = {}
    errors = []
    timestamp = datetime.utcnow()
    
    # Primary: exchangerate.host (free, no API key required for basic usage)
    # Fallback: ECB rates via frankfurter.app
    
    for currency in base_currencies:
        if currency == quote_currency:
            # Same currency, rate is 1.0
            rates[currency] = FXRate(
                base_currency=Currency(currency),
                quote_currency=Currency(quote_currency),
                rate=1.0,
                source="identity",
                timestamp=timestamp
            )
            continue
        
        rate = None
        used_source = source
        
        # Try exchangerate.host first
        if source == "exchangerate.host":
            try:
                # Using exchangerate.host free API
                url = f"https://api.exchangerate.host/convert?from={currency}&to={quote_currency}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("result"):
                        rate = float(data["result"])
            except Exception as e:
                errors.append(f"{currency}: exchangerate.host failed - {str(e)}")
        
        # Fallback to frankfurter.app (ECB rates)
        if rate is None:
            try:
                url = f"https://api.frankfurter.app/latest?from={currency}&to={quote_currency}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if quote_currency in data.get("rates", {}):
                        rate = float(data["rates"][quote_currency])
                        used_source = "ECB via frankfurter.app"
            except Exception as e:
                errors.append(f"{currency}: frankfurter.app failed - {str(e)}")
        
        # Fallback to static rates for GCC currencies (pegged to USD)
        if rate is None:
            static_rates = {
                "AED": 0.2723,  # AED is pegged at 3.6725 AED/USD
                "SAR": 0.2666,  # SAR is pegged at 3.75 SAR/USD
                "KWD": 3.25,    # Approximate, managed float
                "QAR": 0.2747,  # QAR is pegged at 3.64 QAR/USD
                "HKD": 0.128,   # HKD pegged to USD
            }
            if currency in static_rates:
                rate = static_rates[currency]
                used_source = "static_pegged_rate"
                errors.append(f"{currency}: Using static pegged rate (live fetch failed)")
        
        if rate is not None:
            rates[currency] = FXRate(
                base_currency=Currency(currency) if currency in Currency.__members__ else currency,
                quote_currency=Currency(quote_currency),
                rate=rate,
                source=used_source,
                timestamp=timestamp
            )
        else:
            errors.append(f"{currency}: Could not retrieve rate")
    
    status = "All rates fetched successfully" if not errors else "; ".join(errors)
    return rates, status


def calculate_average_fx_from_df(
    fx_df: pd.DataFrame,
    start_date: date,
    end_date: date,
    currency_columns: list[str]
) -> Tuple[Dict[str, float], str]:
    """
    Calculate average FX rates from a DataFrame for a given date range.
    
    Args:
        fx_df: DataFrame with 'date' column and currency columns (e.g., 'AEDUSD')
        start_date: Start of date range
        end_date: End of date range
        currency_columns: List of column names for currency pairs
    
    Returns:
        Tuple of (dict of currency->average_rate, status message)
    """
    try:
        # Ensure date column is datetime
        if 'date' not in fx_df.columns:
            return {}, "Error: 'date' column not found in FX data"
        
        fx_df['date'] = pd.to_datetime(fx_df['date']).dt.date
        
        # Filter to date range
        mask = (fx_df['date'] >= start_date) & (fx_df['date'] <= end_date)
        filtered_df = fx_df[mask]
        
        if filtered_df.empty:
            return {}, f"No FX data found for date range {start_date} to {end_date}"
        
        averages = {}
        missing = []
        
        for col in currency_columns:
            if col in filtered_df.columns:
                avg = filtered_df[col].mean()
                if pd.notna(avg):
                    # Extract currency code from column name (e.g., 'AEDUSD' -> 'AED')
                    currency = col.replace('USD', '')
                    averages[currency] = float(avg)
                else:
                    missing.append(col)
            else:
                missing.append(col)
        
        status = f"Calculated averages from {len(filtered_df)} days"
        if missing:
            status += f"; Missing columns: {', '.join(missing)}"
        
        return averages, status
        
    except Exception as e:
        return {}, f"Error calculating average FX: {str(e)}"


def get_fx_rates(
    config: FXConfiguration,
    required_currencies: list[str],
    date_range: Optional[Tuple[date, date]] = None
) -> Tuple[Dict[str, FXRate], str]:
    """
    Get FX rates based on configuration mode.
    
    Args:
        config: FX configuration object
        required_currencies: List of currencies needed
        date_range: Optional tuple of (start_date, end_date) for average mode
    
    Returns:
        Tuple of (dict of currency->FXRate, status message)
    """
    timestamp = datetime.utcnow()
    rates = {}
    
    if config.mode == FXMode.LIVE_SPOT:
        return get_live_fx_rates(
            required_currencies,
            config.output_currency.value if isinstance(config.output_currency, Currency) else config.output_currency,
            config.live_fx_source
        )
    
    elif config.mode == FXMode.MANUAL:
        # Use manually provided rates
        for currency in required_currencies:
            if currency == config.output_currency:
                rates[currency] = FXRate(
                    base_currency=currency,
                    quote_currency=config.output_currency,
                    rate=1.0,
                    source="identity",
                    timestamp=timestamp
                )
            elif currency in config.manual_rates:
                rates[currency] = FXRate(
                    base_currency=currency,
                    quote_currency=config.output_currency,
                    rate=config.manual_rates[currency],
                    source="manual_entry",
                    timestamp=timestamp
                )
        
        missing = [c for c in required_currencies if c not in rates]
        status = "Manual rates applied" if not missing else f"Missing manual rates for: {', '.join(missing)}"
        return rates, status
    
    elif config.mode == FXMode.AVERAGE:
        if config.average_fx_data is None:
            return {}, "No average FX data provided"
        
        if date_range is None:
            return {}, "Date range required for average FX calculation"
        
        # Convert dict back to DataFrame if needed
        if isinstance(config.average_fx_data, dict):
            fx_df = pd.DataFrame(config.average_fx_data)
        else:
            fx_df = config.average_fx_data
        
        # Determine column names
        currency_columns = [f"{c}USD" for c in required_currencies if c != config.output_currency]
        
        averages, status = calculate_average_fx_from_df(
            fx_df, date_range[0], date_range[1], currency_columns
        )
        
        for currency, rate in averages.items():
            rates[currency] = FXRate(
                base_currency=currency,
                quote_currency=config.output_currency,
                rate=rate,
                source=f"average_{date_range[0]}_to_{date_range[1]}",
                timestamp=timestamp
            )
        
        # Add identity rate for output currency
        if config.output_currency in required_currencies:
            rates[str(config.output_currency)] = FXRate(
                base_currency=config.output_currency,
                quote_currency=config.output_currency,
                rate=1.0,
                source="identity",
                timestamp=timestamp
            )
        
        return rates, status
    
    return {}, f"Unknown FX mode: {config.mode}"


def convert_to_usd(value: Optional[float], fx_rate: Optional[FXRate]) -> Optional[float]:
    """
    Convert a value to USD using the provided FX rate.
    
    Args:
        value: Value in local currency
        fx_rate: FXRate object with conversion rate
    
    Returns:
        Value in USD, or None if conversion not possible
    """
    if value is None or fx_rate is None:
        return None
    
    return value * fx_rate.rate


def format_fx_rates_summary(rates: Dict[str, FXRate]) -> str:
    """Generate a human-readable summary of FX rates used."""
    lines = []
    for currency, rate in rates.items():
        if rate.rate == 1.0:
            continue
        lines.append(f"1 {currency} = {rate.rate:.6f} USD (Source: {rate.source})")
    return "\n".join(lines) if lines else "All values already in USD"
