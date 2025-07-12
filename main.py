import streamlit as st
import json
import pandas as pd
from datetime import datetime
import asyncio
import websockets
import threading
import time
from contextlib import asynccontextmanager

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
if 'ws_stop_event' not in st.session_state:
    st.session_state.ws_stop_event = threading.Event()

@asynccontextmanager
async def websocket_connection():
    """Context manager for WebSocket connection"""
    uri = "wss://stream.binance.com:9443/ws/!ticker@arr"
    websocket = None
    try:
        websocket = await websockets.connect(uri)
        st.session_state.ws_connected = True
        yield websocket
    except Exception as e:
        st.session_state.ws_connected = False
        raise
    finally:
        if websocket:
            await websocket.close()
        st.session_state.ws_connected = False

def process_ticker_data(data):
    """Process incoming ticker data"""
    usdt_data = {}
    
    if isinstance(data, list):
        for item in data:
            if 's' in item and item['s'].endswith('USDT'):
                try:
                    usdt_data[item['s']] = {
                        'current': float(item['c']),
                        'high': float(item['h']),
                        'low': float(item['l']),
                        'change': float(item['P'])
                    }
                except (ValueError, KeyError):
                    continue
    
    # Update session state
    st.session_state.ticker_data = usdt_data
    st.session_state.last_update = datetime.now()

async def websocket_client():
    """WebSocket client for Binance stream"""
    try:
        async with websocket_connection() as websocket:
            while not st.session_state.ws_stop_event.is_set():
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    process_ticker_data(data)
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    break
    except Exception as e:
        pass

def start_websocket():
    """Start WebSocket connection"""
    st.session_state.ws_stop_event.clear()
    
    def run_websocket():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(websocket_client())
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_websocket, daemon=True)
    thread.start()

def stop_websocket():
    """Stop WebSocket connection"""
    st.session_state.ws_stop_event.set()
    st.session_state.ws_connected = False

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
    
    if opportunities:
        df = pd.DataFrame(opportunities)
        return df.sort_values('Profit', key=lambda x: x.str.replace('%', '').astype(float), ascending=False)
    return pd.DataFrame()

# Main UI
st.title("Binance USDT Tracker")
st.markdown("**WebSocket-only real-time streaming**")

# Connection controls
col1, col2 = st.columns(2)

with col1:
    if st.button("Start WebSocket", type="primary"):
        start_websocket()
        st.success("WebSocket started!")
        time.sleep(1)
        st.rerun()

with col2:
    if st.button("Stop WebSocket"):
        stop_websocket()
        st.success("WebSocket stopped!")
        st.rerun()

# Connection status
if st.session_state.ws_connected:
    st.success("🟢 Live data streaming")
else:
    st.error("🔴 WebSocket disconnected")

# Status display
if st.session_state.last_update:
    age = datetime.now() - st.session_state.last_update
    age_seconds = int(age.total_seconds())
    st.info(f"Last update: {age_seconds}s ago | {len(st.session_state.ticker_data)} USDT pairs")
else:
    st.info("Click 'Start WebSocket' to begin streaming")

# Auto-refresh for live updates
if st.session_state.ws_connected:
    time.sleep(1)
    st.rerun()

# Results
if st.session_state.ticker_data:
    st.subheader("Profit Opportunities")
    st.text("~8% profit margin and <2% above low price")
    
    df = calculate_opportunities()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.success(f"Found {len(df)} opportunities!")
    else:
        st.info("No opportunities match criteria")

st.markdown("---")
st.markdown("*WebSocket-only streaming - Optimized performance*")
