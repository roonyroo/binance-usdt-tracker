import streamlit as st
import json
import pandas as pd
from datetime import datetime
import requests
import time

# Page config
st.set_page_config(
    page_title="Binance USDT Tracker",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'ticker_data' not in st.session_state:
    st.session_state.ticker_data = {}
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False

def fetch_ticker_data():
    """Fetch ticker data from Binance API"""
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Filter USDT pairs
        usdt_data = {}
        for item in data:
            if item['symbol'].endswith('USDT'):
                try:
                    usdt_data[item['symbol']] = {
                        'current': float(item['lastPrice']),
                        'high': float(item['highPrice']),
                        'low': float(item['lowPrice']),
                        'change': float(item['priceChangePercent'])
                    }
                except (ValueError, KeyError):
                    continue
        
        st.session_state.ticker_data = usdt_data
        st.session_state.last_update = datetime.now()
        return True, len(usdt_data)
        
    except Exception as e:
        return False, str(e)

def calculate_opportunities():
    """Calculate profit opportunities"""
    if not st.session_state.ticker_data:
        return pd.DataFrame()
    
    opportunities = []
    for symbol, data in st.session_state.ticker_data.items():
        current = data['current']
        high = data['high']
        low = data['low']
        
        # Skip invalid data
        if low <= 0 or high <= 0 or current <= 0 or high < low:
            continue
            
        try:
            ld_percent = ((current - low) / low) * 100
            hd_percent = ((high - current) / current) * 100
            profit_percent = ((high - low) / low) * 100
            
            # Filter: 7%+ profit margin AND <2% above low
            if profit_percent >= 7 and ld_percent <= 2:
                opportunities.append({
                    'Symbol': symbol,
                    'LD': f"{ld_percent:.1f}%",
                    'HD': f"{hd_percent:.1f}%",
                    'Profit': f"{profit_percent:.1f}%"
                })
        except (ZeroDivisionError, ValueError):
            continue
    
    if opportunities:
        df = pd.DataFrame(opportunities)
        return df.sort_values('Profit', key=lambda x: x.str.replace('%', '').astype(float), ascending=False)
    return pd.DataFrame()

# Main UI
st.title("Binance USDT Tracker")
st.markdown("**Live data from Amsterdam region**")

# Controls
col1, col2 = st.columns(2)

with col1:
    if st.button("Get Live Data", type="primary"):
        with st.spinner("Fetching USDT pairs..."):
            success, result = fetch_ticker_data()
            if success:
                st.success(f"Loaded {result} USDT pairs!")
            else:
                st.error(f"Error: {result}")
        st.rerun()

with col2:
    st.session_state.auto_refresh = st.checkbox("Auto-refresh (30s)", value=st.session_state.auto_refresh)

# Status
if st.session_state.last_update:
    age = datetime.now() - st.session_state.last_update
    age_seconds = int(age.total_seconds())
    st.success(f"📊 Data loaded: {age_seconds}s ago | {len(st.session_state.ticker_data)} USDT pairs")
else:
    st.info("💡 Click 'Get Live Data' to fetch from Binance API")

# Auto-refresh logic
if st.session_state.auto_refresh and st.session_state.last_update:
    age = datetime.now() - st.session_state.last_update
    if age.total_seconds() >= 30:
        st.info("🔄 Auto-refreshing...")
        success, result = fetch_ticker_data()
        if success:
            st.rerun()

# Results
if st.session_state.ticker_data:
    st.subheader("Profit Opportunities")
    st.text("~8% profit margin and <2% above low price")
    
    df = calculate_opportunities()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success(f"✅ Found {len(df)} opportunities!")
    else:
        st.info("🔍 No opportunities match criteria")

# Manual refresh
if st.session_state.ticker_data:
    if st.button("🔄 Refresh Now"):
        with st.spinner("Refreshing..."):
            success, result = fetch_ticker_data()
            if success:
                st.success("Data refreshed!")
            else:
                st.error(f"Error: {result}")
        st.rerun()

st.markdown("---")
st.markdown("*Single API call - Production stable*")
