"""
Computation module for exchange metrics conversion and comparison.
All calculations are deterministic using pandas.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .schemas import (
    ExchangeInput, ExchangeOutput, FXConfiguration, FXRate,
    DateRange, AuditRecord, ComparisonResult, CURRENCY_SYMBOLS
)
from .fx import get_fx_rates, convert_to_usd


def format_market_cap(value: Optional[float], currency_symbol: str = "$") -> str:
    """
    Format market cap in human-readable form (billions/trillions).
    
    Args:
        value: Market cap value
        currency_symbol: Currency symbol to prepend
    
    Returns:
        Formatted string like "$1.5T" or "$234.5B"
    """
    if value is None:
        return "N/A"
    
    if value >= 1e12:
        return f"{currency_symbol}{value/1e12:.2f}T"
    elif value >= 1e9:
        return f"{currency_symbol}{value/1e9:.2f}B"
    elif value >= 1e6:
        return f"{currency_symbol}{value/1e6:.2f}M"
    else:
        return f"{currency_symbol}{value:,.0f}"


def format_adtv(value: Optional[float], currency_symbol: str = "$") -> str:
    """
    Format average daily traded value in human-readable form.
    
    Args:
        value: ADTV value
        currency_symbol: Currency symbol to prepend
    
    Returns:
        Formatted string like "$1.5B" or "$234.5M"
    """
    if value is None:
        return "N/A"
    
    if value >= 1e9:
        return f"{currency_symbol}{value/1e9:.2f}B"
    elif value >= 1e6:
        return f"{currency_symbol}{value/1e6:.2f}M"
    elif value >= 1e3:
        return f"{currency_symbol}{value/1e3:.2f}K"
    else:
        return f"{currency_symbol}{value:,.0f}"


def format_percent(value: Optional[float]) -> str:
    """
    Format percentage with sign.
    
    Args:
        value: Percentage value (e.g., 5.23 for 5.23%)
    
    Returns:
        Formatted string like "+5.23%" or "-2.10%"
    """
    if value is None:
        return "N/A"
    
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def compute_exchange_outputs(
    inputs: List[ExchangeInput],
    fx_config: FXConfiguration,
    date_range: DateRange
) -> Tuple[List[ExchangeOutput], List[AuditRecord], Dict[str, FXRate], str]:
    """
    Convert exchange inputs to USD-denominated outputs.
    
    Args:
        inputs: List of exchange input data
        fx_config: FX configuration for conversion
        date_range: Date range for the comparison
    
    Returns:
        Tuple of (outputs, audit_records, fx_rates_used, status_message)
    """
    # Get required currencies
    required_currencies = list(set(
        inp.local_currency if isinstance(inp.local_currency, str) else inp.local_currency.value
        for inp in inputs
    ))
    
    # Fetch FX rates
    fx_rates, fx_status = get_fx_rates(
        fx_config,
        required_currencies,
        (date_range.start_date, date_range.end_date)
    )
    
    outputs = []
    audit_records = []
    
    for inp in inputs:
        currency = inp.local_currency if isinstance(inp.local_currency, str) else inp.local_currency.value
        fx_rate = fx_rates.get(currency)
        
        # Calculate USD values
        market_cap_usd = convert_to_usd(inp.market_cap_local, fx_rate)
        adtv_usd = convert_to_usd(inp.adtv_local, fx_rate)
        
        # Track missing fields
        missing_fields = []
        if inp.ytd_percent is None:
            missing_fields.append("ytd_percent")
        if inp.market_cap_local is None:
            missing_fields.append("market_cap")
        if inp.adtv_local is None:
            missing_fields.append("adtv")
        if fx_rate is None and currency != "USD":
            missing_fields.append(f"fx_rate_{currency}")
        
        # Create output
        output = ExchangeOutput(
            region=inp.region,
            exchange=inp.exchange,
            index_name=inp.index_name,
            local_currency=currency,
            ytd_percent=inp.ytd_percent,
            ytd_percent_display=format_percent(inp.ytd_percent),
            market_cap_local=inp.market_cap_local,
            market_cap_usd=market_cap_usd,
            market_cap_usd_display=format_market_cap(market_cap_usd),
            adtv_local=inp.adtv_local,
            adtv_usd=adtv_usd,
            adtv_usd_display=format_adtv(adtv_usd),
            fx_rate_used=fx_rate.rate if fx_rate else None,
            source=inp.source,
            source_url=inp.source_url,
            source_timestamp=inp.source_timestamp or datetime.utcnow()
        )
        outputs.append(output)
        
        # Create audit record
        audit = AuditRecord(
            exchange=inp.exchange,
            input_local_currency=currency,
            input_market_cap=inp.market_cap_local,
            input_adtv=inp.adtv_local,
            input_ytd_percent=inp.ytd_percent,
            fx_rate=fx_rate.rate if fx_rate else None,
            fx_source=fx_rate.source if fx_rate else "N/A",
            output_market_cap_usd=market_cap_usd,
            output_adtv_usd=adtv_usd,
            missing_fields=missing_fields
        )
        audit_records.append(audit)
    
    return outputs, audit_records, fx_rates, fx_status


def create_comparison_dataframe(outputs: List[ExchangeOutput]) -> pd.DataFrame:
    """
    Create a formatted DataFrame for display.
    
    Args:
        outputs: List of ExchangeOutput objects
    
    Returns:
        DataFrame ready for display
    """
    data = []
    for out in outputs:
        data.append({
            "Region": out.region,
            "Exchange": out.exchange,
            "Index Name": out.index_name,
            "YTD % Change": out.ytd_percent_display,
            "Market Cap (USD)": out.market_cap_usd_display,
            "Avg Daily Value (USD)": out.adtv_usd_display,
        })
    
    return pd.DataFrame(data)


def create_raw_dataframe(outputs: List[ExchangeOutput]) -> pd.DataFrame:
    """
    Create a DataFrame with raw numeric values for export.
    
    Args:
        outputs: List of ExchangeOutput objects
    
    Returns:
        DataFrame with numeric values
    """
    data = []
    for out in outputs:
        data.append({
            "region": out.region,
            "exchange": out.exchange,
            "index_name": out.index_name,
            "local_currency": out.local_currency,
            "ytd_percent": out.ytd_percent,
            "market_cap_local": out.market_cap_local,
            "market_cap_usd": out.market_cap_usd,
            "adtv_local": out.adtv_local,
            "adtv_usd": out.adtv_usd,
            "fx_rate_used": out.fx_rate_used,
            "source": out.source,
        })
    
    return pd.DataFrame(data)


def create_audit_dataframe(audit_records: List[AuditRecord]) -> pd.DataFrame:
    """
    Create a DataFrame showing the audit trail.
    
    Args:
        audit_records: List of AuditRecord objects
    
    Returns:
        DataFrame showing computation details
    """
    data = []
    for record in audit_records:
        data.append({
            "Exchange": record.exchange,
            "Input Currency": record.input_local_currency,
            "Input Market Cap": record.input_market_cap,
            "Input ADTV": record.input_adtv,
            "Input YTD %": record.input_ytd_percent,
            "FX Rate": record.fx_rate,
            "FX Source": record.fx_source,
            "Output Market Cap (USD)": record.output_market_cap_usd,
            "Output ADTV (USD)": record.output_adtv_usd,
            "Computed At": record.computed_at.isoformat(),
            "Missing Fields": ", ".join(record.missing_fields) if record.missing_fields else "None",
        })
    
    return pd.DataFrame(data)


def get_rankings(outputs: List[ExchangeOutput]) -> Dict:
    """
    Calculate various rankings from the outputs.
    
    Args:
        outputs: List of ExchangeOutput objects
    
    Returns:
        Dictionary containing various rankings
    """
    # Filter out entries with missing data for each metric
    ytd_valid = [(o.exchange, o.ytd_percent) for o in outputs if o.ytd_percent is not None]
    cap_valid = [(o.exchange, o.market_cap_usd) for o in outputs if o.market_cap_usd is not None]
    adtv_valid = [(o.exchange, o.adtv_usd) for o in outputs if o.adtv_usd is not None]
    
    rankings = {
        "ytd_best": sorted(ytd_valid, key=lambda x: x[1], reverse=True) if ytd_valid else [],
        "ytd_worst": sorted(ytd_valid, key=lambda x: x[1]) if ytd_valid else [],
        "market_cap_largest": sorted(cap_valid, key=lambda x: x[1], reverse=True) if cap_valid else [],
        "adtv_highest": sorted(adtv_valid, key=lambda x: x[1], reverse=True) if adtv_valid else [],
    }
    
    return rankings


def export_to_json(
    outputs: List[ExchangeOutput],
    audit_records: List[AuditRecord],
    fx_rates: Dict[str, FXRate],
    date_range: DateRange,
    fx_config: FXConfiguration
) -> dict:
    """
    Create a JSON-serializable export of all data.
    
    Args:
        outputs: List of ExchangeOutput objects
        audit_records: List of AuditRecord objects
        fx_rates: Dictionary of FX rates used
        date_range: Date range configuration
        fx_config: FX configuration
    
    Returns:
        Dictionary ready for JSON serialization
    """
    return {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "date_range": {
                "start": date_range.start_date.isoformat(),
                "end": date_range.end_date.isoformat(),
                "preset": date_range.preset.value if hasattr(date_range.preset, 'value') else str(date_range.preset),
                "year": date_range.year,
            },
            "fx_mode": fx_config.mode.value if hasattr(fx_config.mode, 'value') else str(fx_config.mode),
            "output_currency": str(fx_config.output_currency),
        },
        "fx_rates": {
            currency: {
                "rate": rate.rate,
                "source": rate.source,
                "timestamp": rate.timestamp.isoformat(),
            }
            for currency, rate in fx_rates.items()
        },
        "exchanges": [
            {
                "region": o.region,
                "exchange": o.exchange,
                "index_name": o.index_name,
                "local_currency": o.local_currency,
                "ytd_percent": o.ytd_percent,
                "market_cap_local": o.market_cap_local,
                "market_cap_usd": o.market_cap_usd,
                "adtv_local": o.adtv_local,
                "adtv_usd": o.adtv_usd,
                "fx_rate_used": o.fx_rate_used,
                "source": o.source,
            }
            for o in outputs
        ],
        "audit_trail": [
            {
                "exchange": a.exchange,
                "input_currency": a.input_local_currency,
                "input_market_cap": a.input_market_cap,
                "input_adtv": a.input_adtv,
                "fx_rate": a.fx_rate,
                "fx_source": a.fx_source,
                "output_market_cap_usd": a.output_market_cap_usd,
                "output_adtv_usd": a.output_adtv_usd,
                "computed_at": a.computed_at.isoformat(),
                "missing_fields": a.missing_fields,
            }
            for a in audit_records
        ],
    }
