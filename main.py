import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import time

# Page config
st.set_page_config(
    page_title="Binance USDT Tracker",
    page_icon="📊",
    layout="wide"
)

# Initialize session state with caching
if 'data' not in st.session_state:
    st.session_state.data = {}
if 'last_fetch' not in st.session_state:
    st.session_state.last_fetch = None
if 'cache_duration' not in st.session_state:
    st.session_state.cache_duration = 60  # Cache for 60 seconds

def is_cache_valid():
    """Check if cached data is still valid"""
    if not st.session_state.last_fetch:
        return False
    
    time_since_fetch = datetime.now() - st.session_state.last_fetch
    return time_since_fetch.total_seconds() < st.session_state.cache_duration

def test_binance_access():
    """Test if Binance API is accessible with rate limiting"""
    try:
        time.sleep(1)  # Rate limiting delay
        response = requests.get("https://api.binance.com/api/v3/ping", timeout=5)
        return response.status_code == 200, response.status_code
    except Exception as e:
        return False, str(e)

def fetch_data_with_retry():
    """Fetch data with retry logic and rate limiting"""
    # Check cache first
    if is_cache_valid():
        st.info(f"Using cached data (refreshes every {st.session_state.cache_duration}s)")
        return True
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            with st.spinner(f"Fetching data (attempt {attempt + 1}/{max_retries})..."):
                # Rate limiting delay
                time.sleep(2)
                
                response = requests.get(
                    "https://api.binance.com/api/v3/ticker/24hr",
                    timeout=15,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; CryptoTracker/1.0)',
                        'Accept': 'application/json'
                    }
                )
                
                if response.status_code == 429:
                    wait_time = retry_delay * (2 ** attempt)
                    st.warning(f"Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # Filter USDT pairs
                usdt_data = {}
                for item in data:
                    if item['symbol'].endswith('USDT'):
                        usdt_data[item['symbol']] = {
                            'current': float(item['lastPrice']),
                            'high': float(item['highPrice']),
                            'low': float(item['lowPrice']),
                            'change': float(item['priceChangePercent'])
                        }
                
                st.session_state.data = usdt_data
                st.session_state.last_fetch = datetime.now()
                return True
                
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                st.error(f"API Error after {max_retries} attempts: {e}")
                return False
            else:
                st.warning(f"Attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    
    return False

def calculate_opportunities():
    """Calculate profit opportunities"""
    if not st.session_state.data:
        return pd.DataFrame()
    
    opportunities = []
    for symbol, data in st.session_state.data.items():
        current = data['current']
        high = data['high']
        low = data['low']
        
        # Calculate percentages
        ld_percent = ((current - low) / low) * 100
        hd_percent = ((high - current) / current) * 100
        profit_percent = ((high - low) / low) * 100
        
        # Filter criteria: ~8% profit margin and <2% above low
        if profit_percent >= 7 and ld_percent <= 2:
            opportunities.append({
                'Symbol': symbol,
                'LD': f"{ld_percent:.1f}%",
                'HD': f"{hd_percent:.1f}%",
                'Profit': f"{profit_percent:.1f}%"
            })
    
    return pd.DataFrame(opportunities).sort_values('Profit', key=lambda x: x.str.replace('%', '').astype(float), ascending=False)

# Main UI
st.title("Binance USDT Tracker")
st.markdown("**Rate-limited API calls to prevent 429 errors**")

# Cache control
col1, col2, col3 = st.columns(3)

with col1:
    cache_duration = st.selectbox("Cache Duration", [30, 60, 120, 300], index=1)
    st.session_state.cache_duration = cache_duration

with col2:
    if st.button("Test API Access"):
        success, result = test_binance_access()
        if success:
            st.success(f"API accessible! Status: {result}")
        else:
            st.error(f"API blocked. Error: {result}")

with col3:
    if st.button("Get Live Data", type="primary"):
        if fetch_data_with_retry():
            st.success(f"Loaded {len(st.session_state.data)} USDT pairs!")
            st.rerun()

# Status display
if st.session_state.last_fetch:
    age = datetime.now() - st.session_state.last_fetch
    age_seconds = int(age.total_seconds())
    
    if age_seconds < st.session_state.cache_duration:
        st.success(f"Data loaded {age_seconds}s ago (cache valid for {st.session_state.cache_duration - age_seconds}s)")
    else:
        st.warning(f"Data is {age_seconds}s old (cache expired)")
    
    st.info(f"Tracking {len(st.session_state.data)} USDT pairs")
else:
    st.info("Click 'Get Live Data' to fetch from Binance API")

# Auto-refresh with rate limiting
if st.session_state.data and not is_cache_valid():
    st.info("Cache expired - click 'Get Live Data' to refresh")

# Results
if st.session_state.data:
    st.subheader("Profit Opportunities")
    st.text("Coins with ~8% profit margin and <2% above low price")
    
    df = calculate_opportunities()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success(f"Found {len(df)} opportunities!")
    else:
        st.info("No opportunities match criteria")

st.markdown("---")
st.markdown("*Rate-limited Amsterdam deployment - prevents 429 errors*")
