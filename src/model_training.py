# ========= ĐOẠN 1: LOAD MODEL & CHUẨN BỊ DỮ LIỆU =========
# File gợi ý: infer_setup.py

from __future__ import annotations
import os, json, joblib
from typing import Tuple, List, Dict, Any

import numpy as np
import pandas as pd

# TensorFlow / Keras
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras import backend as K
from tensorflow.keras.models import load_model
from metrics_and_backtest import compute_rmse_mape, compute_da, compute_ta, compute_sda
import matplotlib.pyplot as plt


# -----------------------------
# 1) Keras custom layers
# -----------------------------
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


# -----------------------------
# 2) Load mô hình, scaler, config
# -----------------------------
def load_best_artifacts(best_dir: str):
    """
    Nạp best model + scaler + config từ thư mục best_overall (hoặc tương đương).
    Yêu cầu tồn tại:
      - config.json (chứa W, H, TARGET_COL, feature_cols, ...)
      - x_scaler.pkl (sklearn scaler với .transform)
      - best_vae.keras (ưu tiên) hoặc final_vae.keras
    Trả về: (model_vae, scaler, config_dict)
    """
    cfg_path = os.path.join(best_dir, "config.json")
    scl_path = os.path.join(best_dir, "x_scaler.pkl")
    model_path = os.path.join(best_dir, "best_vae.keras")
    if not os.path.exists(model_path):
        model_path = os.path.join(best_dir, "final_vae.keras")

    if not (
        os.path.exists(cfg_path)
        and os.path.exists(scl_path)
        and os.path.exists(model_path)
    ):
        raise FileNotFoundError(
            "Thiếu 1 trong các file bắt buộc: config.json / x_scaler.pkl / best_vae.keras(final_vae.keras)"
        )

    with open(cfg_path, "r") as f:
        config = json.load(f)
    scaler = joblib.load(scl_path)

    vae = load_model(
        model_path,
        custom_objects={"Sampling": Sampling, "KLDivergenceLayer": KLDivergenceLayer},
        compile=False,
    )
    return vae, scaler, config


