#!/usr/bin/env python3
from __future__ import annotations
import argparse
import subprocess
import sys
import os
from pathlib import Path
import importlib
import os, warnings

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")

# ================== CẤU HÌNH ĐƯỜNG DẪN MẶC ĐỊNH ==================
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
DATASET_DIR = BASE_DIR / "dataset"

STOCK_DIR = DATASET_DIR / "stock"
DATA_CSV = DATASET_DIR / "data.csv"  # sau bước 1
JSON_PATH = DATASET_DIR / "daily_scores_vi.json"  # sau bước 5
PREPROCESSED_CSV = (
    DATASET_DIR / "preprocessed_data.csv"
)  # sau bước 3 (+ ghép news nếu code bạn làm ở bước này)

BEST_DIR = BASE_DIR / "web" / "best_model"  # output của training
CHART_DIR = BASE_DIR / "charts_backtest_forecast"  # output của evaluation (nếu có)

# đảm bảo src nằm trong PYTHONPATH
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ================== TIỆN ÍCH CHUNG ==================
def run_py(path: Path, args: list[str] | None = None, env: dict | None = None):
    """Chạy 1 file .py như script. Tự động thêm 'python' hiện tại."""
    cmd = [sys.executable, str(path)]
    if args:
        cmd += args
    print(f"→ RUN: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, env={**os.environ, **(env or {})})


def try_import_attr(module_name: str, attr: str):
    """Import attr (hàm) từ module; trả None nếu không có."""
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, attr)
    except Exception:
        return None


# ================== CÁC BƯỚC PIPELINE ==================
def step_1_load_stock(stock_dir: Path, out_csv: Path):
    """1) Gộp CSV chứng khoán -> data.csv"""
    func = try_import_attr("load_stock", "merge_stock_csvs")
    if func is not None:
        print("==> [1/7] load_stock.merge_stock_csvs()")
        out = func(stock_dir, out_csv)
        print(f"    ✓ Đã gộp -> {out}")
    else:
        print("==> [1/7] Chạy src/load_stock.py (fallback)")
        run_py(
            SRC_DIR / "load_stock.py",
            args=[
                "--stock-dir",
                str(stock_dir),
                "--out-csv",
                str(out_csv),
            ],
        )


def step_2_load_news():
    """2) Tải/ghép news thô (nếu có)"""
    path = SRC_DIR / "load_news.py"
    if path.exists():
        print("==> [2/7] Chạy src/load_news.py")
        run_py(path)
    else:
        print("==> [2/7] Bỏ qua (không có src/load_news.py)")


def step_3_pre_stock(input_csv: Path, json_path: Path, start_date: str, out_csv: Path):
    """3) Tiền xử lý dữ liệu giá (và ghép JSON nếu logic của bạn thực hiện ở đây)"""
    func = try_import_attr("pre_stock", "preprocess_data")
    if func is not None:
        print("==> [3/7] pre_stock.preprocess_data()")
        out_df = func(
            input_path=input_csv,
            json_path=json_path,
            start_date=start_date,
            output_path=out_csv,
        )
        print(f"    ✓ Dòng sau làm sạch: {len(out_df):,}")
        print(f"    ✓ Lưu -> {out_csv}")
    else:
        print("==> [3/7] Chạy src/pre_stock.py (fallback)")
        run_py(SRC_DIR / "pre_stock.py")


def step_4_pre_news():
    """4) Tiền xử lý news thô (nếu có)"""
    path = SRC_DIR / "pre_news.py"
    if path.exists():
        print("==> [4/7] Chạy src/pre_news.py")
        run_py(path)
    else:
        print("==> [4/7] Bỏ qua (không có src/pre_news.py)")


def step_5_model_sentiment(enable: bool, out_json: Path):
    """5) Huấn luyện mô hình sentiment -> daily_scores_vi.json (có thể skip vì lâu)"""
    if not enable:
        print("==> [5/7] Bỏ qua model_sentiment (đặt --skip-sentiment).")
        return

    path = SRC_DIR / "model_sentiment.py"
    if path.exists():
        print("==> [5/7] Chạy src/model_sentiment.py")
        # nếu script của bạn hỗ trợ tham số đầu ra, thêm args vào đây
        run_py(path)
        # đảm bảo file json tồn tại sau khi chạy
        if not out_json.exists():
            print(f"    ⚠️  Không thấy {out_json}. Hãy kiểm tra model_sentiment.py.")
        else:
            print(f"    ✓ Sentiment JSON -> {out_json}")
    else:
        print("==> [5/7] Bỏ qua (không có src/model_sentiment.py)")


