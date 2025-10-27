# web/app.py
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd

from .model import list_symbols, infer_one_symbol

app = FastAPI(title="Stock Forecast API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đọc dữ liệu đã tiền xử lý
DATA_PATH = Path(__file__).parent.parent / "dataset" / "preprocessed_data.csv"
DF_RAW = pd.read_csv(DATA_PATH, parse_dates=["time"])


# ---------- API ----------
@app.get("/symbols")
def symbols():
    return list_symbols(DF_RAW)


@app.get("/infer")
def infer(
    symbol: str = Query(...), backtest_days: int = 60, lookback_hist_plot: int = 120
):
    return infer_one_symbol(
        DF_RAW,
        symbol=symbol,
        backtest_days=backtest_days,
        lookback_hist_plot=lookback_hist_plot,
    )


# ---------- Static (phục vụ index.html, app.js, style.css) ----------
STATIC_DIR = Path(__file__).parent
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