# -----------------------------
# 3) Hàm tiền xử lý đa mã (dựa đúng code bạn đã gửi)
# -----------------------------
def preprocess_multisymbol_df(
    df_raw: pd.DataFrame, use_symbol_onehot: bool = True, clip_abs: float = 1e12
):
    """
    - Tính chỉ báo theo từng symbol
    - ret = log-return (log(close_{t+1}/close_t))  -> phù hợp exp(r)
    - Làm sạch NaN/±inf (ffill/bfill trong từng symbol), kẹp biên, ép float32
    - (tuỳ chọn) thêm one-hot symbol để mô hình phân biệt mã
    Trả về:
      df: DataFrame đã clean, sort theo (symbol,time)
      feature_cols: danh sách cột đặc trưng (KHÔNG gồm 'ret')
      symbol_onehot_cols: list tên cột one-hot (rỗng nếu use_symbol_onehot=False)
    """
    assert {"symbol", "time", "open", "high", "low", "close", "volume"}.issubset(
        df_raw.columns
    ), "Thiếu cột bắt buộc trong df_raw"

    df = df_raw.copy()
    df["time"] = pd.to_datetime(df["time"])
    df["symbol"] = df["symbol"].astype(str).str.upper()
    df = df.sort_values(["symbol", "time"]).reset_index(drop=True)

    # ---- has_news (nếu có 3 cột probs) ----
    for c in ["p_neg", "p_neu", "p_pos"]:
        if c not in df.columns:
            df[c] = np.nan
    df[["p_neg", "p_neu", "p_pos"]] = (
        df[["p_neg", "p_neu", "p_pos"]]
        .fillna({"p_neg": 0.0, "p_neu": 1.0, "p_pos": 0.0})
        .astype("float32")
    )
    sum_p = df[["p_neg", "p_neu", "p_pos"]].sum(axis=1)
    # has_news = 1 khi bộ xác suất hợp lệ (tổng ~1), (bạn có thể thay logic nếu muốn)
    df["has_news"] = ((sum_p > 0.999) & (sum_p < 1.001)).astype("int32")

    g = df.groupby("symbol", group_keys=False)

    # ---- SMA/EMA ----
    df["ma_5"] = g["close"].transform(lambda s: s.rolling(5).mean())
    df["ema_5"] = g["close"].transform(lambda s: s.ewm(span=5, adjust=False).mean())
    df["ma_10"] = g["close"].transform(lambda s: s.rolling(10).mean())
    df["ema_10"] = g["close"].transform(lambda s: s.ewm(span=10, adjust=False).mean())
    df["ma_20"] = g["close"].transform(lambda s: s.rolling(20).mean())
    df["ema_20"] = g["close"].transform(lambda s: s.ewm(span=20, adjust=False).mean())

    # ---- RSI(14) ----
    def rsi_sma(series, period=14):
        delta = series.diff()
        gain = delta.clip(lower=0.0)
        loss = (-delta).clip(lower=0.0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    df["rsi_14"] = g["close"].transform(lambda s: rsi_sma(s, 14))

    # ---- Pct-change (thập phân) ----
    for c in ["open", "high", "low", "close", "volume"]:
        df[f"{c}_pct"] = g[c].transform(lambda s: s.pct_change())

    # ---- MACD (12,26,9) ----
    ema12 = g["close"].transform(lambda s: s.ewm(span=12, adjust=False).mean())
    ema26 = g["close"].transform(lambda s: s.ewm(span=26, adjust=False).mean())
    df["macd"] = ema12 - ema26
    df["macd_signal"] = g["macd"].transform(
        lambda s: s.ewm(span=9, adjust=False).mean()
    )

    # ---- ATR(14) theo True Range ----
    g = df.groupby("symbol", group_keys=False)
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - g["close"].shift()).abs()
    low_close = (df["low"] - g["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["true_range"] = true_range
    df["atr_14"] = df.groupby("symbol", group_keys=False)["true_range"].transform(
        lambda s: s.rolling(14).mean()
    )
    df.drop(columns=["true_range"], inplace=True)

    # ---- TARGET: log-return phù hợp exp(r) ----
    # r_t = log(close_{t+1}/close_t)
    df["ret"] = g["close"].transform(lambda s: np.log(s.shift(-1) / s))

    # ---- Làm sạch, ép kiểu ----
    feature_cols = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "ma_5",
        "ema_5",
        "ma_10",
        "ema_10",
        "ma_20",
        "ema_20",
        "rsi_14",
        "open_pct",
        "high_pct",
        "low_pct",
        "close_pct",
        "volume_pct",
        "macd",
        "macd_signal",
        "atr_14",
        "has_news",
    ]
    clean_cols = feature_cols + ["ret"]
    df[clean_cols] = df[clean_cols].replace([np.inf, -np.inf], np.nan)

    def _ffill_bfill_block(block: pd.DataFrame):
        return block.bfill().ffill()

    df[clean_cols] = df.groupby("symbol", group_keys=False)[clean_cols].apply(
        _ffill_bfill_block
    )
    df[clean_cols] = df[clean_cols].fillna(0.0)
    df[clean_cols] = df[clean_cols].clip(lower=-clip_abs, upper=clip_abs)
    df[clean_cols] = df[clean_cols].astype("float32")

    # ---- Bỏ dòng cuối mỗi symbol (ret NaN trước khi fill) ----
    last_idx_each = df.groupby("symbol", group_keys=False).tail(1).index
    df = df.drop(index=last_idx_each).reset_index(drop=True)

    # ---- One-hot symbol (tuỳ chọn) ----
    symbol_onehot_cols: List[str] = []
    if use_symbol_onehot:
        sym_ohe = pd.get_dummies(df["symbol"], prefix="sym", dtype="float32")
        symbol_onehot_cols = list(sym_ohe.columns)
        df = pd.concat([df, sym_ohe], axis=1)
        feature_cols = feature_cols + symbol_onehot_cols

    # Guard hữu hạn
    X_check = df[feature_cols].to_numpy()
    y_check = df["ret"].to_numpy()
    assert (
        np.isfinite(X_check).all() and np.isfinite(y_check).all()
    ), "Non-finite after cleaning."

    return df, feature_cols, symbol_onehot_cols


# -----------------------------
# 4) Căn đặc trưng theo config lúc train
# -----------------------------
def align_features_for_infer(df_clean: pd.DataFrame, config: Dict[str, Any]):
    """
    Đảm bảo df_clean có đủ và đúng thứ tự cột trong config['feature_cols'].
    Nếu thiếu cột (ví dụ one-hot symbol không xuất hiện ở batch hiện tại) thì thêm cột=0.0
    """
    feature_cols = config["feature_cols"]
    for c in feature_cols:
        if c not in df_clean.columns:
            df_clean[c] = 0.0
    df_clean[feature_cols] = df_clean[feature_cols].astype("float32")
    return df_clean, feature_cols


# -----------------------------
# 5) Hàm tiện ích: Chuẩn bị dữ liệu suy luận
# -----------------------------
def prepare_infer_data(
    df_raw: pd.DataFrame, best_dir: str, use_symbol_onehot: bool = True
):
    """
    - Load vae, scaler, config từ best_dir
    - Preprocess df_raw theo preprocess_multisymbol_df
    - Align cột đặc trưng theo config['feature_cols']
    - Scale X
    Trả về: (vae, scaler, config, df_clean, feature_cols, X_scaled)
    """
    vae, scaler, config = load_best_artifacts(best_dir)
    # kiểm tra khóa bắt buộc trong config
    for k in ["W", "H", "TARGET_COL", "feature_cols"]:
        if k not in config:
            raise KeyError(f"config.json thiếu khóa bắt buộc: {k}")

    df_clean, feat_cols_generated, _ = preprocess_multisymbol_df(
        df_raw, use_symbol_onehot=use_symbol_onehot
    )
    # align theo đúng feature_cols lúc train
    df_aligned, feature_cols = align_features_for_infer(df_clean, config)

    # scale
    X_scaled = scaler.transform(
        df_aligned[feature_cols].to_numpy(dtype="float32", copy=False)
    )

    return vae, scaler, config, df_aligned, feature_cols, X_scaled


def infer_backtest_and_future_symbol(
    df_raw: pd.DataFrame,
    symbol: str,
    best_dir: str,
    preprocess_fn,
    lookback_hist_plot: int = 120,  # số ngày lịch sử để vẽ
    backtest_days: int = 60,  # số ngày dùng để backtest stitched
):
    """
    Walk-forward backtest 1-step (stitched) trên 'backtest_days' ngày cuối của 1 symbol,
    sau đó forecast H ngày tương lai. Trả về:
      - backtest_df: time, actual, pred_1step
      - future_df: time, pred_price
      - metrics_backtest: {days, rmse, mape, da, ta, sda}
    Yêu cầu tồn tại các hàm:
      load_best_artifacts, align_features_for_infer,
      compute_rmse_mape, compute_da, compute_ta, compute_sda.
    """

    # 1) Nạp artifacts & config từ thư mục best
    vae, scaler, config = load_best_artifacts(best_dir)
    W = int(config.get("W", 90))
    H = int(config.get("H", 7))
    TARGET_COL = config.get("TARGET_COL", "close")

    # 2) Tiền xử lý giống lúc train
    #    (hàm preprocess_fn do bạn truyền vào, ví dụ: preprocess_multisymbol_df)
    df_clean, _, _ = preprocess_fn(df_raw, use_symbol_onehot=True)
    df_clean, feature_cols = align_features_for_infer(df_clean, config)

    # 3) Lọc 1 symbol & kiểm tra độ dài
    dfg = (
        df_clean[df_clean["symbol"] == symbol]
        .sort_values("time")
        .reset_index(drop=True)
        .copy()
    )
    if len(dfg) < (W + backtest_days + 1):
        raise ValueError(
            f"{symbol}: cần >= {W + backtest_days + 1} dòng, hiện có {len(dfg)}"
        )

    # 4) Scale toàn bộ đặc trưng của symbol
    X_all = scaler.transform(dfg[feature_cols].to_numpy(dtype="float32", copy=False))
    prices = dfg[TARGET_COL].to_numpy(dtype="float64", copy=False)
    times = pd.to_datetime(dfg["time"])

    # 5) Xác định vùng backtest: chuỗi dự báo 1-step stitched cho 'backtest_days' ngày cuối
    start_bt_idx = len(dfg) - backtest_days
    if start_bt_idx - W < 0:
        start_bt_idx = W  # đảm bảo đủ cửa sổ W trước ngày dự báo đầu tiên

    pred_bt_1step = []
    for t in range(start_bt_idx, len(dfg)):
        s = t - W
        e = t  # dự báo cho ngày index t dựa vào cửa sổ kết thúc ở t-1
        window = X_all[s:e]  # (W, F)
        # Dự báo H bước log-return; lấy bước 1 ngày tới để stitch
        pred_rets = vae.predict(window[np.newaxis], verbose=0)[0, :, 0]
        p0 = float(prices[e - 1])
        p1 = p0 * np.exp(float(pred_rets[0]))  # chuyển log-return -> giá
        pred_bt_1step.append(p1)

    pred_bt_1step = np.asarray(pred_bt_1step, dtype="float64")
    actual_bt = prices[start_bt_idx:]
    times_bt = times[start_bt_idx:]

    # 6) Metrics trên backtest
    valid = np.isfinite(pred_bt_1step)
    if not np.any(valid):
        raise RuntimeError("Không có dự báo hợp lệ trong vùng backtest.")
    first_valid_pos = int(np.flatnonzero(valid)[0])
    # p0: giá ngay trước điểm so sánh đầu tiên
    p0 = float(prices[start_bt_idx + first_valid_pos - 1])

    actual_eval = actual_bt[valid]
    pred_eval = pred_bt_1step[valid]

    rmse_bt, mape_bt = compute_rmse_mape(actual_eval, pred_eval)
    da_bt = compute_da(actual_eval, pred_eval, p0=p0)
    ta_bt = compute_ta(actual_eval, pred_eval, p0=p0)
    sda_bt = compute_sda(actual_eval, pred_eval, p0=p0)

    metrics = {
        "days": int(len(actual_eval)),
        "rmse": float(rmse_bt),
        "mape": float(mape_bt),
        "da": float(da_bt),
        "ta": float(ta_bt),
        "sda": float(sda_bt),
    }

    # 7) Forecast H ngày tương lai từ điểm cuối
    last_window = X_all[-W:]  # (W, F)
    pred_rets_fut = vae.predict(last_window[np.newaxis], verbose=0)[0, :, 0]
    last_price = float(prices[-1])

    pred_future = [last_price]
    for r in pred_rets_fut:
        pred_future.append(pred_future[-1] * np.exp(float(r)))
    pred_future = np.array(pred_future[1:], dtype="float64")  # (H,)

    # thời gian tương lai (ước lượng theo tần suất 2 điểm cuối)
    if len(times) >= 2:
        freq = times.iloc[-1] - times.iloc[-2]
        if freq <= pd.Timedelta(0):
            freq = pd.Timedelta(days=1)
    else:
        freq = pd.Timedelta(days=1)
    fut_times = [times.iloc[-1] + (i + 1) * freq for i in range(H)]

    # 8) Vẽ biểu đồ: lịch sử + 1-step stitched + forecast H ngày
    hist_start = max(0, len(dfg) - lookback_hist_plot)
    plt.figure(figsize=(11, 4.5))
    # Lịch sử
    plt.plot(times.iloc[hist_start:], prices[hist_start:], label="Actual (history)")
    # Backtest 1-step stitched
    plt.plot(
        times_bt[valid],
        pred_bt_1step[valid],
        linestyle="--",
        label=f"1-step stitched (last {metrics['days']}d)",
    )
    # Điểm cuối + Forecast
    plt.scatter([times.iloc[-1]], [last_price], s=30, label="Last observed", zorder=3)
    plt.plot(fut_times, pred_future, linestyle="--", label=f"Forecast +{H}")

    plt.title(f"{symbol} | Walk-forward backtest + {H}-step forecast (W={W})")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend(loc="upper left")
    metrics_txt = (
        f"Backtest({metrics['days']}d)  RMSE={metrics['rmse']:.2f} | "
        f"MAPE={metrics['mape']:.2f}% | DA={metrics['da']:.2f} | "
        f"TA={metrics['ta']:.2f} | SDA={metrics['sda']:.2f}"
    )
    plt.gcf().text(
        0.01,
        0.01,
        metrics_txt,
        fontsize=9,
        ha="left",
        va="bottom",
        bbox=dict(boxstyle="round", fc="w", ec="0.7"),
    )
    plt.tight_layout()
    plt.show()

    # 9) Kết quả trả về
    df_bt = pd.DataFrame(
        {"time": times_bt.values, "actual": actual_bt, "pred_1step": pred_bt_1step}
    )
    df_fut = pd.DataFrame({"time": fut_times, "pred_price": pred_future})
    return {"backtest_df": df_bt, "future_df": df_fut, "metrics_backtest": metrics}


# -----------------------------
# 6) Ví dụ sử dụng (comment minh họa)
# -----------------------------
if __name__ == "__main__":
    # Ví dụ: df_raw là DataFrame đã có các cột:
    # ['time','open','high','low','close','volume','symbol', (tuỳ chọn) p_neg,p_neu,p_pos]
    # df_raw = pd.read_csv("your_data.csv")

    BEST_DIR = "/home/namphuong/course_materials/web/web/best_model"

    # Chuẩn bị dữ liệu suy luận
    # vae, scaler, config, df_clean, feature_cols, X_scaled = prepare_infer_data(df_raw, BEST_DIR)

    # Sau bước này, bạn có thể dùng:
    #   - X_scaled để tạo cửa sổ (W,F) và ra dự báo với vae.predict(...)
    # Hoặc chuyển ngay sang **Đoạn 2** (vẽ & backtest) bạn đã có.
    pass
