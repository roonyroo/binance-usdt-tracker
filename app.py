import streamlit as st
import websocket
import json
import threading
import time
import pandas as pd
from datetime import datetime

# Global variables
ws = None
ticker_data = {}
is_connected = False
ws_thread = None

def on_message(ws, message):
    """Handle incoming WebSocket messages"""
    global ticker_data
    try:
        data = json.loads(message)
        if isinstance(data, list):
            for item in data:
                if 's' in item and item['s'].endswith('USDT'):
                    ticker_data[item['s']] = item
        elif isinstance(data, dict) and 's' in data and data['s'].endswith('USDT'):
            ticker_data[data['s']] = data
    except Exception as e:
        st.error(f"Error processing message: {e}")

def on_error(ws, error):
    """Handle WebSocket errors"""
    st.error(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Handle WebSocket close"""
    global is_connected
    is_connected = False
    st.info("WebSocket connection closed")

def on_open(ws):
    """Handle WebSocket open"""
    global is_connected
    is_connected = True
    st.success("WebSocket connected to Binance!")

def start_websocket():
    """Start the WebSocket connection"""
    global ws, is_connected, ws_thread
    
    if ws is not None:
        ws.close()
    
    ws = websocket.WebSocketApp(
        "wss://stream.binance.com:9443/ws/!ticker@arr",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

def stop_websocket():
    """Stop the WebSocket connection"""
    global ws, is_connected
    if ws:
        ws.close()
        ws = None
    is_connected = False

def calculate_profit_opportunities():
    """Calculate profit opportunities from ticker data"""
    if not ticker_data:
        return pd.DataFrame()
    
    opportunities = []
    
    for symbol, data in ticker_data.items():
        try:
            current_price = float(data['c'])
            high_price = float(data['h'])
            low_price = float(data['l'])
            
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
    
    return pd.DataFrame(opportunities)

# Streamlit UI
st.title("Binance USDT Tracker")

# WebSocket controls
col1, col2 = st.columns(2)

with col1:
    if st.button("Start Connection"):
        start_websocket()

with col2:
    if st.button("Stop Connection"):
        stop_websocket()

# Connection status
if is_connected:
    st.success("🟢 Connected to Binance WebSocket")
else:
    st.error("🔴 Not connected")

# Data display
st.subheader("Profit Opportunities")
st.text("Showing coins with ~8% profit margin and <2% above low price")

if ticker_data:
    df = calculate_profit_opportunities()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No opportunities found matching criteria")
    
    st.text(f"Total USDT pairs tracked: {len(ticker_data)}")
else:
    st.info("No data available. Start connection to begin tracking.")

# Auto-refresh
time.sleep(1)
st.rerun()
