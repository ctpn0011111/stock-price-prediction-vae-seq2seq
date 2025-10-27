# web/model.py
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras import backend as K
from tensorflow.keras.models import load_model

# ---------- ĐƯỜNG DẪN ----------
THIS_DIR = Path(__file__).parent
BEST_DIR = THIS_DIR / "best_model"
CFG_PATH = BEST_DIR / "config.json"
SCL_PATH = BEST_DIR / "x_scaler.pkl"
KERAS_BEST = BEST_DIR / "best_vae.keras"
KERAS_FINAL = BEST_DIR / "final_vae.keras"


# ---------- LAYERS TUỲ BIẾN ----------
class Sampling(layers.Layer):
    def call(self, inputs):
        mu, logvar = inputs
        eps = tf.random.normal(shape=K.shape(mu))
        return mu + K.exp(0.5 * logvar) * eps


class KLDivergenceLayer(layers.Layer):
    def __init__(self, beta=0.5, **kwargs):
        super().__init__(**kwargs)
        self.beta = beta

    def call(self, inputs):
        mu, logvar = inputs
        kl_per = -0.5 * K.sum(1 + logvar - K.square(mu) - K.exp(logvar), axis=1)
        self.add_loss(self.beta * K.mean(kl_per))
        return inputs


# ---------- NẠP ARTIFACTS ----------
if (
    not CFG_PATH.exists()
    or not SCL_PATH.exists()
    or not (KERAS_BEST.exists() or KERAS_FINAL.exists())
):
    raise FileNotFoundError(
        f"Thiếu artifacts trong {BEST_DIR}. Cần config.json, x_scaler.pkl và best_vae.keras (hoặc final_vae.keras)."
    )

with CFG_PATH.open("r") as f:
    CONFIG = json.load(f)
SCALER = joblib.load(SCL_PATH)
MODEL_PATH = KERAS_BEST if KERAS_BEST.exists() else KERAS_FINAL
VAE = load_model(
    MODEL_PATH,
    custom_objects={"Sampling": Sampling, "KLDivergenceLayer": KLDivergenceLayer},
    compile=False,
)

W = int(CONFIG.get("W", 90))
H = int(CONFIG.get("H", 7))
TARGET_COL = CONFIG.get("TARGET_COL", "close")
FEATURE_COLS = CONFIG.get("feature_cols", [])


# ---------- TIỆN ÍCH ----------
def _align_feature_cols(df: pd.DataFrame, feature_cols):
    for c in feature_cols:
        if c not in df.columns:
            df[c] = 0.0
    return df.astype({c: "float32" for c in feature_cols})


def _safe_np(a):
    return np.asarray(a, dtype="float64", order="C")


def list_symbols(df: pd.DataFrame):
    return df["symbol"].dropna().astype(str).str.upper().unique().tolist()


