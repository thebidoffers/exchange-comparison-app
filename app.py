"""
Exchange Comparison App v2.0 - With Auto-Fetch Data
A production-ready web app for comparing stock exchanges with automatic data retrieval.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import json
import sys
sys.path.insert(0, '.')

from src.data_fetcher import (
    fetch_all_indices, 
    get_available_indices, 
    create_comparison_df,
    update_market_caps,
    INDEX_CONFIGS,
    FX_RATES_TO_USD
)
from src.insights import generate_insights, generate_next_steps

# Page configuration
st.set_page_config(
    page_title="Exchange Comparison Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark professional theme
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    h1, h2, h3 { color: #ffffff !important; font-weight: 600; }
    .section-title {
        color: #ffffff;
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #3b82f6;
    }
    .insight-item {
        background-color: #1e2530;
        border-left: 3px solid #3b82f6;
        padding: 12px 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
    .next-step {
        background-color: #1a2332;
        border-left: 3px solid #10b981;
        padding: 12px 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
    .info-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #064e3b;
        border: 1px solid #10b981;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #422006;
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        border: 1px solid #334155;
    }
    .positive { color: #10b981; font-weight: bold; }
    .negative { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'fetched_data' not in st.session_state:
        st.session_state.fetched_data = None
    if 'fetch_status' not in st.session_state:
        st.session_state.fetch_status = None
    if 'manual_market_caps' not in st.session_state:
        st.session_state.manual_market_caps = {}


def render_sidebar():
    """Render sidebar with configuration options."""
    st.sidebar.title("⚙️ Configuration")
    
    # Year Selection
    st.sidebar.markdown("### 📅 Analysis Period")
    current_year = datetime.now().year
    year = st.sidebar.selectbox(
        "Year",
        options=list(range(current_year, current_year - 5, -1)),
        index=0,
        help="Select year for YTD calculation"
    )
    
    st.sidebar.markdown("---")
    
    # Exchange Selection
    st.sidebar.markdown("### 🏛️ Select Exchanges")
    
    available = get_available_indices()
    
    # Group by region
    gcc_indices = [i for i in available if i["region"] == "Middle East"]
    us_indices = [i for i in available if i["region"] == "USA"]
    eu_indices = [i for i in available if i["region"] == "Europe"]
    asia_indices = [i for i in available if i["region"] == "Asia"]
    
    st.sidebar.markdown("**GCC Markets**")
    gcc_selected = []
    for idx in gcc_indices:
        if st.sidebar.checkbox(f"{idx['exchange']}", value=True, key=f"gcc_{idx['key']}"):
            gcc_selected.append(idx['key'])
    
    st.sidebar.markdown("**US Markets**")
    us_selected = []
    for idx in us_indices:
        if st.sidebar.checkbox(f"{idx['exchange']}", value=True, key=f"us_{idx['key']}"):
            us_selected.append(idx['key'])
    
    st.sidebar.markdown("**European Markets**")
    eu_selected = []
    for idx in eu_indices:
        if st.sidebar.checkbox(f"{idx['exchange']}", value=False, key=f"eu_{idx['key']}"):
            eu_selected.append(idx['key'])
    
    st.sidebar.markdown("**Asian Markets**")
    asia_selected = []
    for idx in asia_indices:
        if st.sidebar.checkbox(f"{idx['exchange']}", value=False, key=f"asia_{idx['key']}"):
            asia_selected.append(idx['key'])
    
    selected_indices = gcc_selected + us_selected + eu_selected + asia_selected
    
    st.sidebar.markdown("---")
    
    # Market Cap Override Section
    st.sidebar.markdown("### 💰 Market Cap Override")
    st.sidebar.caption("Override estimated market caps (in USD billions)")
    
    show_overrides = st.sidebar.checkbox("Show market cap inputs", value=False)
    manual_caps = {}
    
    if show_overrides:
        for key in selected_indices:
            config = INDEX_CONFIGS.get(key, {})
            default_cap = config.get("estimated_market_cap_usd", 0) / 1e9  # Convert to billions
            cap_input = st.sidebar.number_input(
                f"{key} Market Cap ($B)",
                value=default_cap,
                min_value=0.0,
                step=10.0,
                key=f"cap_{key}"
            )
            if cap_input > 0:
                manual_caps[key] = cap_input * 1e9  # Convert back to raw number
    
    st.sidebar.markdown("---")
    
    # Data Source Info
    st.sidebar.markdown("### 📡 Data Source")
    st.sidebar.info("""
    **Primary:** Yahoo Finance API
    - YTD % Change: ✅ Live
    - Market Cap: 📊 Estimates (can override)
    - ADTV: 📊 Calculated from volume
    """)
    
    return year, selected_indices, manual_caps


def render_fetch_section(year: int, selected_indices: list, manual_caps: dict):
    """Render the data fetch section."""
    
    st.markdown("### 🔄 Fetch Live Data")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"""
        **Selected:** {len(selected_indices)} exchanges for **{year}** YTD analysis
        """)
    
    with col2:
        fetch_clicked = st.button("🚀 Fetch Data", type="primary", use_container_width=True)
    
    with col3:
        if st.session_state.fetched_data:
            st.success("✅ Data loaded")
    
    if fetch_clicked:
        if not selected_indices:
            st.error("Please select at least one exchange from the sidebar.")
            return
        
        with st.spinner(f"Fetching data for {len(selected_indices)} exchanges..."):
            results, status = fetch_all_indices(selected_indices, year)
            
            # Apply manual market cap overrides
            if manual_caps:
                results = update_market_caps(results, manual_caps)
            
            st.session_state.fetched_data = results
            st.session_state.fetch_status = status
        
        # Show fetch results
        success_count = len(status.get("success", []))
        failed_count = len(status.get("failed", []))
        
        if failed_count == 0:
            st.success(f"✅ Successfully fetched data for all {success_count} exchanges!")
        else:
            st.warning(f"⚠️ Fetched {success_count} exchanges. {failed_count} failed.")
            for fail in status.get("failed", []):
                st.caption(f"❌ {fail['index']}: {fail['error']}")


def render_comparison_table(results: list, year: int):
    """Render the main comparison table."""
    
    # Title
    exchanges_str = ", ".join([r["exchange"] for r in results[:3]])
    if len(results) > 3:
        exchanges_str += f" + {len(results) - 3} more"
    
    st.markdown(f"""
    <div class="section-title">
        📊 {exchanges_str} — {year} YTD Overview (All in USD)
    </div>
    """, unsafe_allow_html=True)
    
    # Show last updated
    if results:
        st.caption(f"🕐 Data fetched: {results[0].get('last_updated', 'N/A')}")
    
    # Create display dataframe
    df = create_comparison_df(results)
    
    # Display columns (hide raw columns)
    display_cols = ["Region", "Exchange", "Index Name", "YTD % Change", "Market Cap (USD)", "Avg Daily Value (USD)"]
    
    # Apply styling based on YTD performance
    def highlight_ytd(val):
        if "+" in str(val):
            return "color: #10b981; font-weight: bold"
        elif "-" in str(val):
            return "color: #ef4444; font-weight: bold"
        return ""
    
    st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    return df


def render_insights_section(results: list, year: int):
    """Render insights section."""
    
    st.markdown("""
    <div class="section-title">
        🔍 Key Observations After Currency Unification
    </div>
    """, unsafe_allow_html=True)
    
    # Convert results to format expected by insights generator
    class MockOutput:
        def __init__(self, data):
            self.region = data.get("region")
            self.exchange = data.get("exchange")
            self.index_name = data.get("index_name")
            self.ytd_percent = data.get("ytd_percent")
            self.market_cap_usd = data.get("market_cap_usd")
            self.adtv_usd = data.get("adtv_usd")
    
    mock_outputs = [MockOutput(r) for r in results]
    insights = generate_insights(mock_outputs, year)
    
    for insight in insights:
        st.markdown(f"""
        <div class="insight-item">
            • {insight}
        </div>
        """, unsafe_allow_html=True)


def render_next_steps_section():
    """Render next steps section."""
    
    st.markdown("""
    <div class="section-title">
        📋 Next Steps
    </div>
    """, unsafe_allow_html=True)
    
    next_steps = generate_next_steps()
    
    for i, step in enumerate(next_steps, 1):
        st.markdown(f"""
        <div class="next-step">
            {i}. {step}
        </div>
        """, unsafe_allow_html=True)


def render_charts(results: list):
    """Render visualization charts."""
    
    st.markdown("""
    <div class="section-title">
        📈 Visual Comparison
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["YTD Performance", "Market Cap", "Daily Volume"])
    
    with tab1:
        # YTD Performance Bar Chart
        ytd_data = [
            {"Exchange": r["exchange"], "YTD %": r["ytd_percent"]}
            for r in results if r.get("ytd_percent") is not None
        ]
        
        if ytd_data:
            df = pd.DataFrame(ytd_data).sort_values("YTD %", ascending=True)
            colors = ['#10b981' if x >= 0 else '#ef4444' for x in df['YTD %']]
            
            fig = go.Figure(data=[
                go.Bar(
                    y=df['Exchange'],
                    x=df['YTD %'],
                    orientation='h',
                    marker_color=colors,
                    text=[f"{x:+.2f}%" for x in df['YTD %']],
                    textposition='outside'
                )
            ])
            fig.update_layout(
                title=f"YTD Performance Comparison",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                xaxis_title="YTD % Change",
                yaxis_title="",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No YTD performance data available")
    
    with tab2:
        # Market Cap Bar Chart
        cap_data = [
            {"Exchange": r["exchange"], "Market Cap ($B)": r["market_cap_usd"] / 1e9}
            for r in results if r.get("market_cap_usd")
        ]
        
        if cap_data:
            df = pd.DataFrame(cap_data).sort_values("Market Cap ($B)", ascending=True)
            
            fig = px.bar(
                df, y="Exchange", x="Market Cap ($B)",
                orientation='h',
                title="Market Capitalization Comparison (USD Billions)",
                color="Market Cap ($B)",
                color_continuous_scale="Blues"
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                showlegend=False,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No market cap data available")
    
    with tab3:
        # ADTV Bar Chart
        adtv_data = [
            {"Exchange": r["exchange"], "ADTV ($M)": r["adtv_usd"] / 1e6}
            for r in results if r.get("adtv_usd")
        ]
        
        if adtv_data:
            df = pd.DataFrame(adtv_data).sort_values("ADTV ($M)", ascending=True)
            
            fig = px.bar(
                df, y="Exchange", x="ADTV ($M)",
                orientation='h',
                title="Average Daily Traded Value (USD Millions)",
                color="ADTV ($M)",
                color_continuous_scale="Greens"
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                showlegend=False,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No ADTV data available")


def render_data_source_info(results: list, status: dict):
    """Render data source and audit information."""
    
    with st.expander("🔎 Data Sources & Audit Trail", expanded=False):
        st.markdown("### Data Sources")
        
        source_df = pd.DataFrame([
            {
                "Exchange": r["exchange"],
                "Source": r.get("data_source", "N/A"),
                "Status": "✅ Success" if r.get("fetch_status") == "success" else "⚠️ Partial/Failed",
                "Last Updated": r.get("last_updated", "N/A"),
            }
            for r in results
        ])
        st.dataframe(source_df, use_container_width=True, hide_index=True)
        
        st.markdown("### FX Rates Used (to USD)")
        fx_df = pd.DataFrame([
            {"Currency": curr, "Rate to USD": rate}
            for curr, rate in FX_RATES_TO_USD.items()
        ])
        st.dataframe(fx_df, use_container_width=True, hide_index=True)
        
        if status:
            st.markdown("### Fetch Status")
            st.json(status)


def render_downloads(results: list, year: int):
    """Render download buttons."""
    
    st.markdown("### 📥 Download Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # CSV Download
        df = create_comparison_df(results)
        csv_data = df.to_csv(index=False)
        st.download_button(
            "⬇️ Download CSV",
            csv_data,
            f"exchange_comparison_{year}.csv",
            "text/csv",
            use_container_width=True
        )
    
    with col2:
        # JSON Download
        json_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "year": year,
                "fx_rates": FX_RATES_TO_USD,
            },
            "exchanges": results
        }
        json_str = json.dumps(json_data, indent=2, default=str)
        st.download_button(
            "⬇️ Download JSON",
            json_str,
            f"exchange_comparison_{year}.json",
            "application/json",
            use_container_width=True
        )


def main():
    """Main application entry point."""
    init_session_state()
    
    # Header
    st.title("📊 Exchange Comparison Dashboard")
    st.markdown("*Compare DFM, ADX, Tadawul and global exchanges — with live data from Yahoo Finance*")
    
    # Sidebar
    year, selected_indices, manual_caps = render_sidebar()
    
    # Main content
    st.markdown("---")
    
    # Fetch Section
    render_fetch_section(year, selected_indices, manual_caps)
    
    # Results Section
    if st.session_state.fetched_data:
        results = st.session_state.fetched_data
        status = st.session_state.fetch_status
        
        st.markdown("---")
        
        # Main Table
        df = render_comparison_table(results, year)
        
        st.markdown("---")
        
        # Insights and Next Steps
        col1, col2 = st.columns([3, 2])
        
        with col1:
            render_insights_section(results, year)
        
        with col2:
            render_next_steps_section()
        
        st.markdown("---")
        
        # Charts
        render_charts(results)
        
        st.markdown("---")
        
        # Data Sources
        render_data_source_info(results, status)
        
        st.markdown("---")
        
        # Downloads
        render_downloads(results, year)
    
    else:
        # Show instructions if no data yet
        st.markdown("""
        <div class="info-box">
            <h4>👆 Get Started</h4>
            <ol>
                <li>Select exchanges from the sidebar</li>
                <li>Click <strong>"🚀 Fetch Data"</strong> to retrieve live YTD performance</li>
                <li>View comparison table, insights, and charts</li>
                <li>Download results as CSV or JSON</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #64748b; font-size: 0.8rem;">
        Exchange Comparison Dashboard v2.0 | Data from Yahoo Finance | 
        Market caps are estimates — verify against official sources
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
