# Binance USDT Tracker

Real-time cryptocurrency analysis using Binance WebSocket API.

## Features

- Live WebSocket connection to Binance
- Filters USDT trading pairs only
- Calculates profit opportunities:
  - **LD**: % difference from current to low price
  - **HD**: % difference from current to high price  
  - **% Profit**: High-low price margin
- Finds coins with ~8% profit margins
- Lists coins <2% above lowest price
- Real-time data updates

## Files

- `binance_tracker.py` - Main Streamlit application
- `streamlit_requirements.txt` - Dependencies
- `streamlit_procfile` - Railway deployment config

## Local Development

```bash
pip install -r streamlit_requirements.txt
streamlit run binance_tracker.py
```

## Railway Deployment

1. Push to GitHub repository
2. Connect to Railway
3. Railway will detect Procfile and deploy
4. Access at your Railway domain

## Environment Variables

- `PORT` - Set automatically by Railway

## Usage

1. Click "Start Connection" to connect to Binance WebSocket
2. Data will load automatically and refresh in real-time
3. View filtered results in organized tables
4. Use "Sort by" dropdown to organize data

## Data Columns

- **Symbol**: Trading pair (e.g., BTCUSDT)
- **LD**: % above lowest price
- **HD**: % below highest price
- **% Profit**: Potential profit margin