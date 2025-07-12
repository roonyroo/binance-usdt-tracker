import streamlit as st
import json
import pandas as pd
from datetime import datetime
import asyncio
import websockets
import threading
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
if 'ws_connected' not in st.session_state:
    st.session_state.ws_connected = False
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'connection_status' not in st.session_state:
    st.session_state.connection_status = "disconnected"
if 'ws_thread' not in st.session_state:
    st.session_state.ws_thread = None
if 'stop_ws' not in st.session_state:
    st.session_state.stop_ws = False

def process_ticker_data(data):
    """Process incoming ticker data"""
    if isinstance(data, list):
        ticker_data = {}
        for item in data:
            if 's' in item and item['s'].endswith('USDT'):
                ticker_data[item['s']] = {
                    'current': float(item['c']),
                    'high': float(item['h']),
                    'low': float(item['l']),
                    'change': float(item['P'])
                }
        
        # Update session state
        st.session_state.ticker_data = ticker_data
        st.session_state.last_update = datetime.now()

async def websocket_client():
    """WebSocket client for Binance stream"""
    uri = "wss://stream.binance.com:9443/ws/!ticker@arr"
    
    try:
        st.session_state.connection_status = "connecting"
        async with websockets.connect(uri) as websocket:
            st.session_state.ws_connected = True
            st.session_state.connection_status = "connected"
            
            while not st.session_state.stop_ws:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    process_ticker_data(data)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    break
                    
    except Exception as e:
        st.session_state.connection_status = f"error: {str(e)}"
    finally:
        st.session_state.ws_connected = False
        st.session_state.connection_status = "disconnected"

def start_websocket():
    """Start WebSocket connection"""
    if st.session_state.ws_connected:
        return  # Already connected
    
    st.session_state.stop_ws = False
    st.session_state.connection_status = "starting"
    
    def run_websocket():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(websocket_client())
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_websocket)
    thread.daemon = True
    thread.start()
    st.session_state.ws_thread = thread

def stop_websocket():
    """Stop WebSocket connection"""
    st.session_state.stop_ws = True
    st.session_state.ws_connected = False
    st.session_state.connection_status = "stopping"

def calculate_opportunities():
    """Calculate profit opportunities with error handling"""
    if not st.session_state.ticker_data:
        return pd.DataFrame()
    
    opportunities = []
    for symbol, data in st.session_state.ticker_data.items():
        current = data['current']
        high = data['high']
        low = data['low']
        
        # Skip if any price is 0 or negative
        if low <= 0 or high <= 0 or current <= 0:
            continue
            
        # Skip if high is less than low (data error)
        if high < low:
            continue
            
        try:
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
        except (ZeroDivisionError, ValueError):
            continue
    
    return pd.DataFrame(opportunities).sort_values('Profit', key=lambda x: x.str.replace('%', '').astype(float), ascending=False)

# Main UI
st.title("Binance USDT Tracker")
st.markdown("**WebSocket-only real-time streaming**")

# Connection controls
col1, col2 = st.columns(2)

with col1:
    if st.button("Start WebSocket", type="primary", disabled=st.session_state.ws_connected):
        start_websocket()

with col2:
    if st.button("Stop WebSocket", disabled=not st.session_state.ws_connected):
        stop_websocket()

# Connection status with better feedback
status = st.session_state.connection_status
if status == "connected":
    st.success("🟢 Live data streaming")
elif status == "connecting" or status == "starting":
    st.info("🟡 Connecting to WebSocket...")
elif status == "stopping":
    st.info("🟡 Disconnecting...")
elif status.startswith("error"):
    st.error(f"🔴 Connection error: {status}")
else:
    st.error("🔴 WebSocket disconnected")

# Status display
if st.session_state.last_update:
    age = datetime.now() - st.session_state.last_update
    age_seconds = int(age.total_seconds())
    st.info(f"📊 Last update: {age_seconds}s ago | {len(st.session_state.ticker_data)} USDT pairs")
else:
    st.info("💡 Click 'Start WebSocket' to begin streaming")

# Auto-refresh only if connected and has data
if st.session_state.ws_connected and st.session_state.ticker_data:
    # Use a much shorter sleep and only refresh if there's new data
    placeholder = st.empty()
    with placeholder.container():
        st.text("🔄 Auto-refreshing... (live data)")
    
    # Non-blocking refresh
    if st.session_state.last_update:
        age = datetime.now() - st.session_state.last_update
        if age.total_seconds() < 30:  # Only auto-refresh if data is fresh
            time.sleep(1)
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

# Manual refresh button
if st.session_state.ws_connected:
    if st.button("🔄 Refresh Display"):
        st.rerun()

st.markdown("---")
st.markdown("*WebSocket-only streaming with improved connection handling*")
