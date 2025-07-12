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

# Global variables
ticker_data = {}
ws_connected = False
ws_thread = None
stop_ws = False

# Initialize session state
if 'ticker_data' not in st.session_state:
    st.session_state.ticker_data = {}
if 'ws_connected' not in st.session_state:
    st.session_state.ws_connected = False
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

def process_ticker_data(data):
    """Process incoming ticker data"""
    global ticker_data
    
    if isinstance(data, list):
        for item in data:
            if 's' in item and item['s'].endswith('USDT'):
                ticker_data[item['s']] = {
                    'current': float(item['c']),
                    'high': float(item['h']),
                    'low': float(item['l']),
                    'change': float(item['P'])
                }
    
    # Update session state
    st.session_state.ticker_data = ticker_data.copy()
    st.session_state.last_update = datetime.now()

async def websocket_client():
    """WebSocket client for Binance stream"""
    global ws_connected, stop_ws
    
    uri = "wss://stream.binance.com:9443/ws/!ticker@arr"
    
    try:
        async with websockets.connect(uri) as websocket:
            ws_connected = True
            st.session_state.ws_connected = True
            
            while not stop_ws:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    process_ticker_data(data)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    st.error(f"WebSocket error: {e}")
                    break
                    
    except Exception as e:
        st.error(f"Connection error: {e}")
    finally:
        ws_connected = False
        st.session_state.ws_connected = False

def start_websocket():
    """Start WebSocket connection in thread"""
    global ws_thread, stop_ws
    
    stop_ws = False
    
    def run_websocket():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(websocket_client())
        loop.close()
    
    ws_thread = threading.Thread(target=run_websocket)
    ws_thread.daemon = True
    ws_thread.start()

def stop_websocket():
    """Stop WebSocket connection"""
    global stop_ws, ws_connected
    stop_ws = True
    ws_connected = False
    st.session_state.ws_connected = False

def calculate_opportunities():
    """Calculate profit opportunities"""
    if not st.session_state.ticker_data:
        return pd.DataFrame()
    
    opportunities = []
    for symbol, data in st.session_state.ticker_data.items():
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
st.markdown("**Real-time WebSocket streaming**")

# Connection controls
col1, col2 = st.columns(2)

with col1:
    if st.button("🔗 Start WebSocket", type="primary"):
        start_websocket()
        st.success("WebSocket connection started!")
        time.sleep(2)
        st.rerun()

with col2:
    if st.button("🔌 Stop WebSocket"):
        stop_websocket()
        st.success("WebSocket connection stopped!")
        st.rerun()

# Connection status
if st.session_state.ws_connected:
    st.success("🟢 WebSocket Connected - Live data streaming")
else:
    st.error("🔴 WebSocket Disconnected")

# Status display
if st.session_state.last_update:
    age = datetime.now() - st.session_state.last_update
    age_seconds = int(age.total_seconds())
    st.info(f"Last update: {age_seconds}s ago | Tracking {len(st.session_state.ticker_data)} USDT pairs")
else:
    st.info("Click 'Start WebSocket' to begin live data streaming")

# Auto-refresh for live updates
if st.session_state.ws_connected:
    time.sleep(2)
    st.rerun()

# Results
if st.session_state.ticker_data:
    st.subheader("Profit Opportunities")
    st.text("Coins with ~8% profit margin and <2% above low price")
    
    df = calculate_opportunities()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success(f"Found {len(df)} opportunities!")
    else:
        st.info("No opportunities match criteria")
    
    # Show total pairs
    st.metric("Total USDT Pairs", len(st.session_state.ticker_data))

st.markdown("---")
st.markdown("*Real-time WebSocket streaming - No rate limits*")
