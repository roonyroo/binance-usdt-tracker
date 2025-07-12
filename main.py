import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Binance USDT Tracker",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = {}
if 'last_fetch' not in st.session_state:
    st.session_state.last_fetch = None

def fetch_binance_data():
    """Single REST API call to get all USDT pairs"""
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Filter USDT pairs in single loop
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
        return True, len(usdt_data)
        
    except Exception as e:
        return False, str(e)

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
        
        # Filter: ~8% profit margin AND <2% above low
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
st.markdown("**Single REST API call - Amsterdam region**")

# Single fetch button
if st.button("Get Live Data", type="primary"):
    with st.spinner("Fetching all USDT pairs..."):
        success, result = fetch_binance_data()
        if success:
            st.success(f"Loaded {result} USDT pairs!")
        else:
            st.error(f"Error: {result}")
    st.rerun()

# Status
if st.session_state.last_fetch:
    st.success(f"Data loaded at {st.session_state.last_fetch.strftime('%H:%M:%S')}")
    st.info(f"Tracking {len(st.session_state.data)} USDT pairs")
else:
    st.info("Click 'Get Live Data' to fetch from Binance API")

# Results
if st.session_state.data:
    st.subheader("Profit Opportunities")
    st.text("~8% profit margin and <2% above low price")
    
    df = calculate_opportunities()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success(f"Found {len(df)} opportunities!")
    else:
        st.info("No opportunities match criteria")

st.markdown("---")
st.markdown("*Single API call - Maximum efficiency*")
