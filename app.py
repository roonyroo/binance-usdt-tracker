import streamlit as st
import requests
import json
import threading
import time
import pandas as pd
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title=\"Binance USDT Tracker\",
    page_icon=\"📊\",
    layout=\"wide\"
)

# Global variables
ticker_data = {}
is_fetching = False
fetch_thread = None

def fetch_binance_data():
    \"\"\"Fetch ticker data from Binance REST API\"\"\"
    global ticker_data, is_fetching
    
    try:
        response = requests.get(
            \"https://api.binance.com/api/v3/ticker/24hr\",
            timeout=10
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
        
        ticker_data = new_ticker_data
        return True
        
    except requests.exceptions.RequestException as e:
        st.error(f\"API request failed: {e}\")
        return False
    except Exception as e:
        st.error(f\"Data processing error: {e}\")
        return False

def start_data_fetching():
    \"\"\"Start periodic data fetching\"\"\"
    global is_fetching, fetch_thread
    
    if is_fetching:
        return
        
    is_fetching = True
    
    def fetch_loop():
        while is_fetching:
            fetch_binance_data()
            time.sleep(5)  # Fetch every 5 seconds
    
    fetch_thread = threading.Thread(target=fetch_loop)
    fetch_thread.daemon = True
    fetch_thread.start()

def stop_data_fetching():
    \"\"\"Stop data fetching\"\"\"
    global is_fetching
    is_fetching = False

def calculate_profit_opportunities():
    \"\"\"Calculate profit opportunities from ticker data\"\"\"
    if not ticker_data:
        return pd.DataFrame()
    
    opportunities = []
    
    for symbol, data in ticker_data.items():
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
                    'LD': f\"{ld_percent:.1f}%\",
                    'HD': f\"{hd_percent:.1f}%\",
                    'Profit': f\"{profit_percent:.1f}%\"
                })
        except (ValueError, KeyError):
            continue
    
    # Sort by profit percentage (descending)
    opportunities.sort(key=lambda x: float(x['Profit'].replace('%', '')), reverse=True)
    return pd.DataFrame(opportunities)

# Main Streamlit UI
st.title(\"Binance USDT Tracker\")
st.markdown(\"Real-time cryptocurrency analysis using Binance REST API\")

# Data fetching controls
col1, col2 = st.columns(2)

with col1:
    if st.button(\"Start Live Data\"):
        start_data_fetching()
        st.rerun()

with col2:
    if st.button(\"Stop Data\"):
        stop_data_fetching()
        st.rerun()

# Connection status
if is_fetching:
    st.success(\"🟢 Fetching live data from Binance API\")
else:
    st.error(\"🔴 Not fetching data\")

# Manual refresh button
if st.button(\"Refresh Data Now\"):
    with st.spinner(\"Fetching latest data...\"):
        if fetch_binance_data():
            st.success(\"Data updated successfully!\")
        else:
            st.error(\"Failed to fetch data\")
    st.rerun()

# Data display
st.subheader(\"Profit Opportunities\")
st.text(\"Showing coins with ~8% profit margin and <2% above low price\")

if ticker_data:
    df = calculate_profit_opportunities()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success(f\"Found {len(df)} profit opportunities!\")
    else:
        st.info(\"No opportunities found matching criteria (8% profit, <2% above low)\")
    
    st.text(f\"Total USDT pairs tracked: {len(ticker_data)}\")
    
    # Show last update time
    if ticker_data:
        latest_time = max(data['timestamp'] for data in ticker_data.values())
        st.text(f\"Last update: {latest_time.strftime('%H:%M:%S')}\")
else:
    st.info(\"No data available. Click 'Start Live Data' to begin tracking.\")

# Auto-refresh every 10 seconds when fetching
if is_fetching:
    time.sleep(10)
    st.rerun()
