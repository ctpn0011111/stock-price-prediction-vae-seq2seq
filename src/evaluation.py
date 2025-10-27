# evaluation.py
import os
import pandas as pd
import numpy as np

# Dùng backend không cần GUI (tránh popup cửa sổ)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os, warnings

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # tắt log của TensorFlow

# Tắt tất cả cảnh báo
warnings.filterwarnings("ignore")

# ==== IMPORT từ Đoạn 1 ====
from model_training import (
    prepare_infer_data,  # (không dùng trực tiếp ở đây nhưng giữ import nếu bạn cần nơi khác)
    infer_backtest_and_future_symbol,  # sinh dự báo 1 mã + dict kết quả
    preprocess_multisymbol_df,  # preprocess multisymbol bạn đã viết
)


# ===================== CÁC HÀM VẼ =====================
def _metrics_text(m):
    return f"Backtest({m['days']}d)  RMSE={m['rmse']:.2f} | MAPE={m['mape']:.2f}%"


def plot_backtest_forecast_for_symbol(
    df_raw,
    symbol,
    result,
    target_col="close",
    lookback_hist_plot=120,
    W=90,
    H=7,
    save_path=None,
    show=False,  # mặc định không hiện
):
    """
    Vẽ biểu đồ: history + backtest 1-step stitched + forecast H ngày.
    'result' là output từ infer_backtest_and_future_symbol(...)
    """
    # --- dữ liệu lịch sử để vẽ phần "Actual (history)" ---
    dfg = (
        df_raw[df_raw["symbol"] == symbol]
        .sort_values("time")
        .reset_index(drop=True)
        .copy()
    )
    dfg["time"] = pd.to_datetime(dfg["time"])
    prices = dfg[target_col].to_numpy(dtype="float64", copy=False)
    times = dfg["time"]

    hist_start = max(0, len(dfg) - lookback_hist_plot)

    # --- lấy backtest & forecast từ result ---
    bt = result["backtest_df"].copy()
    fut = result["future_df"].copy()
    m = result["metrics_backtest"]

    # --- vẽ ---
    fig = plt.figure(figsize=(11, 4.5))

    # history
    plt.plot(times.iloc[hist_start:], prices[hist_start:], label="Actual (history)")

    # 1-step stitched (backtest)
    bt = bt.dropna(subset=["pred_1step"])
    plt.plot(
        pd.to_datetime(bt["time"]),
        bt["pred_1step"],
        linestyle="--",
        label=f"1-step stitched (last {m['days']}d)",
    )

    # last observed
    plt.scatter([times.iloc[-1]], [prices[-1]], s=30, label="Last observed", zorder=3)

    # forecast +H
    plt.plot(
        pd.to_datetime(fut["time"]),
        fut["pred_price"],
        linestyle="--",
        label=f"Forecast +{H}",
    )

    plt.title(f"{symbol} | Walk-forward backtest + {H}-step forecast (W={W})")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend(loc="upper left")

    # metrics box
    plt.gcf().text(
        0.01,
        0.01,
        _metrics_text(m),
        fontsize=9,
        ha="left",
        va="bottom",
        bbox=dict(boxstyle="round", fc="w", ec="0.7"),
    )

    plt.tight_layout()

    # Lưu và đóng
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)


def plot_all_symbols_grid(
    df_raw,
    results_dict,
    symbols=None,
    target_col="close",
    lookback_hist_plot=120,
    W=90,
    H=7,
    save_path=None,
    show=False,  # thêm tham số show
):
    """
    Vẽ lưới 3x3 (tối đa 9 mã) – phiên bản gọn để xem nhanh.
    """
    if symbols is None:
        symbols = list(results_dict.keys())
    symbols = symbols[:9]

    n = len(symbols)
    if n == 0:
        return

    rows = int(np.ceil(n / 3))
    fig, axes = plt.subplots(rows, 3, figsize=(18, 4.8 * rows), squeeze=False)
    axes = axes.flatten()

    for i, sym in enumerate(symbols):
        ax = axes[i]
        dfg = df_raw[df_raw["symbol"] == sym].sort_values("time").copy()
        dfg["time"] = pd.to_datetime(dfg["time"])
        p = dfg[target_col].to_numpy(dtype="float64", copy=False)
        t = dfg["time"]
        s = max(0, len(dfg) - lookback_hist_plot)

        ax.plot(t.iloc[s:], p[s:], label="Actual", linewidth=1.0)

        res = results_dict[sym]
        bt, fut, m = (
            res["backtest_df"].copy(),
            res["future_df"].copy(),
            res["metrics_backtest"],
        )

        bt = bt.dropna(subset=["pred_1step"])
        ax.plot(
            pd.to_datetime(bt["time"]),
            bt["pred_1step"],
            linestyle="--",
            linewidth=1.0,
            label="1-step",
        )
        ax.scatter([t.iloc[-1]], [p[-1]], s=18)
        ax.plot(
            pd.to_datetime(fut["time"]),
            fut["pred_price"],
            linestyle="--",
            linewidth=1.0,
            label=f"+{H}",
        )

        ax.set_title(f"{sym} | RMSE={m['rmse']:.2f}, MAPE={m['mape']:.2f}%")
        ax.tick_params(axis="x", rotation=0)

    # ẩn các ô thừa
    for j in range(i + 1, rows * 3):
        axes[j].axis("off")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=6)
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    # Lưu và đóng
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)