# ---------- INFER 1 SYMBOL ----------
def infer_one_symbol(
    df_raw: pd.DataFrame,
    symbol: str,
    backtest_days: int = 60,
    lookback_hist_plot: int = 120,
):
    # Lọc 1 mã
    dfg = (
        df_raw[df_raw["symbol"].astype(str).str.upper() == symbol.upper()]
        .sort_values("time")
        .reset_index(drop=True)
        .copy()
    )
    if len(dfg) < (W + backtest_days + 1):
        raise ValueError(
            f"{symbol}: cần >= {W + backtest_days + 1} dòng, hiện có {len(dfg)}"
        )

    dfg["time"] = pd.to_datetime(dfg["time"])
    dfg = _align_feature_cols(dfg, FEATURE_COLS)

    # Scale & series
    X_all = SCALER.transform(dfg[FEATURE_COLS].to_numpy(dtype="float32", copy=False))
    prices = _safe_np(dfg[TARGET_COL].to_numpy(copy=False))
    times = pd.to_datetime(dfg["time"])

    # ----- 1) Backtest 1-step stitched -----
    start_bt_idx = len(dfg) - backtest_days
    if start_bt_idx - W < 0:
        start_bt_idx = W

    pred_bt_1step = []
    for t in range(start_bt_idx, len(dfg)):
        s, e = t - W, t
        window = X_all[s:e]  # (W,F)
        pred_rets = VAE.predict(window[np.newaxis], verbose=0)[0, :, 0]
        p0 = float(prices[e - 1])
        p1 = p0 * np.exp(float(pred_rets[0]))  # 1-step
        pred_bt_1step.append(p1)

    pred_bt_1step = _safe_np(pred_bt_1step)
    actual_bt = prices[start_bt_idx:]
    times_bt = times[start_bt_idx:]

    valid = np.isfinite(pred_bt_1step)
    if not np.any(valid):
        raise RuntimeError("Không có dự báo hợp lệ trong vùng backtest.")
    first_valid_pos = int(np.flatnonzero(valid)[0])
    p0 = float(prices[start_bt_idx + first_valid_pos - 1])

    # ----- 2) Metrics -----
    def _safe_div(a, b):
        return a / np.clip(b, 1e-12, None)

    err = pred_bt_1step[valid] - actual_bt[valid]
    rmse = float(np.sqrt(np.mean(err**2)))
    mape = float(np.mean(np.abs(_safe_div(err, actual_bt[valid]))) * 100.0)

    a = np.concatenate([[p0], actual_bt[valid]])
    p = np.concatenate([[p0], pred_bt_1step[valid]])
    da = float(np.mean(np.sign(np.diff(a)) == np.sign(np.diff(p))))
    if len(a) >= 3:
        a_dir = np.sign(np.diff(a))
        p_dir = np.sign(np.diff(p))
        ta = float(np.mean((a_dir[1:] != a_dir[:-1]) == (p_dir[1:] != p_dir[:-1])))
        sda = float(np.mean(np.sign(a[2:] - a[:-2]) == np.sign(p[2:] - p[:-2])))
    else:
        ta, sda = float("nan"), float("nan")

    metrics = {
        "days": int(len(actual_bt[valid])),
        "rmse": rmse,
        "mape": mape,
        "da": da,
        "ta": ta,
        "sda": sda,
    }

    # ----- 3) Forecast H ngày -----
    last_window = X_all[-W:]
    pred_rets_fut = VAE.predict(last_window[np.newaxis], verbose=0)[0, :, 0]
    last_price = float(prices[-1])
    fut_prices = [last_price]
    for r in pred_rets_fut:
        fut_prices.append(fut_prices[-1] * np.exp(float(r)))
    fut_prices = _safe_np(fut_prices[1:])

    if len(times) >= 2:
        freq = times.iloc[-1] - times.iloc[-2]
        if freq <= pd.Timedelta(0):
            freq = pd.Timedelta(days=1)
    else:
        freq = pd.Timedelta(days=1)
    fut_times = [times.iloc[-1] + (i + 1) * freq for i in range(H)]

    # ----- 4) Gói thêm INDICATORS CHO FRONTEND -----
    # cắt cùng vùng backtest để vẽ các chỉ báo song song với actual/pred
    slice_df = dfg.iloc[start_bt_idx:].reset_index(drop=True)

    def _safe_series(col):
        return (
            slice_df[col].to_numpy(dtype="float64", copy=False)
            if col in slice_df.columns
            else np.full(len(slice_df), np.nan, dtype="float64")
        )

    vol = _safe_series("volume")
    ema20 = _safe_series("ema20")
    ema60 = _safe_series("ema60")
    ma10 = _safe_series("ma_10")
    ma20 = _safe_series("ma_20")
    rsi14 = _safe_series("rsi_14")
    macd = _safe_series("macd")
    macds = _safe_series("macd_signal")
    mch = macd - macds

    backtest_df = pd.DataFrame(
        {
            "time": times_bt.values,
            "actual": actual_bt,
            "pred_1step": pred_bt_1step,
            # indicators
            "volume": vol,
            "ema20": ema20,
            "ema60": ema60,
            "ma10": ma10,
            "ma20": ma20,
            "rsi_14": rsi14,
            "macd": macd,
            "macd_signal": macds,
            "macd_hist": mch,
        }
    )

    future_df = pd.DataFrame({"time": fut_times, "pred_price": fut_prices})

    return {
        "backtest_df": backtest_df.to_dict(orient="records"),
        "future_df": future_df.to_dict(orient="records"),
        "metrics_backtest": metrics,
    }
