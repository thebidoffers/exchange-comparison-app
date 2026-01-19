"""
Deterministic insight generation module.
Generates executive-ready observations from computed data.
No LLM required - pure algorithmic analysis.
"""

from typing import List, Dict, Optional
from .schemas import ExchangeOutput
from .compute import format_market_cap, format_adtv, format_percent


def generate_insights(outputs: List[ExchangeOutput], year: int) -> List[str]:
    """
    Generate 4-6 key insights from the comparison data.
    
    Args:
        outputs: List of ExchangeOutput objects
        year: Year being analyzed
    
    Returns:
        List of insight strings (bullet points)
    """
    insights = []
    
    # Filter outputs with valid data for each metric
    ytd_valid = [o for o in outputs if o.ytd_percent is not None]
    cap_valid = [o for o in outputs if o.market_cap_usd is not None]
    adtv_valid = [o for o in outputs if o.adtv_usd is not None]
    
    # 1. YTD Performance Leader
    if ytd_valid:
        best_ytd = max(ytd_valid, key=lambda x: x.ytd_percent)
        worst_ytd = min(ytd_valid, key=lambda x: x.ytd_percent)
        
        if best_ytd.ytd_percent >= 0:
            insights.append(
                f"**{best_ytd.exchange}** leads in YTD performance at "
                f"{format_percent(best_ytd.ytd_percent)}, outperforming other exchanges in the comparison."
            )
        else:
            insights.append(
                f"All exchanges show negative YTD returns in {year}, with **{best_ytd.exchange}** "
                f"declining the least at {format_percent(best_ytd.ytd_percent)}."
            )
        
        # Performance spread insight
        if len(ytd_valid) >= 2:
            spread = best_ytd.ytd_percent - worst_ytd.ytd_percent
            if spread > 10:
                insights.append(
                    f"Significant performance dispersion observed: {spread:.1f} percentage points "
                    f"separate the best ({best_ytd.exchange}) from the weakest ({worst_ytd.exchange}) performer."
                )
    
    # 2. Market Cap Dominance
    if cap_valid:
        total_cap = sum(o.market_cap_usd for o in cap_valid if o.market_cap_usd)
        largest = max(cap_valid, key=lambda x: x.market_cap_usd)
        
        if total_cap > 0:
            largest_pct = (largest.market_cap_usd / total_cap) * 100
            insights.append(
                f"**{largest.exchange}** dominates by market capitalization at "
                f"{format_market_cap(largest.market_cap_usd)}, representing {largest_pct:.1f}% "
                f"of the combined market cap in this comparison."
            )
    
    # 3. Liquidity (ADTV) Analysis
    if adtv_valid:
        highest_adtv = max(adtv_valid, key=lambda x: x.adtv_usd)
        
        # Check liquidity relative to market cap
        if cap_valid and highest_adtv.market_cap_usd:
            turnover_pct = (highest_adtv.adtv_usd / highest_adtv.market_cap_usd) * 100 * 252  # Annualized
            insights.append(
                f"**{highest_adtv.exchange}** shows the highest liquidity with "
                f"{format_adtv(highest_adtv.adtv_usd)} average daily traded value"
                f"{f', implying ~{turnover_pct:.0f}% annualized turnover' if turnover_pct < 500 else ''}."
            )
        else:
            insights.append(
                f"**{highest_adtv.exchange}** leads in liquidity with "
                f"{format_adtv(highest_adtv.adtv_usd)} average daily traded value."
            )
    
    # 4. Divergence Analysis - High cap but weak performance
    if ytd_valid and cap_valid:
        # Find exchanges with above-median cap but below-median YTD
        median_cap = sorted([o.market_cap_usd for o in cap_valid])[len(cap_valid) // 2]
        median_ytd = sorted([o.ytd_percent for o in ytd_valid])[len(ytd_valid) // 2]
        
        divergent = [
            o for o in outputs
            if o.market_cap_usd is not None and o.ytd_percent is not None
            and o.market_cap_usd >= median_cap and o.ytd_percent < median_ytd
        ]
        
        if divergent:
            for d in divergent[:1]:  # Limit to one divergence insight
                insights.append(
                    f"Notable divergence: **{d.exchange}** has significant market cap "
                    f"({format_market_cap(d.market_cap_usd)}) but underperformed at "
                    f"{format_percent(d.ytd_percent)}, suggesting potential value or structural headwinds."
                )
    
    # 5. Small cap outperformer
    if ytd_valid and cap_valid and len(cap_valid) >= 3:
        # Find if any small cap exchange (bottom third) outperformed (top third YTD)
        cap_sorted = sorted(cap_valid, key=lambda x: x.market_cap_usd)
        ytd_sorted = sorted(ytd_valid, key=lambda x: x.ytd_percent, reverse=True)
        
        small_caps = set(o.exchange for o in cap_sorted[:len(cap_sorted)//3 + 1])
        top_performers = set(o.exchange for o in ytd_sorted[:len(ytd_sorted)//3 + 1])
        
        outperformers = small_caps & top_performers
        for exchange in list(outperformers)[:1]:
            ex_obj = next(o for o in outputs if o.exchange == exchange)
            insights.append(
                f"**{exchange}** demonstrates strong performance ({format_percent(ex_obj.ytd_percent)}) "
                f"despite its smaller market cap, indicating momentum in this market."
            )
    
    # 6. Regional observation
    regions = {}
    for o in outputs:
        if o.region not in regions:
            regions[o.region] = []
        regions[o.region].append(o)
    
    if len(regions) >= 2:
        # Compare regional averages
        regional_ytd = {}
        for region, exchanges in regions.items():
            valid = [e.ytd_percent for e in exchanges if e.ytd_percent is not None]
            if valid:
                regional_ytd[region] = sum(valid) / len(valid)
        
        if len(regional_ytd) >= 2:
            best_region = max(regional_ytd.items(), key=lambda x: x[1])
            if best_region[1] > 0:
                insights.append(
                    f"**{best_region[0]}** region shows the strongest average performance "
                    f"at {format_percent(best_region[1])} across its exchanges."
                )
    
    # Ensure we have at least 4 insights
    if len(insights) < 4:
        # Add currency note if relevant
        currencies = set(o.local_currency for o in outputs)
        if len(currencies) > 1:
            insights.append(
                f"Currency unification applied across {len(currencies)} currencies "
                f"({', '.join(sorted(currencies))}) to enable direct comparison."
            )
    
    # Add data quality note if there are missing values
    missing_count = sum(1 for o in outputs if o.ytd_percent is None or o.market_cap_usd is None)
    if missing_count > 0:
        insights.append(
            f"⚠️ Note: {missing_count} exchange(s) have incomplete data marked as N/A. "
            f"Insights are based on available data only."
        )
    
    return insights[:6]  # Return max 6 insights


def generate_next_steps() -> List[str]:
    """
    Generate standard next steps for the analysis.
    
    Returns:
        List of next step recommendations
    """
    return [
        "**Create a global bar chart** comparing YTD performance and market cap visually across all exchanges.",
        "**Add sector-wise breakdown** for leading sectors in each region to identify key drivers.",
        "**Highlight top 3 companies** by market cap in each exchange to show index composition.",
    ]


def generate_executive_summary(
    outputs: List[ExchangeOutput],
    year: int,
    date_range_str: str
) -> str:
    """
    Generate an executive summary paragraph.
    
    Args:
        outputs: List of ExchangeOutput objects
        year: Year being analyzed
        date_range_str: Human-readable date range
    
    Returns:
        Summary paragraph
    """
    ytd_valid = [o for o in outputs if o.ytd_percent is not None]
    cap_valid = [o for o in outputs if o.market_cap_usd is not None]
    
    exchange_count = len(outputs)
    region_count = len(set(o.region for o in outputs))
    
    summary_parts = [
        f"This analysis compares {exchange_count} stock exchanges across {region_count} regions "
        f"for {date_range_str}."
    ]
    
    if ytd_valid:
        avg_ytd = sum(o.ytd_percent for o in ytd_valid) / len(ytd_valid)
        positive_count = sum(1 for o in ytd_valid if o.ytd_percent > 0)
        summary_parts.append(
            f"Average YTD performance is {format_percent(avg_ytd)}, "
            f"with {positive_count} of {len(ytd_valid)} exchanges showing positive returns."
        )
    
    if cap_valid:
        total_cap = sum(o.market_cap_usd for o in cap_valid)
        summary_parts.append(
            f"Combined market capitalization totals {format_market_cap(total_cap)}."
        )
    
    return " ".join(summary_parts)
