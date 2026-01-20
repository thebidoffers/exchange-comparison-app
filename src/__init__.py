"""
Exchange Comparison App v2.0 - Source Module
With auto-fetch data capabilities
"""

from .data_fetcher import (
    fetch_all_indices,
    get_available_indices,
    create_comparison_df,
    update_market_caps,
    INDEX_CONFIGS,
    FX_RATES_TO_USD,
    IndexData,
)

from .insights import (
    generate_insights,
    generate_next_steps,
    generate_executive_summary,
)

__all__ = [
    'fetch_all_indices', 'get_available_indices',
    'create_comparison_df', 'update_market_caps',
    'INDEX_CONFIGS', 'FX_RATES_TO_USD', 'IndexData',
    'generate_insights', 'generate_next_steps', 'generate_executive_summary',
]
