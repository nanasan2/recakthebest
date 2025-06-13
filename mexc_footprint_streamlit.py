import streamlit as st
import asyncio
import websockets
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# ---- Streamlit UI ----
st.set_page_config(page_title="MEXC Footprint Chart", layout="wide")
st.title("📊 Real-Time MEXC 1-Minute Footprint Chart")
status = st.empty()
chart = st.empty()

# ---- Variables ----
symbol = "BTC_USDT"
trade_url = f"wss://wbs.mexc.com/ws"

# ---- Data Storage ----
footprints = []

# ---- Footprint Aggregation ----
def aggregate_footprints(trades):
    df = pd.DataFrame(trades)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    grouped = df.groupby(pd.Grouper(freq='1Min')).agg({
        'price': 'last',
        'quantity': 'sum',
        'side': lambda x: (x == 'buy').sum() - (x == 'sell').sum()
    }).dropna()

    return grouped

# ---- Plotting ----
def plot_footprint(df):
    fig, ax = plt.subplots(figsize=(10, 4))
    df['quantity'].plot(kind='bar', ax=ax, color='skyblue', alpha=0.8)
    ax.set_title('1-Minute Volume Footprint')
    ax.set_ylabel('Volume')
    ax.set_xlabel('Time')
    ax.grid(True)
    plt.xticks(rotation=45)
    st.pyplot(fig)

# ---- WebSocket Handling ----
async def stream_trades():
    status.info("🔌 Connecting to MEXC WebSocket...")
    try:
        async with websockets.connect(trade_url) as ws:
            subscribe_msg = {
                "method": "SUBSCRIPTION",
                "params": [f"spot@public.deals.v3.api@{symbol}"],
                "id": 1
            }
            await ws.send(json.dumps(subscribe_msg))
            trades = []

            while True:
                message = await ws.recv()
                data = json.loads(message)
                deals = data.get("data", {}).get("deals", [])

                for deal in deals:
                    trades.append({
                        "timestamp": int(deal["t"]),
                        "price": float(deal["p"]),
                        "quantity": float(deal["v"]),
                        "side": "buy" if deal["S"] == "BUY" else "sell"
                    })

                if len(trades) >= 30:  # every ~30 trades, update
                    df = aggregate_footprints(trades)
                    if not df.empty:
                        chart.empty()
                        chart.info("📈 Updating chart...")
                        plot_footprint(df)
                    trades.clear()
    except Exception as e:
        status.error(f"❌ Error: {e}")

# ---- Run App ----
asyncio.run(stream_trades())
