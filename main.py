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
if 'stop_ws' not in st.session_state:
    st.session_state.stop_ws = False

def update_ticker_data(data):
    """Update ticker data in session state"""
    if isinstance(data, list):
        ticker_data = {}
        for item in data:
            if 's' in item and item['s'].endswith('USDT'):
                try:
                    ticker_data[item['s']] = {
                        'current': float(item['c']),
                        'high': float(item['h']),
                        'low': float(item['l']),
                        'change': float(item['P'])
                    }
                except (ValueError, KeyError):
                    continue
        
        st.session_state.ticker_data = ticker_data
        st.session_state.last_update = datetime.now()
        st.session_state.ws_connected = True
        st.session_state.connection_status = "connected"

async def websocket_handler():
    """Handle WebSocket connection"""
    uri = "wss://stream.binance.com:9443/ws/!ticker@arr"
    
    try:
        async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as websocket:
            st.session_state.connection_status = "connected"
            st.session_state.ws_connected = True
            
            while not st.session_state.stop_ws:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    update_ticker_data(data)
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    break
                    
    except Exception as e:
        st.session_state.connection_status = f"error: {str(e)[:50]}"
    finally:
        st.session_state.ws_connected = False
        if not st.session_state.stop_ws:
            st.session_state.connection_status = "disconnected"

def start_websocket():
    """Start WebSocket connection"""
    if st.session_state.ws_connected:
        return
    
    st.session_state.stop_ws = False
    st.session_state.connection_status = "connecting"
    
    def run_websocket():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(websocket_handler())
        except Exception as e:
            st.session_state.connection_status = f"failed: {str(e)[:50]}"
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_websocket, daemon=True)
    thread.start()

def stop_websocket():
    """Stop WebSocket connection"""
    st.session_state.stop_ws = True
    st.session_state.ws_connected = False
    st.session_state.connection_status = "disconnected"

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
st.markdown("**WebSocket-only real-time streaming**")

# Connection controls
col1, col2 = st.columns(2)

with col1:
    if st.button("Start WebSocket", type="primary", disabled=st.session_state.ws_connected):
        start_websocket()
        time.sleep(1)
        st.rerun()

with col2:
    if st.button("Stop WebSocket", disabled=not st.session_state.ws_connected):
        stop_websocket()
        st.rerun()

# Connection status
status = st.session_state.connection_status
if status == "connected":
    st.success("🟢 Live data streaming")
elif status == "connecting":
    st.info("🟡 Connecting to WebSocket...")
elif status.startswith("error") or status.startswith("failed"):
    st.error(f"🔴 Connection failed: {status}")
else:
    st.error("🔴 WebSocket disconnected")

# Data status
if st.session_state.last_update:
    age = datetime.now() - st.session_state.last_update
    age_seconds = int(age.total_seconds())
    st.info(f"📊 Last update: {age_seconds}s ago | {len(st.session_state.ticker_data)} USDT pairs")
else:
    st.info("💡 Click 'Start WebSocket' to begin streaming")

# Auto-refresh when connected
if st.session_state.ws_connected:
    time.sleep(2)
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

st.markdown("---")
st.markdown("*WebSocket-only streaming - Fixed connection handling*")
