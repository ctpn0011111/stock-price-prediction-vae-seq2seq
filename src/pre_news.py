# src/text_cleaning.py
import re
import unicodedata
from datetime import datetime
import pandas as pd
from underthesea import sent_tokenize

# === Cấu hình ===
TICKER_WHITELIST = {
    "FPT",
    "VNZ",
    "GAS",
    "OIL",
    "CMC",
    "PVG",
    "PLX",
    "ITC",
    "SGT",
}
DOMAIN_TLDS = r"(vn|com|net|org|io|co|gov|edu|biz|info)"

# === Regex ===
RE_URL = re.compile(
    r"(https?://|www\.)\S+|\b[a-z0-9.-]+\." + DOMAIN_TLDS + r"\b", re.IGNORECASE
)
RE_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
RE_PHONE = re.compile(r"(?:\+?84|0)\d{8,11}")
RE_TRACK = re.compile(r"(utm_[a-z]+|\?ref=|fbclid=)", re.IGNORECASE)

RE_CAPTION_PREFIX = re.compile(
    r"^(ảnh|hình|hình ảnh|ảnh minh họa|video|clip|infographic|bảng|biểu đồ|sơ đồ|nguồn( ảnh)?):",
    re.IGNORECASE,
)
RE_FIG = re.compile(r"[\[(](hình|fig\.?|figure|ảnh)\s*\d+[\)\]]", re.IGNORECASE)
RE_BYLINE_PREFIX = re.compile(
    r"^(theo|tác giả|phóng viên|pv|biên tập|lược dịch|dịch bởi|nguồn):", re.IGNORECASE
)
RE_CTA_PREFIX = re.compile(
    r"^(xem thêm|đọc thêm|xem tiếp|xem nhanh|tin liên quan|bài viết liên quan|chủ đề|từ khóa|tag|hashtag|chia sẻ|share|theo dõi|follow|bình luận):",
    re.IGNORECASE,
)
RE_BREADCRUMB = re.compile(r"(trang chủ)\s*(»|>|/)", re.IGNORECASE)
RE_CONTACT_PREFIX = re.compile(
    r"^(liên hệ|contact|hotline|email|fanpage|tải ứng dụng|app store|google play|ch play):",
    re.IGNORECASE,
)
RE_SOCIAL = re.compile(
    r"(facebook|twitter|linkedin|youtube|zalo|tiktok)", re.IGNORECASE
)
RE_AD = re.compile(r"^(quảng cáo|qc|\[qc\]|sponsored|tài trợ|pr)\b", re.IGNORECASE)
RE_TIME_META = re.compile(
    r"^(cập nhật|ngày đăng|đăng lúc|ngày:|\d{1,2}:\d{2}(\s*\(gmt[+\-]?\d+\))?$)",
    re.IGNORECASE,
)
RE_DATE_LINE = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$")
RE_LONE_QUOTE = re.compile(r'^[\'"]+$')
RE_SHORT_DASH = re.compile(r"^-+$")
RE_ONLY_PUNCT = re.compile(r"^[\W_]+$")


