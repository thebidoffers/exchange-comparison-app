"""
Web extraction module for fetching exchange data from public sources.
WARNING: Web scraping is experimental and may fail due to website changes.
This module should be used with caution and manual verification.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Optional, Tuple
import re


class ExtractionError(Exception):
    """Custom exception for extraction failures."""
    pass


def fetch_page(url: str, timeout: int = 15) -> Tuple[Optional[str], str]:
    """
    Fetch HTML content from a URL.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
    
    Returns:
        Tuple of (HTML content or None, status message)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text, "Success"
    except requests.exceptions.Timeout:
        return None, f"Timeout fetching {url}"
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def extract_number(text: str) -> Optional[float]:
    """
    Extract a numeric value from text.
    Handles formats like "1,234.56", "1.5B", "2.3T", etc.
    
    Args:
        text: Text containing a number
    
    Returns:
        Extracted float value or None
    """
    if not text:
        return None
    
    # Clean text
    text = text.strip().replace(',', '').replace(' ', '')
    
    # Handle billion/trillion suffixes
    multipliers = {
        'T': 1e12, 't': 1e12,
        'B': 1e9, 'b': 1e9,
        'M': 1e6, 'm': 1e6,
        'K': 1e3, 'k': 1e3,
    }
    
    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return float(text[:-1]) * mult
            except ValueError:
                pass
    
    # Try direct conversion
    try:
        # Remove currency symbols
        text = re.sub(r'^[^\d.-]+', '', text)
        text = re.sub(r'[^\d.-]+$', '', text)
        return float(text)
    except ValueError:
        return None


def extract_percentage(text: str) -> Optional[float]:
    """
    Extract a percentage value from text.
    Handles formats like "+5.23%", "-2.10%", "5.23", etc.
    
    Args:
        text: Text containing a percentage
    
    Returns:
        Extracted percentage as float (e.g., 5.23 for 5.23%)
    """
    if not text:
        return None
    
    # Remove % symbol and whitespace
    text = text.strip().replace('%', '').replace(' ', '')
    
    try:
        return float(text)
    except ValueError:
        return None


def try_extract_from_config(config: Dict) -> Tuple[Dict, str]:
    """
    Attempt to extract exchange data based on a configuration.
    
    Args:
        config: Dictionary with:
            - url: Source URL
            - selectors: Dict of CSS selectors for each field
            - exchange: Exchange identifier
    
    Returns:
        Tuple of (extracted data dict, status message)
    
    Example config:
    {
        "url": "https://www.dfm.ae/en/market-data/market-summary",
        "exchange": "DFM",
        "selectors": {
            "index_value": "div.index-value",
            "market_cap": "td.market-cap",
            "ytd_change": "span.ytd-percent"
        }
    }
    """
    result = {
        "exchange": config.get("exchange", "Unknown"),
        "source": config.get("url", ""),
        "timestamp": datetime.utcnow().isoformat(),
        "data": {},
        "errors": []
    }
    
    url = config.get("url")
    if not url:
        return result, "No URL provided"
    
    html, status = fetch_page(url)
    if not html:
        result["errors"].append(status)
        return result, status
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        selectors = config.get("selectors", {})
        
        for field, selector in selectors.items():
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    
                    if "percent" in field.lower() or "change" in field.lower():
                        value = extract_percentage(text)
                    else:
                        value = extract_number(text)
                    
                    result["data"][field] = {
                        "raw": text,
                        "parsed": value
                    }
                else:
                    result["errors"].append(f"Selector '{selector}' found no element for {field}")
            except Exception as e:
                result["errors"].append(f"Error extracting {field}: {str(e)}")
        
        status = "Partial success" if result["errors"] else "Success"
        return result, status
        
    except Exception as e:
        result["errors"].append(f"Parsing error: {str(e)}")
        return result, f"Parsing failed: {str(e)}"


# Pre-configured extraction configs for known exchanges
# These are BEST EFFORT and may break when websites change
KNOWN_EXCHANGE_CONFIGS = {
    "DFM": {
        "url": "https://www.dfm.ae/",
        "exchange": "DFM",
        "note": "Dubai Financial Market - extraction may require JavaScript rendering",
        "selectors": {}  # Empty - needs specific selectors
    },
    "ADX": {
        "url": "https://www.adx.ae/",
        "exchange": "ADX",
        "note": "Abu Dhabi Securities Exchange - extraction may require JavaScript rendering",
        "selectors": {}
    },
    "Tadawul": {
        "url": "https://www.saudiexchange.sa/",
        "exchange": "Tadawul",
        "note": "Saudi Exchange - extraction may require JavaScript rendering",
        "selectors": {}
    },
}


def get_extraction_status() -> str:
    """
    Return a status message about extraction capabilities.
    """
    return """
    ⚠️ **Web Extraction Notice**
    
    Automated web extraction is experimental and provided as-is:
    - Most exchange websites use JavaScript rendering, requiring special tools (Selenium/Playwright)
    - Websites may block automated requests
    - Data structures change frequently
    - Results should always be manually verified
    
    **Recommended Approach:** Use manual data entry or CSV upload for production use.
    Web extraction is suitable only for experimentation.
    """


def create_extraction_config_template() -> Dict:
    """
    Create a template configuration for custom extraction.
    """
    return {
        "url": "https://example.com/market-data",
        "exchange": "EXCHANGE_NAME",
        "selectors": {
            "index_value": "CSS_SELECTOR_FOR_INDEX",
            "market_cap": "CSS_SELECTOR_FOR_MARKET_CAP",
            "ytd_change": "CSS_SELECTOR_FOR_YTD_PERCENT",
            "adtv": "CSS_SELECTOR_FOR_DAILY_VALUE"
        },
        "notes": "Add any notes about the source here"
    }