# ===================== PIPELINE CHẠY & LƯU =====================
def run_evaluation_and_save(
    df_raw: pd.DataFrame,
    best_dir: str,
    save_dir: str = "./charts_backtest_forecast",
    backtest_days: int = 60,
    lookback_hist_plot: int = 120,
    target_col: str = "close",
    W: int = 90,
    H: int = 7,
    save_metrics_csv: bool = True,
):
    """
    Chạy infer cho TẤT CẢ mã, lưu hình từng mã + grid, và (tuỳ chọn) lưu metrics CSV.
    """
    os.makedirs(save_dir, exist_ok=True)

    symbols = df_raw["symbol"].dropna().unique().tolist()
    results = {}
    rows = []

    for sym in symbols:
        try:
            out = infer_backtest_and_future_symbol(
                df_raw=df_raw,
                symbol=sym,
                best_dir=best_dir,
                preprocess_fn=preprocess_multisymbol_df,
                lookback_hist_plot=lookback_hist_plot,
                backtest_days=backtest_days,
            )
            results[sym] = out
            m = out["metrics_backtest"]
            rows.append({"symbol": sym, **m})

            # Lưu hình từng mã
            save_path = os.path.join(save_dir, f"{sym}.png")
            # H thực tế có thể lấy theo out["future_df"].shape[0]
            H_sym = int(out["future_df"].shape[0]) if "future_df" in out else int(H)
            plot_backtest_forecast_for_symbol(
                df_raw=df_raw,
                symbol=sym,
                result=out,
                target_col=target_col,
                lookback_hist_plot=lookback_hist_plot,
                W=int(W),
                H=H_sym,
                save_path=save_path,
                show=False,
            )
        except Exception as e:
            print(f"[ERROR] {sym}: {e}")

    # Lưu metrics
    metrics_path = None
    if rows and save_metrics_csv:
        metrics_df = pd.DataFrame(rows).sort_values("rmse").reset_index(drop=True)
        metrics_path = os.path.join(save_dir, "metrics_backtest_all_symbols.csv")
        metrics_df.to_csv(metrics_path, index=False)
        print(f"Đã lưu metrics: {os.path.abspath(metrics_path)}")

    # Lưu grid 9 mã đầu (nếu có kết quả)
    if results:
        # Suy ra H mặc định từ 1 kết quả đầu
        any_sym = next(iter(results.keys()))
        H_any = (
            int(results[any_sym]["future_df"].shape[0])
            if "future_df" in results[any_sym]
            else int(H)
        )

        grid_path = os.path.join(save_dir, "grid_9_symbols.png")
        plot_all_symbols_grid(
            df_raw=df_raw,
            results_dict=results,
            symbols=symbols[:9],
            target_col=target_col,
            lookback_hist_plot=lookback_hist_plot,
            W=int(W),
            H=H_any,
            save_path=grid_path,
            show=False,
        )
        print(f"Đã lưu grid: {os.path.abspath(grid_path)}")
    else:
        print("[WARN] Không có kết quả nào được tạo.")

    print(f"Đã lưu toàn bộ hình vào: {os.path.abspath(save_dir)}")
    return results


# ===================== CHẠY ĐÁNH GIÁ & LƯU =====================
if __name__ == "__main__":
    # Đường dẫn model
    BEST_DIR = "/home/namphuong/course_materials/web/web/best_model"

    # Dữ liệu đã tiền xử lý (hoặc raw cũng được – preprocess sẽ chạy lại)
    df_raw = pd.read_csv(
        "/home/namphuong/course_materials/web/dataset/preprocessed_data.csv"
    )
    df_raw["time"] = pd.to_datetime(df_raw["time"])

    # Thư mục lưu output
    SAVE_DIR = "./charts_backtest_forecast"

    # Tham số
    BACKTEST_DAYS = 60
    LOOKBACK_HIST_PLOT = 120
    TARGET_COL = "close"
    W = 90
    H = 7  # sẽ được suy ra theo từng mã nếu future_df có kích thước khác

    # Chạy
    run_evaluation_and_save(
        df_raw=df_raw,
        best_dir=BEST_DIR,
        save_dir=SAVE_DIR,
        backtest_days=BACKTEST_DAYS,
        lookback_hist_plot=LOOKBACK_HIST_PLOT,
        target_col=TARGET_COL,
        W=W,
        H=H,
        save_metrics_csv=True,
    )
