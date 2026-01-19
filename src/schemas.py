"""
Pydantic schemas and dataclasses for Exchange Comparison App.
Ensures type safety and validation for all data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    AED = "AED"
    SAR = "SAR"
    KWD = "KWD"
    QAR = "QAR"
    GBP = "GBP"
    EUR = "EUR"
    JPY = "JPY"
    HKD = "HKD"


class FXMode(str, Enum):
    """FX rate retrieval modes."""
    LIVE_SPOT = "live_spot"
    MANUAL = "manual"
    AVERAGE = "average"


class DateRangePreset(str, Enum):
    """Date range preset options."""
    YTD = "ytd"
    FULL_YEAR = "full_year"
    CUSTOM = "custom"


class ExchangeInput(BaseModel):
    """Input model for a single exchange entry."""
    region: str = Field(..., description="Geographic region (e.g., UAE, Saudi Arabia)")
    exchange: str = Field(..., description="Exchange name (e.g., DFM, ADX, Tadawul)")
    index_name: str = Field(..., description="Main index name (e.g., DFM General Index)")
    local_currency: Currency = Field(..., description="Local currency code")
    ytd_percent: Optional[float] = Field(None, description="Year-to-date percentage change")
    market_cap_local: Optional[float] = Field(None, ge=0, description="Market cap in local currency")
    adtv_local: Optional[float] = Field(None, ge=0, description="Avg daily traded value in local currency")
    source: str = Field(default="manual", description="Data source identifier")
    source_url: Optional[str] = Field(None, description="URL if data was fetched from web")
    source_timestamp: Optional[datetime] = Field(None, description="When data was retrieved")

    class Config:
        use_enum_values = True


class FXRate(BaseModel):
    """Model for a single FX rate."""
    base_currency: Currency
    quote_currency: Currency = Currency.USD
    rate: float = Field(..., gt=0, description="Exchange rate (base/quote)")
    source: str = Field(..., description="Source of FX rate")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class ExchangeOutput(BaseModel):
    """Output model with USD-converted values."""
    region: str
    exchange: str
    index_name: str
    local_currency: str
    ytd_percent: Optional[float] = None
    ytd_percent_display: str = "N/A"
    market_cap_local: Optional[float] = None
    market_cap_usd: Optional[float] = None
    market_cap_usd_display: str = "N/A"
    adtv_local: Optional[float] = None
    adtv_usd: Optional[float] = None
    adtv_usd_display: str = "N/A"
    fx_rate_used: Optional[float] = None
    source: str = "manual"
    source_url: Optional[str] = None
    source_timestamp: Optional[datetime] = None

    class Config:
        use_enum_values = True


@dataclass
class DateRange:
    """Date range configuration."""
    start_date: date
    end_date: date
    preset: DateRangePreset = DateRangePreset.YTD
    year: int = field(default_factory=lambda: datetime.now().year)

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError("Start date must be before or equal to end date")


@dataclass
class FXConfiguration:
    """FX conversion configuration."""
    mode: FXMode
    output_currency: Currency = Currency.USD
    manual_rates: dict = field(default_factory=dict)  # e.g., {"AED": 0.2723, "SAR": 0.2667}
    average_fx_data: Optional[dict] = None  # DataFrame stored as dict
    live_fx_source: str = "exchangerate.host"


@dataclass
class AuditRecord:
    """Audit trail for a single exchange computation."""
    exchange: str
    input_local_currency: str
    input_market_cap: Optional[float]
    input_adtv: Optional[float]
    input_ytd_percent: Optional[float]
    fx_rate: Optional[float]
    fx_source: str
    output_market_cap_usd: Optional[float]
    output_adtv_usd: Optional[float]
    computed_at: datetime = field(default_factory=datetime.utcnow)
    missing_fields: list = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Complete comparison result with audit trail."""
    date_range: DateRange
    fx_config: FXConfiguration
    exchanges: list  # List of ExchangeOutput
    audit_records: list  # List of AuditRecord
    insights: list  # List of insight strings
    generated_at: datetime = field(default_factory=datetime.utcnow)


# Default exchange configurations
DEFAULT_EXCHANGES = [
    {
        "region": "UAE",
        "exchange": "DFM",
        "index_name": "DFM General Index",
        "local_currency": "AED",
    },
    {
        "region": "UAE",
        "exchange": "ADX",
        "index_name": "ADX General Index",
        "local_currency": "AED",
    },
    {
        "region": "Saudi Arabia",
        "exchange": "Tadawul",
        "index_name": "TASI",
        "local_currency": "SAR",
    },
]

OPTIONAL_EXCHANGES = [
    {
        "region": "Kuwait",
        "exchange": "Boursa Kuwait",
        "index_name": "Premier Market Index",
        "local_currency": "KWD",
    },
    {
        "region": "Qatar",
        "exchange": "QSE",
        "index_name": "QE Index",
        "local_currency": "QAR",
    },
    {
        "region": "USA",
        "exchange": "NYSE",
        "index_name": "NYSE Composite",
        "local_currency": "USD",
    },
    {
        "region": "USA",
        "exchange": "NASDAQ",
        "index_name": "NASDAQ Composite",
        "local_currency": "USD",
    },
    {
        "region": "UK",
        "exchange": "LSE",
        "index_name": "FTSE 100",
        "local_currency": "GBP",
    },
    {
        "region": "Germany",
        "exchange": "XETRA",
        "index_name": "DAX",
        "local_currency": "EUR",
    },
    {
        "region": "France",
        "exchange": "Euronext Paris",
        "index_name": "CAC 40",
        "local_currency": "EUR",
    },
    {
        "region": "Japan",
        "exchange": "TSE",
        "index_name": "Nikkei 225",
        "local_currency": "JPY",
    },
    {
        "region": "Hong Kong",
        "exchange": "HKEX",
        "index_name": "Hang Seng",
        "local_currency": "HKD",
    },
]

# Currency symbols for display
CURRENCY_SYMBOLS = {
    "USD": "$",
    "AED": "AED ",
    "SAR": "SAR ",
    "KWD": "KWD ",
    "QAR": "QAR ",
    "GBP": "£",
    "EUR": "€",
    "JPY": "¥",
    "HKD": "HK$",
}
