import pandas as pd
import time
from vnstock import Vnstock


def fetch_history(symbol, start_date="2025-01-01", end_date="2025-09-01", source="VCI"):
    """
    Lấy dữ liệu lịch sử giá cho symbol trong khoảng thời gian đã cho.
    source: TCBS | VCI | MSN (nguồn dữ liệu được vnstock hỗ trợ)
    """
    stock = Vnstock().stock(symbol=symbol, source=source)
    df = stock.quote.history(start=start_date, end=end_date)

    # Chuẩn hóa cột ngày
    if "tradingDate" in df.columns:
        df = df.rename(columns={"tradingDate": "date"})
    return df


def fetch_multiple(
    symbols,
    start_date,
    end_date,
    output_csv="stocks_history.csv",
    source="VCI",
    delay=2,
):
    """
    Crawl dữ liệu cho nhiều mã và ghi ra một file CSV duy nhất.
    delay: thời gian nghỉ giữa các request (giây)
    """
    all_data = []
    for sym in symbols:
        try:
            print(f"Đang lấy dữ liệu cho {sym} ...")
            df = fetch_history(sym, start_date, end_date, source=source)
            df["symbol"] = sym  # đánh dấu mã chứng khoán
            all_data.append(df)
        except Exception as e:
            print(f"Không lấy được dữ liệu cho {sym}: {e}")
        # Nghỉ giữa các request
        time.sleep(delay)

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df.to_csv(output_csv, index=False)
        print(f"Đã ghi dữ liệu vào '{output_csv}'.")
    else:
        print("Không có dữ liệu để ghi ra CSV.")


if __name__ == "__main__":
    # Thay bằng list 20 mã bạn cần
    symbols = ["ELC"]
    fetch_multiple(
        symbols,
        "2025-01-01",
        "2025-09-01",
        output_csv="vnstock_20_1.csv",
        source="TCBS",
        delay=3,  # chờ 3 giây giữa các request
    )
