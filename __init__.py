"""
Exchange Comparison App - Source Module
"""

from .schemas import (
    Currency,
    FXMode,
    DateRangePreset,
    ExchangeInput,
    ExchangeOutput,
    FXRate,
    DateRange,
    FXConfiguration,
    AuditRecord,
    ComparisonResult,
    DEFAULT_EXCHANGES,
    OPTIONAL_EXCHANGES,
    CURRENCY_SYMBOLS,
)

from .fx import (
    get_fx_rates,
    get_live_fx_rates,
    convert_to_usd,
    format_fx_rates_summary,
    calculate_average_fx_from_df,
)

from .compute import (
    compute_exchange_outputs,
    create_comparison_dataframe,
    create_raw_dataframe,
    create_audit_dataframe,
    get_rankings,
    export_to_json,
    format_market_cap,
    format_adtv,
    format_percent,
)

from .insights import (
    generate_insights,
    generate_next_steps,
    generate_executive_summary,
)

from .extraction import (
    try_extract_from_config,
    get_extraction_status,
    create_extraction_config_template,
    KNOWN_EXCHANGE_CONFIGS,
)

__all__ = [
    # Schemas
    'Currency', 'FXMode', 'DateRangePreset',
    'ExchangeInput', 'ExchangeOutput', 'FXRate',
    'DateRange', 'FXConfiguration', 'AuditRecord', 'ComparisonResult',
    'DEFAULT_EXCHANGES', 'OPTIONAL_EXCHANGES', 'CURRENCY_SYMBOLS',
    # FX
    'get_fx_rates', 'get_live_fx_rates', 'convert_to_usd',
    'format_fx_rates_summary', 'calculate_average_fx_from_df',
    # Compute
    'compute_exchange_outputs', 'create_comparison_dataframe',
    'create_raw_dataframe', 'create_audit_dataframe',
    'get_rankings', 'export_to_json',
    'format_market_cap', 'format_adtv', 'format_percent',
    # Insights
    'generate_insights', 'generate_next_steps', 'generate_executive_summary',
    # Extraction
    'try_extract_from_config', 'get_extraction_status',
    'create_extraction_config_template', 'KNOWN_EXCHANGE_CONFIGS',
]
