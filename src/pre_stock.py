# src/preprocessing.py
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import json

DATASET = Path("/home/namphuong/course_materials/web/dataset")
DATA_CSV = DATASET / "data.csv"
JSON_PATH = DATASET / "daily_scores_vi.json"

REQUIRED = ["time", "open", "high", "low", "close", "symbol"]


def _read_json_scores(json_path: str | Path) -> pd.DataFrame:
    json_path = Path(json_path)
    if not json_path.exists():
        return pd.DataFrame(columns=["time", "p_neg", "p_neu", "p_pos"])
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    recs = []
    for t, scores in raw.items():
        neg, neu, pos = (scores + [None, None, None])[:3]
        recs.append({"time": t, "p_neg": neg, "p_neu": neu, "p_pos": pos})
    dfj = pd.DataFrame(recs)
    dfj["time"] = pd.to_datetime(dfj["time"], errors="coerce")
    for c in ["p_neg", "p_neu", "p_pos"]:
        dfj[c] = pd.to_numeric(dfj[c], errors="coerce")
    return dfj


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI (Wilder)."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    # Wilder's smoothing (EMA với adjust=False)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def preprocess_data(
    input_path: str | Path = DATA_CSV,
    json_path: str | Path = JSON_PATH,
    start_date: str | None = "2020-01-01",
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    # ==== 1) CSV ====
    df = pd.read_csv(input_path, low_memory=False)
    # chuẩn tên cột
    df.columns = [c.lower().strip() for c in df.columns]
    if "date" in df.columns and "time" not in df.columns:
        df = df.rename(columns={"date": "time"})
    if "ticker" in df.columns and "symbol" not in df.columns:
        df = df.rename(columns={"ticker": "symbol"})
    if "code" in df.columns and "symbol" not in df.columns:
        df = df.rename(columns={"code": "symbol"})
    # ép kiểu
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()

    # ép numeric cơ bản
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # giữ cột tối thiểu
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Thiếu cột bắt buộc trong CSV: {missing}")

    # ==== 2) JSON ====
    df_json = _read_json_scores(json_path)

    # ==== 3) Merge theo time ====
    df = pd.merge(df, df_json, on="time", how="outer", copy=False)

    # lọc, sắp xếp
    df = df.dropna(subset=["time"])
    df = df[df["symbol"].notna()]
    if start_date:
        start_ts = pd.to_datetime(start_date, errors="coerce")
        if pd.notna(start_ts):
            df = df[df["time"] >= start_ts]
    df = df.sort_values(["symbol", "time"]).drop_duplicates()

    # ==== 4) Sentiment fill + has_news ====
    for c in ["p_neg", "p_neu", "p_pos"]:
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # fill mặc định: neutral
    df[["p_neg", "p_neu", "p_pos"]] = df[["p_neg", "p_neu", "p_pos"]].fillna(
        {"p_neg": 0.0, "p_neu": 1.0, "p_pos": 0.0}
    )
    # cờ has_news: có tin khi phân phối khác (0,1,0)
    probs_sum = df["p_neg"] + df["p_neu"] + df["p_pos"]
    df["has_news"] = np.where(
        (
            np.isclose(df["p_neg"], 0.0)
            & np.isclose(df["p_neu"], 1.0)
            & np.isclose(df["p_pos"], 0.0)
            & np.isclose(probs_sum, 1.0)
        ),
        0,
        1,
    )

    # ==== 5) Feature tính theo từng mã (TRỌNG TÂM BỔ SUNG) ====
    def _feat(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("time")

        # --- Returns cơ bản ---
        g["ret1"] = g["close"].pct_change()
        g["logret"] = np.log(g["close"] / g["close"].shift(1))
        g["ret5"] = g["close"].pct_change(5)
        g["ret20"] = g["close"].pct_change(20)

        # --- EMA gốc (giữ nguyên) ---
        g["ema20"] = g["close"].ewm(span=20, adjust=False).mean()
        g["ema60"] = g["close"].ewm(span=60, adjust=False).mean()
        g["ema20_dist"] = (g["close"] - g["ema20"]) / g["ema20"]
        g["ema60_slope"] = g["ema60"].diff()

        # --- Volatility gốc (giữ nguyên) ---
        g["vol20"] = g["logret"].rolling(20).std()
        # atr14 đơn giản như bản cũ (để tương thích)
        g["atr14"] = (g["high"] - g["low"]).rolling(14).mean()

        # --- Volume Z-score ---
        if "volume" in g.columns:
            mean20 = g["volume"].rolling(20).mean()
            std20 = g["volume"].rolling(20).std()
            g["vol_z20"] = (g["volume"] - mean20) / std20
        else:
            g["vol_z20"] = np.nan

        # --- Sentiment features ---
        g["sent_polarity"] = g["p_pos"] - g["p_neg"]
        g["sent_entropy"] = -(
            g[["p_neg", "p_neu", "p_pos"]]
            * np.log(g[["p_neg", "p_neu", "p_pos"]] + 1e-6)
        ).sum(axis=1)
        g["sent_polarity_ema3"] = g["sent_polarity"].ewm(span=3, adjust=False).mean()
        g["sent_vol_interact"] = g["sent_polarity"] * g["vol_z20"]

        # --- Target (close mượt) – shift -1 để dự báo phiên kế tiếp ---
        g["target"] = g["close"].ewm(span=30, adjust=False).mean().shift(-1)

        # ====== BỔ SUNG CHỈ SỐ BẠN YÊU CẦU ======
        # 1) SMA & EMA 5/10/20
        g["ma_5"] = g["close"].rolling(window=5).mean()
        g["ema_5"] = g["close"].ewm(span=5, adjust=False).mean()

        g["ma_10"] = g["close"].rolling(window=10).mean()
        g["ema_10"] = g["close"].ewm(span=10, adjust=False).mean()

        g["ma_20"] = g["close"].rolling(window=20).mean()
        g["ema_20"] = g["close"].ewm(span=20, adjust=False).mean()  # khác tên với ema20

        # 2) RSI (14)
        g["rsi_14"] = _rsi(g["close"], period=14)

        # 3) Daily return (mặc định theo close; nếu muốn theo open, thay bằng g["open"].pct_change())
        g["ret"] = g["close"].pct_change()

        # 4) % thay đổi theo ngày
        g["open_pct"] = g["open"].pct_change()
        g["high_pct"] = g["high"].pct_change()
        g["low_pct"] = g["low"].pct_change()
        g["close_pct"] = g["close"].pct_change()
        g["volume_pct"] = g["volume"].pct_change() if "volume" in g.columns else np.nan

        # 5) MACD (12, 26, 9)
        ema12 = g["close"].ewm(span=12, adjust=False).mean()
        ema26 = g["close"].ewm(span=26, adjust=False).mean()
        g["macd"] = ema12 - ema26
        g["macd_signal"] = g["macd"].ewm(span=9, adjust=False).mean()

        # 6) ATR (14) theo True Range
        high_low = g["high"] - g["low"]
        high_close = (g["high"] - g["close"].shift()).abs()
        low_close = (g["low"] - g["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        g["atr_14"] = tr.rolling(window=14).mean()

        return g

    df = df.groupby("symbol", group_keys=False).apply(_feat)

    # chuyển inf -> NaN rồi drop các hàng thiếu do rolling/shift
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna().reset_index(drop=True)

    # ==== 6) Lưu (tuỳ chọn) ====
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

    return df


if __name__ == "__main__":
    df_processed = preprocess_data(
        input_path=DATA_CSV,
        json_path=JSON_PATH,
        start_date="2020-01-01",
        output_path=DATASET / "preprocessed_data.csv",
    )
    print(f"Đã tiền xử lý dữ liệu. Kích thước: {df_processed.shape}")
    print(f"File lưu tại: {DATASET / 'preprocessed_data.csv'}")
