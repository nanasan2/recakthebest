import asyncio
import json
import websockets
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

MEXC_WS_URL = "wss://wbs.mexc.com/ws"
symbol = "BTC_USDT"
raw_trades = []

TRADE_WINDOW_MIN = 5

async def get_trades():
    global raw_trades
    async with websockets.connect(MEXC_WS_URL) as ws:
        msg = {
            "method": "SUBSCRIPTION",
            "params": {
                "channels": [f"spot@public.deals.v3.api@{symbol}"]
            }
        }
        await ws.send(json.dumps(msg))
        print(f"Subscribed to {symbol} trades")

        while True:
            res = await ws.recv()
            data = json.loads(res)

            if "data" in data and isinstance(data["data"], list):
                for trade in data["data"]:
                    ts = trade["t"]
                    qty = float(trade["v"])
                    side = trade["S"]
                    raw_trades.append({
                        "minute": datetime.fromtimestamp(ts / 1000).replace(second=0, microsecond=0),
                        "side": side,
                        "qty": qty,
                        "timestamp": datetime.utcnow()
                    })

            # Remove old data
            cutoff = datetime.utcnow() - timedelta(minutes=TRADE_WINDOW_MIN)
            raw_trades = [t for t in raw_trades if t["timestamp"] >= cutoff]

async def stream_data():
    asyncio.create_task(get_trades())
    while True:
        await asyncio.sleep(1)

st.set_page_config(page_title="MEXC Footprint", layout="wide")
st.title("🧭 Real-Time 1-Minute Footprint Chart (MEXC BTC/USDT)")

placeholder = st.empty()

async def update_chart():
    await stream_data()

    while True:
        if raw_trades:
            df = pd.DataFrame(raw_trades)
            grouped = df.groupby(["minute", "side"])["qty"].sum().unstack(fill_value=0)
            grouped = grouped.rename(columns={"BUY": "Buy Volume", "SELL": "Sell Volume"})
            grouped['Delta'] = grouped['Buy Volume'] - grouped['Sell Volume']
            placeholder.bar_chart(grouped[["Buy Volume", "Sell Volume"]])
        await asyncio.sleep(5)

asyncio.run(update_chart())
