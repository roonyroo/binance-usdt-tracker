import streamlit as st
import websocket
import json
import pandas as pd
import threading
import time
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Binance USDT Tracker",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'ticker_data' not in st.session_state:
    st.session_state.ticker_data = {}
if 'ws_running' not in st.session_state:
    st.session_state.ws_running = False
if 'ws_thread' not in st.session_state:
    st.session_state.ws_thread = None
if 'ws_connection' not in st.session_state:
    st.session_state.ws_connection = None

def on_message(ws, message):
    """Handle incoming WebSocket messages"""
    try:
        data = json.loads(message)
        symbol = data['s']
        
        # Filter for USDT pairs only
        if symbol.endswith('USDT'):
            st.session_state.ticker_data[symbol] = {
                'current_price': float(data['c']),
                'high_price': float(data['h']),
                'low_price': float(data['l']),
                'price_change_percent': float(data['P']),
                'timestamp': datetime.now()
            }
    except Exception as e:
        print(f"Error processing message: {e}")

def on_error(ws, error):
    """Handle WebSocket errors"""
    print(f"WebSocket error: {error}")
    st.session_state.ws_running = False

def on_close(ws, close_status_code, close_msg):
    """Handle WebSocket close"""
    print(f"WebSocket closed: {close_status_code} - {close_msg}")
    st.session_state.ws_running = False

def on_open(ws):
    """Handle WebSocket open"""
    print("WebSocket connection opened")
    st.session_state.ws_running = True

def start_websocket():
    """Start the WebSocket connection"""
    try:
        ws_url = "wss://stream.binance.com:9443/ws/!ticker@arr"
        st.session_state.ws_connection = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        st.session_state.ws_connection.run_forever()
    except Exception as e:
        print(f"Error starting WebSocket: {e}")
        st.session_state.ws_running = False

def stop_websocket():
    """Stop the WebSocket connection"""
    if st.session_state.ws_connection:
        st.session_state.ws_connection.close()
    st.session_state.ws_running = False

def calculate_profit_opportunities():
    """Calculate profit opportunities from ticker data"""
    if not st.session_state.ticker_data:
        return pd.DataFrame()
    
    opportunities = []
    
    for symbol, data in st.session_state.ticker_data.items():
        current_price = data['current_price']
        high_price = data['high_price']
        low_price = data['low_price']
        
        # Calculate % difference from current price to lowest price
        ld = ((current_price - low_price) / low_price) * 100
        
        # Calculate % difference from current price to highest price
        hd = ((high_price - current_price) / current_price) * 100
        
        # Calculate profit margin (% difference between highest and lowest price)
        profit = ((high_price - low_price) / low_price) * 100
        
        opportunities.append({
            'Symbol': symbol,
            'Current': current_price,
            'High': high_price,
            'Low': low_price,
            'LD': round(ld, 2),
            'HD': round(hd, 2),
            '% Profit': round(profit, 2)
        })
    
    df = pd.DataFrame(opportunities)
    return df

# Main title
st.title("📊 Binance USDT Tracker")

# WebSocket controls
col1, col2 = st.columns(2)

with col1:
    if st.button("Start Connection", type="primary"):
        if not st.session_state.ws_running:
            st.session_state.ws_thread = threading.Thread(target=start_websocket, daemon=True)
            st.session_state.ws_thread.start()
            st.success("Connection started!")
        else:
            st.info("Already connected")

with col2:
    if st.button("Stop Connection"):
        stop_websocket()
        st.info("Connection stopped")

# Connection status
if st.session_state.ws_running:
    st.success("🟢 Connected")
else:
    st.error("🔴 Disconnected")

# Auto-refresh
if st.session_state.ws_running:
    time.sleep(1)
    st.rerun()

# Display data
if st.session_state.ticker_data:
    df = calculate_profit_opportunities()
    
    if not df.empty:
        st.write(f"**{len(df)} USDT pairs**")
        
        # ~8% profit margin
        st.subheader("~8% Profit")
        profit_8 = df[(df['% Profit'] >= 7) & (df['% Profit'] <= 9)]
        if not profit_8.empty:
            st.dataframe(profit_8[['Symbol', 'LD', 'HD', '% Profit']].sort_values('% Profit', ascending=False),
                        use_container_width=True)
        else:
            st.info("No matches")
        
        # <2% from low
        st.subheader("<2% from Low")
        low_2 = df[df['LD'] < 2]
        if not low_2.empty:
            st.dataframe(low_2[['Symbol', 'LD', 'HD', '% Profit']].sort_values('LD'),
                        use_container_width=True)
        else:
            st.info("No matches")
        
        # All data
        st.subheader("All Data")
        sort_by = st.selectbox("Sort by:", ['% Profit', 'LD', 'HD', 'Symbol'])
        sorted_df = df.sort_values(sort_by, ascending=False)
        st.dataframe(sorted_df[['Symbol', 'LD', 'HD', '% Profit']], use_container_width=True)

else:
    st.info("Start connection to load data")