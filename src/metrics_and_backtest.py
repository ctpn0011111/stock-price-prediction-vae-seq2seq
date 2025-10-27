# metrics_and_backtest.py
import numpy as np


def _safe_div(a, b):
    return a / np.clip(b, 1e-12, None)


def compute_rmse_mape(actual_prices, pred_prices):
    err = pred_prices - actual_prices
    rmse = float(np.sqrt(np.mean(err**2)))
    mape = float(np.mean(np.abs(_safe_div(err, actual_prices))) * 100.0)
    return rmse, mape


def compute_da(actual_prices, pred_prices, p0):
    """
    DA: tỷ lệ đúng chiều tăng/giảm theo từng bước.
    p0 = giá quan sát cuối cùng ngay trước horizon (mốc để lấy chênh lệch bước đầu tiên)
    """
    a = np.concatenate([[p0], actual_prices])
    p = np.concatenate([[p0], pred_prices])
    return float(np.mean(np.sign(np.diff(a)) == np.sign(np.diff(p))))


def compute_ta(actual_prices, pred_prices, p0):
    """
    TA: đúng điểm đổi chiều (sign đổi giữa 2 bước liên tiếp).
    Cần >= 3 điểm trong horizon, nếu không trả về NaN.
    """
    a = np.concatenate([[p0], actual_prices])
    p = np.concatenate([[p0], pred_prices])
    if len(a) < 3 or len(p) < 3:
        return float("nan")
    a_dir = np.sign(np.diff(a))
    p_dir = np.sign(np.diff(p))
    a_turn = a_dir[1:] != a_dir[:-1]
    p_turn = p_dir[1:] != p_dir[:-1]
    return float(np.mean(a_turn == p_turn))


def compute_sda(actual_prices, pred_prices, p0):
    """
    SDA (Slope Directional Accuracy):
    So sánh dấu của 'độ dốc' 2-bước: sign(x_{t+1} - x_{t-1}) giữa actual & predicted.
    Cần >= 3 điểm trong horizon, nếu không trả về NaN.
    """
    a = np.concatenate([[p0], actual_prices])
    p = np.concatenate([[p0], pred_prices])
    if len(a) < 3 or len(p) < 3:
        return float("nan")
    a_slope = np.sign(a[2:] - a[:-2])
    p_slope = np.sign(p[2:] - p[:-2])
    return float(np.mean(a_slope == p_slope))


def backtest_multi_symbol(vae, df, feature_cols, scaler, target_col, window, horizon):
    """
    - Với mỗi symbol: lấy cửa sổ (W) ngay TRƯỚC H ngày cuối, dự báo H bước (log-return).
    - Dựng giá bằng exp(r).
    - Tính RMSE, MAPE, DA, TA, SDA cho từng symbol, rồi lấy trung bình.
    """
    rmses, mapes, das, tas, sdas = [], [], [], [], []
    details = {}

    for sym, dfg in df.groupby("symbol"):
        n = len(dfg)
        if n < window + horizon:
            continue

        X_all = scaler.transform(
            dfg[feature_cols].to_numpy(dtype="float32", copy=False)
        )
        bt_window = X_all[-horizon - window : -horizon]  # (W,F)
        if bt_window.shape[0] != window:
            continue

        # dự báo log-return rồi dựng giá
        pred_rets = vae.predict(bt_window[np.newaxis], verbose=0)[0, :, 0]  # (H,)
        start_price = float(dfg[target_col].iloc[-horizon - 1])

        pred_prices = [start_price]
        for r in pred_rets:
            pred_prices.append(pred_prices[-1] * np.exp(float(r)))
        pred_prices = np.asarray(pred_prices[1:], dtype="float64")  # (H,)

        actual_prices = (
            dfg[target_col].iloc[-horizon:].to_numpy(dtype="float64", copy=False)
        )

        rmse, mape = compute_rmse_mape(actual_prices, pred_prices)
        da = compute_da(actual_prices, pred_prices, p0=start_price)
        ta = compute_ta(actual_prices, pred_prices, p0=start_price)
        sda = compute_sda(actual_prices, pred_prices, p0=start_price)

        rmses.append(rmse)
        mapes.append(mape)
        das.append(da)
        tas.append(ta)
        sdas.append(sda)

        details[sym] = {"rmse": rmse, "mape": mape, "da": da, "ta": ta, "sda": sda}

    if len(rmses) == 0:
        return {
            "rmse": np.inf,
            "mape": np.inf,
            "da": np.nan,
            "ta": np.nan,
            "sda": np.nan,
        }, details

    agg = {
        "rmse": float(np.mean(rmses)),
        "mape": float(np.mean(mapes)),
        "da": float(np.mean(das)),
        "ta": float(np.nanmean(tas)),
        "sda": float(np.nanmean(sdas)),
    }
    return agg, details
