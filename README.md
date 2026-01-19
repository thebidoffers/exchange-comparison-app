# 📊 Exchange Comparison Dashboard

A production-ready Streamlit web application for comparing stock exchanges (DFM, ADX, Tadawul, and global exchanges) on liquidity and performance metrics, with automatic USD currency unification.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

- **Multi-Exchange Comparison**: Compare DFM, ADX, Tadawul and 9+ global exchanges
- **Currency Unification**: Automatic conversion to USD using live FX rates, manual rates, or historical averages
- **Executive-Ready Output**: Clean, professional tables with key insights
- **Full Audit Trail**: Complete traceability of all data sources and calculations
- **Multiple Input Methods**: Manual entry, CSV upload, or experimental web extraction
- **Interactive Charts**: Visual comparisons of market cap, liquidity, and YTD performance
- **Export Options**: Download results as CSV or JSON with full metadata

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/exchange-comparison-app.git
   cd exchange-comparison-app
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Open in browser**
   - The app will automatically open at `http://localhost:8501`

## 🌐 Deployment

### Streamlit Community Cloud (Recommended)

1. Push your code to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your repository, branch, and `app.py` as the main file
5. Click "Deploy"

### Render.com

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Deploy

### Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 📖 Usage Guide

### 1. Configure Settings (Sidebar)

#### Date Range
- **YTD**: January 1st of selected year to today
- **Full Year**: January 1st to December 31st
- **Custom**: Select specific start and end dates

#### Exchange Selection
- **Primary (GCC)**: DFM, ADX, Tadawul (selected by default)
- **Additional (Global)**: Kuwait, Qatar, NYSE, NASDAQ, FTSE 100, DAX, CAC 40, Nikkei 225, Hang Seng

#### FX Rate Mode
- **Live Spot**: Fetches current rates from free APIs (exchangerate.host / ECB)
- **Manual Entry**: Enter your own FX rates
- **Average**: Upload a CSV with daily FX rates to calculate period averages

### 2. Enter Data

#### Manual Entry
Fill in the form for each exchange:
- YTD % Change (e.g., 5.23 for +5.23%)
- Market Cap in local currency (raw number)
- Average Daily Traded Value in local currency

#### CSV Upload
Download the template, fill it out, and upload:
```csv
region,exchange,index_name,local_currency,ytd_percent,market_cap_local,adtv_local
UAE,DFM,DFM General Index,AED,5.23,750000000000,450000000
```

### 3. Generate Report

Click "Generate Comparison Report" to:
- Convert all values to USD
- Generate comparison table
- Create insights automatically
- Display interactive charts

### 4. Export Results

Download your results as:
- **CSV**: Raw data for further analysis
- **JSON**: Full data with audit metadata
- **Display CSV**: Formatted table as shown

## 📁 Project Structure

```
exchange-comparison-app/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── data/
│   ├── example_input_template.csv  # Template for CSV upload
│   └── fx_sample.csv               # Sample FX data for averaging
└── src/
    ├── __init__.py           # Module exports
    ├── schemas.py            # Pydantic models & data classes
    ├── fx.py                 # FX rate retrieval & conversion
    ├── compute.py            # Metrics computation & formatting
    ├── insights.py           # Deterministic insight generation
    └── extraction.py         # Web extraction (experimental)
```

## 🔧 Adding More Exchanges

1. **Edit `src/schemas.py`**:
   ```python
   # Add to OPTIONAL_EXCHANGES list
   {
       "region": "Your Region",
       "exchange": "Exchange Name",
       "index_name": "Main Index",
       "local_currency": "CUR",  # 3-letter code
   },
   ```

2. **Add FX Support** (if new currency):
   - For pegged currencies: Add to `static_rates` in `src/fx.py`
   - For floating currencies: The live API should handle it automatically

3. **Update Manual Rates UI** (if needed):
   - Add input field in `render_sidebar()` function in `app.py`

## 🔐 Data Integrity Rules

This application follows strict data integrity rules:

1. **No Invented Data**: If a value is missing, it displays "N/A"
2. **Full Traceability**: Every number links to a user input, stored file, or API response
3. **Transparent FX**: Always shows FX source, rates used, and timestamps
4. **Deterministic Calculations**: All computations in pandas, reproducible results

## 📊 Supported Metrics

| Metric | Description |
|--------|-------------|
| YTD % Change | Year-to-date index performance |
| Market Cap | Total market capitalization |
| ADTV | Average Daily Traded Value |
| Index Name | Primary market index |
| Region | Geographic region |

## 🛠️ Technical Details

### FX Rate Sources

1. **Primary**: exchangerate.host (free, no API key)
2. **Fallback**: frankfurter.app (ECB rates)
3. **Static**: Pegged rates for GCC currencies (AED, SAR, QAR)

### Supported Currencies

| Currency | Type | Rate to USD |
|----------|------|-------------|
| AED | Pegged | ~0.2723 |
| SAR | Pegged | ~0.2666 |
| QAR | Pegged | ~0.2747 |
| KWD | Managed Float | ~3.25 |
| USD | Base | 1.0 |
| GBP, EUR, JPY, HKD | Floating | Live rates |

## ⚠️ Limitations

- **Web Extraction**: Experimental only; most exchange sites require JavaScript
- **Real-time Data**: Not connected to live market feeds
- **Historical Data**: Requires manual input or CSV upload
- **Rate Limits**: Free FX APIs may have usage limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Streamlit](https://streamlit.io/) for the amazing framework
- [Plotly](https://plotly.com/) for interactive charts
- [exchangerate.host](https://exchangerate.host/) for free FX data
- [ECB](https://www.ecb.europa.eu/) for reference rates

## 📞 Support

For issues or questions:
- Open a GitHub issue
- Check existing documentation
- Review the audit trail for data traceability

---

**Disclaimer**: This tool is for informational purposes only. Always verify data against official exchange sources before making investment decisions.
