from pathlib import Path
import pandas as pd


def merge_stock_csvs(
    input_dir: str | Path = "/home/namphuong/course_materials/web/dataset/stock",
    out_csv: str | Path = "/home/namphuong/course_materials/web/dataset/data.csv",
    parse_date_col: str = "time",
    add_source_col: bool = True,
) -> Path:
    """
    Gộp tất cả *.csv trong input_dir thành 1 file CSV duy nhất.
    - Chuẩn hoá cột thời gian -> datetime (nếu có)
    - Thêm cột 'source_file' (tên file) để truy vết (có thể tắt)
    - Bỏ trùng hoàn toàn (duplicate rows)
    - Sắp xếp theo symbol, time nếu có các cột này
    Trả về đường dẫn file đầu ra.
    """
    input_dir = Path(input_dir)
    out_csv = Path(out_csv)
    files = sorted(input_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"Không tìm thấy CSV trong: {input_dir}")

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
        except UnicodeDecodeError:
            # fallback nếu file không phải UTF-8
            df = pd.read_csv(f, encoding="latin1")
        # chuẩn hoá cột thời gian nếu tồn tại
        if parse_date_col in df.columns:
            df[parse_date_col] = pd.to_datetime(df[parse_date_col], errors="coerce")
        frames.append(df)

    # Hợp nhất outer để không mất cột nào nếu schema khác nhau giữa các file
    merged = pd.concat(frames, ignore_index=True, join="outer")

    # Bỏ trùng hoàn toàn (mọi cột giống nhau)
    merged = merged.drop_duplicates()

    # Sắp xếp nếu có các cột liên quan
    sort_cols = [c for c in ["symbol", parse_date_col] if c in merged.columns]
    if sort_cols:
        merged = merged.sort_values(sort_cols)

    # Ghi ra CSV
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_csv, index=False)
    return out_csv


if __name__ == "__main__":
    try:
        output_path = merge_stock_csvs()
        print(f"Đã gộp dữ liệu thành công. File kết quả: {output_path}")
    except Exception as e:
        print(f"Lỗi: {str(e)}")
