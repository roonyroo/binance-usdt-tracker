import streamlit as st
import requests
import json
import time
import pandas as pd
from datetime import datetime
import threading

# Set page configuration
st.set_page_config(
    page_title="Binance USDT Tracker",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'ticker_data' not in st.session_state:
    st.session_state.ticker_data = {}
if 'is_fetching' not in st.session_state:
    st.session_state.is_fetching = False
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

def fetch_binance_data():
    """Fetch ticker data from Binance REST API"""
    try:
        st.info("Fetching live data from Binance API...")
        response = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        # Filter USDT pairs and update ticker_data
        new_ticker_data = {}
        for item in data:
            if item['symbol'].endswith('USDT'):
                new_ticker_data[item['symbol']] = {
                    'current_price': float(item['lastPrice']),
                    'high_price': float(item['highPrice']),
                    'low_price': float(item['lowPrice']),
                    'price_change_percent': float(item['priceChangePercent']),
                    'timestamp': datetime.now()
                }
        
        st.session_state.ticker_data = new_ticker_data
        st.session_state.last_update = datetime.now()
        st.success(f"Successfully fetched {len(new_ticker_data)} USDT pairs!")
        return True
        
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return False
    except Exception as e:
        st.error(f"Data processing error: {e}")
        return False

def calculate_profit_opportunities():
    """Calculate profit opportunities from ticker data"""
    if not st.session_state.ticker_data:
        return pd.DataFrame()
    
    opportunities = []
    
    for symbol, data in st.session_state.ticker_data.items():
        try:
            current_price = data['current_price']
            high_price = data['high_price']
            low_price = data['low_price']
            
            # Calculate percentages
            ld_percent = ((current_price - low_price) / low_price) * 100
            hd_percent = ((high_price - current_price) / current_price) * 100
            profit_percent = ((high_price - low_price) / low_price) * 100
            
            # Filter: ~8% profit margin and <2% above low price
            if profit_percent >= 7 and ld_percent <= 2:
                opportunities.append({
                    'Symbol': symbol,
                    'LD': f"{ld_percent:.1f}%",
                    'HD': f"{hd_percent:.1f}%",
                    'Profit': f"{profit_percent:.1f}%"
                })
        except (ValueError, KeyError):
            continue
    
    # Sort by profit percentage (descending)
    opportunities.sort(key=lambda x: float(x['Profit'].replace('%', '')), reverse=True)
    return pd.DataFrame(opportunities)

# Main UI
st.title("Binance USDT Tracker")
st.markdown("**Real-time cryptocurrency analysis using HTTP API**")
st.markdown("*Deployed on Railway with live Binance data*")

# Controls
col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 Refresh Data Now", type="primary"):
        if fetch_binance_data():
            st.rerun()

with col2:
    if st.button("📊 Calculate Opportunities"):
        if st.session_state.ticker_data:
            st.rerun()
        else:
            st.warning("Please fetch data first!")

# Status
if st.session_state.last_update:
    st.success(f"✅ Live data active - Last updated: {st.session_state.last_update.strftime('%H:%M:%S')}")
else:
    st.info("🔄 Click 'Refresh Data Now' to fetch live Binance data")

# Display results
st.subheader("Profit Opportunities")
st.text("Coins with ~8% profit margin and <2% above low price")

if st.session_state.ticker_data:
    df = calculate_profit_opportunities()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success(f"Found {len(df)} profit opportunities!")
        
        # Show top opportunity
        if len(df) > 0:
            top_coin = df.iloc[0]
            st.markdown(f"**Top Opportunity:** {top_coin['Symbol']} - {top_coin['Profit']} profit potential")
    else:
        st.info("No opportunities found matching criteria")
    
    st.text(f"Total USDT pairs: {len(st.session_state.ticker_data)}")
else:
    st.info("No data loaded. Click 'Refresh Data Now' to start.")

# Auto-refresh option
if st.checkbox("Auto-refresh every 30 seconds"):
    time.sleep(30)
    fetch_binance_data()
    st.rerun()

# Footer
st.markdown("---")
st.markdown("*Railway deployment with live Binance API data*")
