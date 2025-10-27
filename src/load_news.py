# src/read_data_folders.py
from __future__ import annotations
import os
import json
import pandas as pd
from typing import Iterable, List, Optional


def read_data_folders(
    root_dir: str = "dataset/data_news",
    target_folders: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """
    Đọc tất cả file JSON/CSV trong các thư mục con và ghép lại.
    Thêm cột 'folder' = tên thư mục con. KHÔNG xử lý nội dung.
    """
    if target_folders is None:
        target_folders = [
            d
            for d in sorted(os.listdir(root_dir))
            if os.path.isdir(os.path.join(root_dir, d))
        ]

    all_data: List[dict] = []

    for folder in target_folders:
        folder_path = os.path.join(root_dir, folder)
        if not os.path.isdir(folder_path):
            continue

        for file in sorted(os.listdir(folder_path)):
            file_path = os.path.join(folder_path, file)

            # --- JSON ---
            if file.lower().endswith(".json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if isinstance(data, list):
                        for row in data:
                            if isinstance(row, dict):
                                row = dict(row)
                                row["folder"] = folder
                                all_data.append(row)
                    elif isinstance(data, dict):
                        row = dict(data)
                        row["folder"] = folder
                        all_data.append(row)

                except Exception as e:
                    print(f"❌ Lỗi đọc JSON {file_path}: {e}")

            # --- CSV ---
            elif file.lower().endswith(".csv"):
                try:
                    df_csv = pd.read_csv(file_path, encoding="utf-8", low_memory=False)
                except UnicodeDecodeError:
                    df_csv = pd.read_csv(file_path, encoding="latin1", low_memory=False)
                except Exception as e:
                    print(f"❌ Lỗi đọc CSV {file_path}: {e}")
                    continue

                df_csv = df_csv.copy()
                df_csv["folder"] = folder
                all_data.extend(df_csv.to_dict(orient="records"))

    return pd.DataFrame(all_data)


def clean_news_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Áp dụng đúng các bước xử lý trong notebook:
    - Fill ngay_dang/ngay_crawl từ pub_date/crawl_date khi thiếu
    - Chọn cột quan trọng, folder -> source
    - Format lại ngay_dang theo từng 'source' (vnz, gas, oil, pvg, cmc, sgt, plx)
    """
    if df.empty:
        return df

    # Bảo vệ: tạo cột nếu thiếu để tránh KeyError
    for c in [
        "ngay_dang",
        "pub_date",
        "ngay_crawl",
        "crawl_date",
        "url",
        "title",
        "content",
        "folder",
    ]:
        if c not in df.columns:
            df[c] = pd.NA

    # 1) Fillna thời gian
    df["ngay_dang"] = df["ngay_dang"].fillna(df["pub_date"])
    df["ngay_crawl"] = df["ngay_crawl"].fillna(df["crawl_date"])

    # 2) Lọc/trả tên cột
    df = df.rename(columns={"folder": "source"})
    df = df[["url", "title", "content", "ngay_dang", "source"]].copy()

    # Tất cả sang chuỗi để thao tác slice/replace an toàn
    for c in ["ngay_dang", "source"]:
        df[c] = df[c].astype(str)

    # 3) Chuẩn hoá theo từng source (y hệt notebook)

    # vnz: lấy 10 ký tự cuối
    mask = df["source"].str.strip().str.lower().eq("vnz")
    df.loc[mask, "ngay_dang"] = df.loc[mask, "ngay_dang"].str[-10:]

    # gas: lấy từ index 1..12
    mask = df["source"].str.strip().str.lower().eq("gas")
    df.loc[mask, "ngay_dang"] = df.loc[mask, "ngay_dang"].str[1:12]

    # oil: thay . -> /
    mask = df["source"].str.strip().str.lower().eq("oil")
    df.loc[mask, "ngay_dang"] = df.loc[mask, "ngay_dang"].str.replace(
        ".", "/", regex=False
    )

    # pvg: lấy 10 ký tự cuối rồi lại slice 0..10 (giữ nguyên ý notebook)
    mask = df["source"].str.strip().str.lower().eq("pvg")
    df.loc[mask, "ngay_dang"] = df.loc[mask, "ngay_dang"].str[-10:]
    df.loc[mask, "ngay_dang"] = df.loc[mask, "ngay_dang"].str.slice(0, 10)

    # cmc: parse về datetime rồi format dd/mm/YYYY
    mask = df["source"].str.strip().str.lower().eq("cmc")
    df.loc[mask, "ngay_dang"] = pd.to_datetime(
        df.loc[mask, "ngay_dang"], errors="coerce", dayfirst=True
    ).dt.strftime("%d/%m/%Y")

    # sgt: lấy 15 ký tự cuối → bỏ chữ "Tháng " → chuẩn hoá khoảng trắng → tách & ghép dd/mm/yyyy
    mask = df["source"].str.strip().str.lower().eq("sgt")
    df.loc[mask, "ngay_dang"] = df.loc[mask, "ngay_dang"].str[-15:]
    df.loc[mask, "ngay_dang"] = df.loc[mask, "ngay_dang"].str.replace(
        "Tháng ", "", regex=False
    )
    df.loc[mask, "ngay_dang"] = (
        df.loc[mask, "ngay_dang"].str.strip().str.replace(r"\s+", " ", regex=True)
    )
    split_cols = df.loc[mask, "ngay_dang"].str.split(" ", expand=True)
    if not split_cols.empty and split_cols.shape[1] >= 3:
        split_cols.columns = ["day", "month", "year"] + [
            f"extra{i}" for i in range(split_cols.shape[1] - 3)
        ]
        df.loc[mask, "day"] = split_cols["day"]
        df.loc[mask, "month"] = split_cols["month"]
        df.loc[mask, "year"] = split_cols["year"]
        df.loc[mask, "day"] = df.loc[mask, "day"].str.zfill(2)
        df.loc[mask, "month"] = df.loc[mask, "month"].str.zfill(2)
        df.loc[mask, "ngay_dang"] = (
            df.loc[mask, "day"]
            + "/"
            + df.loc[mask, "month"]
            + "/"
            + df.loc[mask, "year"]
        )
        df = df.drop(columns=["day", "month", "year"], errors="ignore")

    # plx: bỏ từ 'tháng' + ',' → tách & ghép dd/mm/yyyy
    mask = df["source"].str.strip().str.lower().eq("plx")
    df.loc[mask, "ngay_dang"] = (
        df.loc[mask, "ngay_dang"]
        .str.replace("tháng", "", case=False, regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )
    split_cols = df.loc[mask, "ngay_dang"].str.split(" ", expand=True)
    if not split_cols.empty and split_cols.shape[1] >= 3:
        split_cols.columns = ["day", "month", "year"] + [
            f"extra{i}" for i in range(split_cols.shape[1] - 3)
        ]
        df.loc[mask, "day"] = split_cols["day"].str.zfill(2)
        df.loc[mask, "month"] = split_cols["month"].str.zfill(2)
        df.loc[mask, "year"] = split_cols["year"]
        df.loc[mask, "ngay_dang"] = (
            df.loc[mask, "day"]
            + "/"
            + df.loc[mask, "month"]
            + "/"
            + df.loc[mask, "year"]
        )
        df = df.drop(columns=["day", "month", "year"], errors="ignore")

    return df


# Ví dụ chạy nhanh
if __name__ == "__main__":
    root_dir = "dataset/data_news/"
    target_folders = ["vnz", "itc", "cmc", "fpt", "gas", "sgt", "oil", "plx", "pvg"]

    raw = read_data_folders(root_dir, target_folders)
    print("Raw shape:", raw.shape)

    data = clean_news_dataframe(raw)
    data = data[["content", "ngay_dang", "source"]]
    data = data.dropna(subset=["content", "ngay_dang", "source"]).reset_index(drop=True)
    print("Clean shape:", data.shape)
    print(data.head())

    # Lưu nếu muốn:
    data.to_csv("dataset/merged_news_clean.csv", index=False, encoding="utf-8")
    print("Saved to dataset/merged_news_clean.csv")