# === Normalize ===
def normalize_unicode(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def mostly_non_alpha(s: str, thresh=0.55) -> bool:
    if not s:
        return True
    letters_digits = sum(ch.isalnum() for ch in s)
    return (letters_digits / max(1, len(s))) < (1 - thresh)


def is_short_heading(s: str) -> bool:
    st = s.strip()
    if len(st) <= 3:
        return not (st.isupper() and st in TICKER_WHITELIST)
    if st.isupper() and len(st.split()) <= 6 and not st.endswith(":"):
        toks = {tok for tok in re.findall(r"[A-Z]{2,}", st)}
        if not (toks & TICKER_WHITELIST):
            return True
    if len(st.split()) <= 4 and st.endswith(":"):
        return True
    return False


VI_LOWER = "aàáảãạăắằẳẵặâấầẩẫậbcdđeèéẻẽẹêếềểễệfghiìíỉĩịjklmnoòóỏõọôốồổỗộơớờởỡợpqrstuùúủũụưứừửữựvxyỳýỷỹỵ"
VI_UPPER = VI_LOWER.upper()


def _normalize_quotes(s: str) -> str:
    return (
        s.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
        .replace("…", "...")
    )


def _collapse_ws(s: str) -> str:
    s = s.replace("\u200b", "")
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\s*\n\s*", " ", s)
    return s.strip()


def _fix_initial_split_letter(s: str) -> str:
    pattern = re.compile(
        r'(^|[("\[\s])\s*([' + VI_UPPER + r"]{1})\s+([" + VI_LOWER + r"]+)"
    )
    return pattern.sub(lambda m: (m.group(1) or "") + m.group(2) + m.group(3), s)


def normalize_sentence(s: str) -> str:
    s = normalize_unicode(s)
    s = _normalize_quotes(s)
    s = _collapse_ws(s)
    s = _fix_initial_split_letter(s)
    s = s.strip(" \t\"'-•*|")
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    return s


# === Quyết định drop câu ===
def should_drop_sentence(raw: str):
    s = normalize_sentence(raw or "")
    if not s:
        return True, "empty_after_clean", s
    if RE_URL.search(s):
        return True, "url", s
    if RE_EMAIL.search(s):
        return True, "email", s
    if RE_PHONE.search(s):
        return True, "phone", s
    if RE_TRACK.search(s):
        return True, "tracking", s
    if RE_CAPTION_PREFIX.match(s):
        return True, "caption_prefix", s
    if RE_FIG.search(s):
        return True, "figure_ref", s
    if "©" in s or "bản quyền" in s.lower():
        return True, "copyright", s
    if RE_BYLINE_PREFIX.match(s):
        return True, "byline", s
    if RE_CTA_PREFIX.match(s):
        return True, "cta", s
    if RE_BREADCRUMB.search(s):
        return True, "breadcrumb", s
    if RE_CONTACT_PREFIX.match(s):
        return True, "contact", s
    if RE_SOCIAL.search(s) and len(s) <= 80:
        return True, "social", s
    if RE_AD.match(s):
        return True, "ads", s
    if RE_TIME_META.match(s):
        return True, "time_meta", s
    if RE_DATE_LINE.match(s):
        return True, "date_only", s
    if is_short_heading(s):
        return True, "heading_short", s
    if mostly_non_alpha(s):
        return True, "noisy_nonalpha", s
    if RE_LONE_QUOTE.match(s):
        return True, "lone_quote", s
    if RE_SHORT_DASH.match(s):
        return True, "dash_line", s
    if RE_ONLY_PUNCT.match(s):
        return True, "only_punct", s
    if len(s.split()) <= 2:
        return True, "too_short", s
    return False, "", s


# === Tách câu & lọc ===
def vi_sent_tokenize(text):
    text = str(text or "").strip()  # ✅ fix: tránh lỗi float
    if not text:
        return []
    # ưu tiên underthesea nếu có
    try:
        from underthesea import sent_tokenize

        sents = sent_tokenize(text)
        sents = [re.sub(r"\s+", " ", s).strip() for s in sents if s and s.strip()]
        if sents:
            return sents
    except Exception:
        pass

    txt = re.sub(r"\s+", " ", text)
    txt = re.sub(
        r"([\.!?…])(\s+)(?=[“\"'(\[\{]*[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯÝ])",
        r"\1\n",
        txt,
    )
    sents = [s.strip() for s in txt.split("\n") if s.strip()]
    return sents


# === Bộ lọc nâng cao ===
FIN_KEYWORDS = [
    "lợi nhuận",
    "doanh thu",
    "lỗ",
    "phá sản",
    "cắt giảm",
    "sáp nhập",
    "phát hành",
    "nợ xấu",
    "hạ hạng",
    "nâng hạng",
    "cổ tức",
    "hồi phục",
    "lao dốc",
    "bứt phá",
    "kỷ lục",
    "ra mắt sản phẩm",
    "tấn công mạng",
    "AI",
    "blockchain",
    "khách hàng mới",
    "mất dữ liệu",
    "điện mặt trời",
    "điện gió",
    "năng lượng tái tạo",
    "mở rộng công suất",
    "giá dầu",
    "cháy nổ",
]
NUMERIC_HINTS = [
    "%",
    "tỷ",
    "tỉ",
    "tỷ đồng",
    "tỉ đồng",
    "yoy",
    "qoq",
    "lnst",
    "ebitda",
    "P/E",
    "P/B",
    "ROE",
    "ROA",
]
NON_ALPHA_MIN_RATIO = 0.35


def _contains_any(s, kws):
    s = (s or "").lower()
    return any(k in s for k in kws)


def _mostly_non_alnum(s):
    valid = re.findall(r"[A-Za-zÀ-ỹ0-9]", s)
    return (len(valid) / max(1, len(s))) < NON_ALPHA_MIN_RATIO


def keep_sentence(s):
    s = (s or "").strip()
    if not s:
        return False
    tokens = re.findall(r"\w+", s, flags=re.UNICODE)
    if len(tokens) <= 1:
        return _contains_any(s, FIN_KEYWORDS) or bool(re.search(r"[!?]", s))
    if s.endswith(":") and len(tokens) <= 3 and not _contains_any(s, FIN_KEYWORDS):
        return False
    if s.isupper():
        if len(tokens) >= 5 or _contains_any(s, NUMERIC_HINTS):
            return True
        return False
    if _mostly_non_alnum(s) and not _contains_any(s, NUMERIC_HINTS):
        return False
    return True


def normalize_date_vi(s):
    s = str(s).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return s


def explode_content_to_sentences(
    df, date_col="ngay_dang", ticker_col="ticket", content_col="content"
):
    """
    Input: DataFrame có cột ngay_dang, ticket, content
    Output: DataFrame các câu (article_id, date, ticket, cau, sent_idx)
    """
    work = df[[date_col, ticker_col, content_col]].copy()
    work.rename(
        columns={date_col: "date", ticker_col: "ticket", content_col: "content"},
        inplace=True,
    )
    work["date"] = work["date"].map(normalize_date_vi)

    rows = []
    for idx, row in work.iterrows():
        date = row["date"]
        ticket = row["ticket"]
        content = row["content"]
        article_id = f"art_{idx}"
        sents = vi_sent_tokenize(content)
        sents = [s for s in sents if keep_sentence(s)]
        for i, s in enumerate(sents):
            rows.append(
                {
                    "article_id": article_id,
                    "date": date,
                    "ticket": ticket,
                    "cau": s,
                    "sent_idx": i,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import pandas as pd

    input_file = "/home/namphuong/course_materials/web/dataset/merged_news_clean.csv"
    output_file = "/home/namphuong/course_materials/web/dataset/sentences_clean.csv"

    if not pd.io.common.file_exists(input_file):
        print(f"❌ Không tìm thấy file {input_file}. Hãy chạy bước tiền xử lý trước.")
    else:
        df = pd.read_csv(input_file, encoding="utf-8")

        # Thêm cột 'ticket' giả định từ source (cần map theo thực tế)
        if "ticket" not in df.columns:
            df["ticket"] = df["source"].str.upper()

        # Gọi hàm tách câu
        df_sent = explode_content_to_sentences(
            df, date_col="ngay_dang", ticker_col="ticket", content_col="content"
        )

        print("Số câu sau khi tách:", df_sent.shape)
        print(df_sent.head())

        # Lưu file kết quả
        df_sent.to_csv(output_file, index=False, encoding="utf-8")
        print(f"✅ Đã lưu file tách câu tại {output_file}")
