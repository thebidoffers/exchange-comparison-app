"""
Exchange Comparison App - Main Streamlit Application

A production-ready web app for comparing stock exchanges (DFM, ADX, Tadawul, and global)
on liquidity and performance metrics, with USD currency unification.

Author: Senior Full-Stack Engineer
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import json
import io

# Import our modules
import sys
sys.path.insert(0, '.')
from src.schemas import (
    Currency, FXMode, DateRangePreset,
    ExchangeInput, DateRange, FXConfiguration,
    DEFAULT_EXCHANGES, OPTIONAL_EXCHANGES, CURRENCY_SYMBOLS
)
from src.fx import get_fx_rates, format_fx_rates_summary
from src.compute import (
    compute_exchange_outputs, create_comparison_dataframe,
    create_raw_dataframe, create_audit_dataframe,
    export_to_json, format_market_cap, format_adtv
)
from src.insights import generate_insights, generate_next_steps, generate_executive_summary
from src.extraction import get_extraction_status

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
    /* Main background and text */
    .main {
        background-color: #0e1117;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 600;
    }
    
    /* Comparison table styling */
    .comparison-table {
        background-color: #1a1f29;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
    }
    
    /* Section headers */
    .section-title {
        color: #ffffff;
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #3b82f6;
    }
    
    /* Insight bullets */
    .insight-item {
        background-color: #1e2530;
        border-left: 3px solid #3b82f6;
        padding: 12px 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
    
    /* Next steps */
    .next-step {
        background-color: #1a2332;
        border-left: 3px solid #10b981;
        padding: 12px 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
    
    /* Info boxes */
    .info-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    
    /* Positive/negative values */
    .positive {
        color: #10b981;
    }
    .negative {
        color: #ef4444;
    }
    
    /* Download buttons */
    .stDownloadButton > button {
        background-color: #3b82f6;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
    }
    
    /* Dataframe styling */
    .dataframe {
        font-size: 14px;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #1a1f29;
    }
    
    /* Warning box */
    .warning-box {
        background-color: #422006;
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        border: 1px solid #334155;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #3b82f6;
    }
    .metric-label {
        color: #94a3b8;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'exchange_data' not in st.session_state:
        st.session_state.exchange_data = []
    if 'computed_results' not in st.session_state:
        st.session_state.computed_results = None
    if 'fx_rates' not in st.session_state:
        st.session_state.fx_rates = {}


def create_date_range(preset: str, year: int, custom_start: date = None, custom_end: date = None) -> DateRange:
    """Create a DateRange object from user inputs."""
    if preset == "YTD":
        start = date(year, 1, 1)
        end = date.today()
        return DateRange(start_date=start, end_date=end, preset=DateRangePreset.YTD, year=year)
    elif preset == "Full Year":
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        return DateRange(start_date=start, end_date=end, preset=DateRangePreset.FULL_YEAR, year=year)
    else:  # Custom
        return DateRange(start_date=custom_start, end_date=custom_end, preset=DateRangePreset.CUSTOM, year=year)


def render_sidebar():
    """Render the sidebar with all input controls."""
    st.sidebar.title("⚙️ Configuration")
    
    # Date Range Section
    st.sidebar.markdown("### 📅 Date Range")
    
    current_year = datetime.now().year
    year = st.sidebar.selectbox(
        "Year",
        options=list(range(current_year, current_year - 10, -1)),
        index=0
    )
    
    date_preset = st.sidebar.radio(
        "Range Type",
        options=["YTD", "Full Year", "Custom"],
        index=0
    )
    
    custom_start = custom_end = None
    if date_preset == "Custom":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            custom_start = st.date_input("Start Date", date(year, 1, 1))
        with col2:
            custom_end = st.date_input("End Date", date.today())
    
    date_range = create_date_range(date_preset, year, custom_start, custom_end)
    
    st.sidebar.markdown("---")
    
    # Exchange Selection
    st.sidebar.markdown("### 🏛️ Exchanges")
    
    # Default exchanges (always shown)
    default_selected = st.sidebar.multiselect(
        "Primary Exchanges (GCC)",
        options=[f"{e['exchange']} ({e['region']})" for e in DEFAULT_EXCHANGES],
        default=[f"{e['exchange']} ({e['region']})" for e in DEFAULT_EXCHANGES]
    )
    
    # Optional exchanges
    optional_selected = st.sidebar.multiselect(
        "Additional Exchanges (Global)",
        options=[f"{e['exchange']} ({e['region']})" for e in OPTIONAL_EXCHANGES],
        default=[]
    )
    
    # Parse selected exchanges
    selected_exchanges = []
    for sel in default_selected:
        exchange_name = sel.split(" (")[0]
        for e in DEFAULT_EXCHANGES:
            if e['exchange'] == exchange_name:
                selected_exchanges.append(e)
                break
    
    for sel in optional_selected:
        exchange_name = sel.split(" (")[0]
        for e in OPTIONAL_EXCHANGES:
            if e['exchange'] == exchange_name:
                selected_exchanges.append(e)
                break
    
    st.sidebar.markdown("---")
    
    # Currency/FX Section
    st.sidebar.markdown("### 💱 Currency Settings")
    
    fx_mode = st.sidebar.radio(
        "FX Rate Mode",
        options=["Live Spot (Free API)", "Manual Entry", "Average (Upload CSV)"],
        index=0,
        help="Choose how to get FX rates for currency conversion"
    )
    
    manual_rates = {}
    average_fx_data = None
    
    if fx_mode == "Manual Entry":
        st.sidebar.markdown("**Enter FX Rates (to USD):**")
        manual_rates['AED'] = st.sidebar.number_input(
            "1 AED = X USD", value=0.2723, format="%.6f", step=0.0001
        )
        manual_rates['SAR'] = st.sidebar.number_input(
            "1 SAR = X USD", value=0.2666, format="%.6f", step=0.0001
        )
        manual_rates['GBP'] = st.sidebar.number_input(
            "1 GBP = X USD", value=1.27, format="%.4f", step=0.01
        )
        manual_rates['EUR'] = st.sidebar.number_input(
            "1 EUR = X USD", value=1.08, format="%.4f", step=0.01
        )
        manual_rates['JPY'] = st.sidebar.number_input(
            "1 JPY = X USD", value=0.0067, format="%.6f", step=0.0001
        )
        manual_rates['HKD'] = st.sidebar.number_input(
            "1 HKD = X USD", value=0.128, format="%.4f", step=0.001
        )
        manual_rates['KWD'] = st.sidebar.number_input(
            "1 KWD = X USD", value=3.25, format="%.4f", step=0.01
        )
        manual_rates['QAR'] = st.sidebar.number_input(
            "1 QAR = X USD", value=0.2747, format="%.6f", step=0.0001
        )
    
    elif fx_mode == "Average (Upload CSV)":
        st.sidebar.markdown("**Upload FX CSV:**")
        st.sidebar.caption("Columns: date, AEDUSD, SARUSD, etc.")
        fx_file = st.sidebar.file_uploader("FX Data CSV", type=['csv'])
        if fx_file:
            try:
                average_fx_data = pd.read_csv(fx_file).to_dict()
                st.sidebar.success("✅ FX data loaded")
            except Exception as e:
                st.sidebar.error(f"Error loading FX data: {e}")
    
    # Create FX configuration
    if fx_mode == "Live Spot (Free API)":
        fx_config = FXConfiguration(
            mode=FXMode.LIVE_SPOT,
            output_currency=Currency.USD,
            live_fx_source="exchangerate.host"
        )
    elif fx_mode == "Manual Entry":
        fx_config = FXConfiguration(
            mode=FXMode.MANUAL,
            output_currency=Currency.USD,
            manual_rates=manual_rates
        )
    else:
        fx_config = FXConfiguration(
            mode=FXMode.AVERAGE,
            output_currency=Currency.USD,
            average_fx_data=average_fx_data
        )
    
    st.sidebar.markdown("---")
    
    # Data Input Mode
    st.sidebar.markdown("### 📥 Data Input")
    
    input_mode = st.sidebar.radio(
        "Input Method",
        options=["Manual Entry", "CSV Upload", "Web Extraction (Experimental)"],
        index=0
    )
    
    return date_range, selected_exchanges, fx_config, input_mode


def render_manual_data_entry(selected_exchanges):
    """Render manual data entry form."""
    st.markdown("### 📝 Enter Exchange Data")
    st.markdown("Enter the metrics for each selected exchange in their local currencies.")
    
    exchange_inputs = []
    
    # Create columns for a cleaner layout
    for i, exchange_config in enumerate(selected_exchanges):
        with st.expander(f"**{exchange_config['exchange']}** ({exchange_config['region']})", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                ytd = st.number_input(
                    f"YTD % Change",
                    value=0.0,
                    format="%.2f",
                    step=0.1,
                    key=f"ytd_{i}",
                    help="Year-to-date percentage change of the index"
                )
            
            with col2:
                market_cap = st.number_input(
                    f"Market Cap ({exchange_config['local_currency']})",
                    value=0.0,
                    format="%.0f",
                    step=1e9,
                    key=f"cap_{i}",
                    help="Total market capitalization in local currency (enter raw number, e.g., 500000000000 for 500B)"
                )
            
            with col3:
                adtv = st.number_input(
                    f"Avg Daily Value ({exchange_config['local_currency']})",
                    value=0.0,
                    format="%.0f",
                    step=1e6,
                    key=f"adtv_{i}",
                    help="Average daily traded value in local currency"
                )
            
            # Create ExchangeInput
            exchange_input = ExchangeInput(
                region=exchange_config['region'],
                exchange=exchange_config['exchange'],
                index_name=exchange_config['index_name'],
                local_currency=exchange_config['local_currency'],
                ytd_percent=ytd if ytd != 0.0 else None,
                market_cap_local=market_cap if market_cap > 0 else None,
                adtv_local=adtv if adtv > 0 else None,
                source="manual"
            )
            exchange_inputs.append(exchange_input)
    
    return exchange_inputs


def render_csv_upload(selected_exchanges):
    """Render CSV upload interface."""
    st.markdown("### 📄 Upload Exchange Data CSV")
    
    # Show template
    st.markdown("**CSV Template:**")
    template_data = []
    for e in selected_exchanges:
        template_data.append({
            'region': e['region'],
            'exchange': e['exchange'],
            'index_name': e['index_name'],
            'local_currency': e['local_currency'],
            'ytd_percent': '',
            'market_cap_local': '',
            'adtv_local': ''
        })
    
    template_df = pd.DataFrame(template_data)
    st.dataframe(template_df, use_container_width=True)
    
    # Download template button
    csv_template = template_df.to_csv(index=False)
    st.download_button(
        "📥 Download Template CSV",
        csv_template,
        "exchange_data_template.csv",
        "text/csv"
    )
    
    # Upload
    uploaded_file = st.file_uploader("Upload your data CSV", type=['csv'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.success("✅ CSV loaded successfully")
            st.dataframe(df, use_container_width=True)
            
            # Convert to ExchangeInput objects
            exchange_inputs = []
            for _, row in df.iterrows():
                exchange_input = ExchangeInput(
                    region=row.get('region', 'Unknown'),
                    exchange=row.get('exchange', 'Unknown'),
                    index_name=row.get('index_name', 'Unknown'),
                    local_currency=row.get('local_currency', 'USD'),
                    ytd_percent=row.get('ytd_percent') if pd.notna(row.get('ytd_percent')) else None,
                    market_cap_local=row.get('market_cap_local') if pd.notna(row.get('market_cap_local')) else None,
                    adtv_local=row.get('adtv_local') if pd.notna(row.get('adtv_local')) else None,
                    source="csv_upload"
                )
                exchange_inputs.append(exchange_input)
            
            return exchange_inputs
        except Exception as e:
            st.error(f"Error loading CSV: {e}")
            return []
    
    return []


def render_web_extraction():
    """Render web extraction interface with warnings."""
    st.markdown("### 🌐 Web Extraction (Experimental)")
    
    st.markdown(get_extraction_status())
    
    st.warning("""
    **⚠️ Web extraction is disabled in the MVP.**
    
    Most exchange websites require JavaScript rendering or block automated requests.
    Please use Manual Entry or CSV Upload for reliable data input.
    """)
    
    return []


def render_comparison_table(outputs, date_range, year):
    """Render the main comparison table."""
    
    # Title
    exchanges_str = " vs ".join([o.exchange for o in outputs[:3]])
    if len(outputs) > 3:
        exchanges_str = f"{exchanges_str} + {len(outputs) - 3} more"
    
    st.markdown(f"""
    <div class="section-title">
        {exchanges_str} — {year} Overview (All in USD)
    </div>
    """, unsafe_allow_html=True)
    
    # Date range info
    st.caption(f"📅 Date Range: {date_range.start_date} to {date_range.end_date}")
    
    # Create display dataframe
    display_df = create_comparison_dataframe(outputs)
    
    # Style the dataframe
    def style_ytd(val):
        if val == "N/A":
            return "color: gray"
        try:
            num = float(val.replace('%', '').replace('+', ''))
            if num >= 0:
                return "color: #10b981; font-weight: bold"
            else:
                return "color: #ef4444; font-weight: bold"
        except:
            return ""
    
    # Display table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Region": st.column_config.TextColumn("Region", width="small"),
            "Exchange": st.column_config.TextColumn("Exchange", width="small"),
            "Index Name": st.column_config.TextColumn("Index Name", width="medium"),
            "YTD % Change": st.column_config.TextColumn("YTD % Change", width="small"),
            "Market Cap (USD)": st.column_config.TextColumn("Market Cap (USD)", width="medium"),
            "Avg Daily Value (USD)": st.column_config.TextColumn("Avg Daily Value (USD)", width="medium"),
        }
    )


def render_insights(outputs, year):
    """Render the key insights section."""
    st.markdown("""
    <div class="section-title">
        🔍 Key Observations After Currency Unification
    </div>
    """, unsafe_allow_html=True)
    
    insights = generate_insights(outputs, year)
    
    for insight in insights:
        st.markdown(f"""
        <div class="insight-item">
            • {insight}
        </div>
        """, unsafe_allow_html=True)


def render_next_steps():
    """Render the next steps section."""
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


def render_charts(outputs):
    """Render visualization charts."""
    st.markdown("""
    <div class="section-title">
        📊 Visual Comparison
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Market Cap", "Daily Volume", "YTD Performance"])
    
    with tab1:
        # Market Cap Bar Chart
        cap_data = [
            {"Exchange": o.exchange, "Market Cap (USD)": o.market_cap_usd or 0}
            for o in outputs if o.market_cap_usd is not None
        ]
        if cap_data:
            df = pd.DataFrame(cap_data)
            fig = px.bar(
                df, x="Exchange", y="Market Cap (USD)",
                title="Market Capitalization by Exchange (USD)",
                color="Market Cap (USD)",
                color_continuous_scale="Blues"
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                showlegend=False
            )
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>Market Cap: $%{y:,.0f}<extra></extra>"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No market cap data available for visualization")
    
    with tab2:
        # ADTV Bar Chart
        adtv_data = [
            {"Exchange": o.exchange, "ADTV (USD)": o.adtv_usd or 0}
            for o in outputs if o.adtv_usd is not None
        ]
        if adtv_data:
            df = pd.DataFrame(adtv_data)
            fig = px.bar(
                df, x="Exchange", y="ADTV (USD)",
                title="Average Daily Traded Value by Exchange (USD)",
                color="ADTV (USD)",
                color_continuous_scale="Greens"
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                showlegend=False
            )
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>ADTV: $%{y:,.0f}<extra></extra>"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No ADTV data available for visualization")
    
    with tab3:
        # YTD Performance Bar Chart
        ytd_data = [
            {"Exchange": o.exchange, "YTD %": o.ytd_percent}
            for o in outputs if o.ytd_percent is not None
        ]
        if ytd_data:
            df = pd.DataFrame(ytd_data)
            colors = ['#10b981' if x >= 0 else '#ef4444' for x in df['YTD %']]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=df['Exchange'],
                    y=df['YTD %'],
                    marker_color=colors,
                    text=[f"{x:+.2f}%" for x in df['YTD %']],
                    textposition='outside'
                )
            ])
            fig.update_layout(
                title="YTD Performance by Exchange",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                yaxis_title="YTD % Change",
                xaxis_title="Exchange"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No YTD performance data available for visualization")


def render_audit_panel(audit_records, fx_rates, fx_config, date_range):
    """Render the audit trail panel."""
    with st.expander("🔎 Audit Trail & Data Traceability", expanded=False):
        st.markdown("### FX Rates Used")
        
        # FX Summary
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**FX Mode:** {fx_config.mode.value}")
            st.markdown(f"**Output Currency:** {fx_config.output_currency}")
        with col2:
            st.markdown(f"**Date Range:** {date_range.start_date} to {date_range.end_date}")
            if fx_rates:
                ts = list(fx_rates.values())[0].timestamp if fx_rates else datetime.utcnow()
                st.markdown(f"**As-of Timestamp:** {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # FX Rates Table
        if fx_rates:
            fx_df = pd.DataFrame([
                {
                    "Currency": curr,
                    "Rate (to USD)": f"{rate.rate:.6f}",
                    "Source": rate.source,
                    "Timestamp": rate.timestamp.strftime('%Y-%m-%d %H:%M')
                }
                for curr, rate in fx_rates.items()
            ])
            st.dataframe(fx_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### Computation Audit Trail")
        
        # Audit records table
        audit_df = create_audit_dataframe(audit_records)
        st.dataframe(audit_df, use_container_width=True, hide_index=True)


def render_downloads(outputs, audit_records, fx_rates, date_range, fx_config):
    """Render download buttons."""
    st.markdown("### 📥 Downloads")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # CSV Download
        raw_df = create_raw_dataframe(outputs)
        csv_data = raw_df.to_csv(index=False)
        st.download_button(
            "⬇️ Download CSV",
            csv_data,
            f"exchange_comparison_{date_range.year}.csv",
            "text/csv",
            use_container_width=True
        )
    
    with col2:
        # JSON Download
        json_data = export_to_json(outputs, audit_records, fx_rates, date_range, fx_config)
        json_str = json.dumps(json_data, indent=2, default=str)
        st.download_button(
            "⬇️ Download JSON",
            json_str,
            f"exchange_comparison_{date_range.year}.json",
            "application/json",
            use_container_width=True
        )
    
    with col3:
        # Display-ready CSV
        display_df = create_comparison_dataframe(outputs)
        display_csv = display_df.to_csv(index=False)
        st.download_button(
            "⬇️ Download Display CSV",
            display_csv,
            f"exchange_comparison_display_{date_range.year}.csv",
            "text/csv",
            use_container_width=True
        )


def render_placeholder_panels():
    """Render placeholder panels for future features."""
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container():
            st.markdown("""
            <div class="info-box">
                <h4>🏢 Sector Breakdown</h4>
                <p style="color: #94a3b8;">Coming in v2.0</p>
                <p style="color: #64748b; font-size: 0.9rem;">
                    Sector-wise breakdown showing leading sectors in each region
                    with contribution to overall index performance.
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        with st.container():
            st.markdown("""
            <div class="info-box">
                <h4>🏆 Top Companies</h4>
                <p style="color: #94a3b8;">Coming in v2.0</p>
                <p style="color: #64748b; font-size: 0.9rem;">
                    Top 3 companies by market cap in each exchange
                    with their individual performance metrics.
                </p>
            </div>
            """, unsafe_allow_html=True)


def main():
    """Main application entry point."""
    init_session_state()
    
    # Header
    st.title("📊 Exchange Comparison Dashboard")
    st.markdown("*Compare DFM, ADX, Tadawul and global exchanges on liquidity and performance*")
    
    # Sidebar configuration
    date_range, selected_exchanges, fx_config, input_mode = render_sidebar()
    
    # Main content area
    if not selected_exchanges:
        st.warning("Please select at least one exchange from the sidebar.")
        return
    
    # Data Input Section
    st.markdown("---")
    
    exchange_inputs = []
    
    if input_mode == "Manual Entry":
        exchange_inputs = render_manual_data_entry(selected_exchanges)
    elif input_mode == "CSV Upload":
        exchange_inputs = render_csv_upload(selected_exchanges)
    else:
        exchange_inputs = render_web_extraction()
        if not exchange_inputs:
            # Fall back to manual entry
            st.markdown("---")
            st.info("Please use manual entry below:")
            exchange_inputs = render_manual_data_entry(selected_exchanges)
    
    # Generate Report Button
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_clicked = st.button(
            "🚀 Generate Comparison Report",
            use_container_width=True,
            type="primary"
        )
    
    if generate_clicked and exchange_inputs:
        with st.spinner("Computing comparison..."):
            # Compute outputs
            outputs, audit_records, fx_rates, fx_status = compute_exchange_outputs(
                exchange_inputs, fx_config, date_range
            )
            
            # Store in session state
            st.session_state.computed_results = {
                'outputs': outputs,
                'audit_records': audit_records,
                'fx_rates': fx_rates,
                'fx_status': fx_status
            }
        
        st.success(f"✅ Report generated! FX Status: {fx_status}")
    
    # Display Results
    if st.session_state.computed_results:
        results = st.session_state.computed_results
        outputs = results['outputs']
        audit_records = results['audit_records']
        fx_rates = results['fx_rates']
        
        st.markdown("---")
        
        # Main comparison table
        render_comparison_table(outputs, date_range, date_range.year)
        
        st.markdown("---")
        
        # Two-column layout for insights and next steps
        col1, col2 = st.columns([3, 2])
        
        with col1:
            render_insights(outputs, date_range.year)
        
        with col2:
            render_next_steps()
        
        st.markdown("---")
        
        # Charts
        render_charts(outputs)
        
        st.markdown("---")
        
        # Placeholder panels
        render_placeholder_panels()
        
        st.markdown("---")
        
        # Audit panel
        render_audit_panel(audit_records, fx_rates, fx_config, date_range)
        
        st.markdown("---")
        
        # Downloads
        render_downloads(outputs, audit_records, fx_rates, date_range, fx_config)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #64748b; font-size: 0.8rem;">
        Exchange Comparison Dashboard v1.0 | Built with Streamlit | 
        Data should be verified against official sources
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
