# 1. Cài đặt các thư viện

pip install -r requirements.txt

# Chạy chương trình (file main.py)

\*\* Bỏ comment ở bước 5 (để tạo sentiment)
python main.py

# Hiển thị giao diện web

uvicorn web.app:app --reload --port 8000
truy cập trang web: http://127.0.0.1:8000