def step_6_model_training(best_dir: Path, data_csv: Path):
    """6) Huấn luyện mô hình dự báo (VAE) -> lưu best_model"""
    path = SRC_DIR / "model_training.py"
    if path.exists():
        print("==> [6/7] Chạy src/model_training.py")
        best_dir.mkdir(parents=True, exist_ok=True)
        # Nếu script hỗ trợ tham số, bạn có thể thêm ở đây.
        # Ví dụ: --data & --best-dir. Nếu chưa hỗ trợ, script sẽ dùng đường dẫn mặc định bên trong.
        try:
            run_py(
                path,
                args=[
                    "--data",
                    str(data_csv),
                    "--best-dir",
                    str(best_dir),
                ],
            )
        except subprocess.CalledProcessError:
            # fallback: chạy không tham số
            print(
                "    ⚠️  model_training.py không chấp nhận args --data/--best-dir; chạy không đối số..."
            )
            run_py(path)
    else:
        print("==> [6/7] Bỏ qua (không có src/model_training.py)")


def step_7_evaluation(best_dir: Path, data_csv: Path, chart_dir: Path):
    """7) Đánh giá & vẽ biểu đồ"""
    path = SRC_DIR / "evaluation.py"
    if path.exists():
        print("==> [7/7] Chạy src/evaluation.py")
        chart_dir.mkdir(parents=True, exist_ok=True)
        # Nhiều bạn hardcode BEST_DIR trong evaluation.py.
        # Nếu evaluation.py hỗ trợ args, truyền vào; nếu không, script sẽ dùng mặc định của nó.
        try:
            run_py(
                path,
                args=[
                    "--best-dir",
                    str(best_dir),
                    "--data",
                    str(data_csv),
                    "--out-dir",
                    str(chart_dir),
                ],
            )
        except subprocess.CalledProcessError:
            print("    ⚠️  evaluation.py không chấp nhận args; chạy không đối số...")
            run_py(path)
    else:
        print("==> [7/7] Bỏ qua (không có src/evaluation.py)")


# ================== CLI & MAIN ==================
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Pipeline: load_stock -> load_news -> pre_stock -> pre_news -> model_sentiment -> model_training -> evaluation"
    )
    p.add_argument("--stock-dir", type=Path, default=STOCK_DIR, help="Thư mục CSV giá")
    p.add_argument(
        "--out-csv", type=Path, default=DATA_CSV, help="File CSV hợp nhất sau bước 1"
    )
    p.add_argument("--json", type=Path, default=JSON_PATH, help="File JSON sentiment")
    p.add_argument(
        "--start-date", type=str, default="2020-01-01", help="Lọc từ ngày này"
    )
    p.add_argument(
        "--preprocessed-csv",
        type=Path,
        default=PREPROCESSED_CSV,
        help="File dữ liệu sạch sau bước 3",
    )
    p.add_argument(
        "--best-dir", type=Path, default=BEST_DIR, help="Thư mục lưu/bọc model tốt nhất"
    )
    p.add_argument(
        "--chart-dir",
        type=Path,
        default=CHART_DIR,
        help="Thư mục lưu biểu đồ evaluation",
    )

    # Bật/tắt bước
    p.add_argument(
        "--skip-sentiment", action="store_true", help="Bỏ qua bước 5 (model_sentiment)"
    )
    p.add_argument(
        "--only",
        type=str,
        default="",
        help="Chỉ chạy 1 bước: 1..7, hoặc nhiều bước cách nhau bởi dấu phẩy (vd: 1,3,7)",
    )
    return p


def main():
    args = build_parser().parse_args()

    # Nếu dùng --only thì chỉ chạy các bước được liệt kê
    only_set = set([s.strip() for s in args.only.split(",") if s.strip()])

    def should(step_num: int) -> bool:
        return (not only_set) or (str(step_num) in only_set)

    # Bảo đảm thư mục dataset tồn tại
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    if should(1):
        step_1_load_stock(args.stock_dir, args.out_csv)

    if should(2):
        step_2_load_news()

    if should(3):
        # Lưu ý: với code của bạn, pre_stock.preprocess_data có thể đã "ghép JSON".
        step_3_pre_stock(
            args.out_csv, args.json, args.start_date, args.preprocessed_csv
        )

    if should(4):
        step_4_pre_news()

    if should(5):
        step_5_model_sentiment(enable=not args.skip_sentiment, out_json=args.json)

    if should(6):
        step_6_model_training(args.best_dir, args.preprocessed_csv)

    if should(7):
        step_7_evaluation(args.best_dir, args.preprocessed_csv, args.chart_dir)

    print("✅ Hoàn tất pipeline.")


if __name__ == "__main__":
    main()
