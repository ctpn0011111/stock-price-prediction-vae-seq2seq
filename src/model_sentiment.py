# src/model_sentiment.py
from __future__ import annotations
import json
import torch
import numpy as np
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# ====== 1. Load PhoBERT model ======
MODEL_NAME = "wonrax/phobert-base-vietnamese-sentiment"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
model.eval()


# ====== 2. Chấm điểm sentiment cho list câu ======
def score_sentences_vi(texts, batch_size=32, max_length=256, device=None):
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    if not texts:
        return np.zeros((0, 3), dtype=np.float32)

    probs_all = []
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = [
                str(t) if isinstance(t, str) and t.strip() else ""
                for t in texts[i : i + batch_size]
            ]
            enc = tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=max_length,
            ).to(device)
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=1).cpu().numpy()
            probs_all.append(probs)
    return np.vstack(probs_all)


# ====== 3. Tính sentiment cho từng bài báo ======
def compute_article_sentiment_from_df(
    df_sent: pd.DataFrame, article_col="article_id", text_col="cau"
) -> pd.DataFrame:
    rows = []
    for aid, g in df_sent.groupby(article_col, dropna=False):
        texts = g[text_col].astype(str).tolist()
        P = score_sentences_vi(texts)
        if P.shape[0] == 0:
            agg = np.array([1.0, 0.0, 0.0], dtype=np.float32)  # mặc định NEG
        else:
            agg = P.mean(axis=0)
        compound = float(agg[2] - agg[0])
        rows.append(
            {
                "article_id": aid,
                "p_neg": float(agg[0]),
                "p_neu": float(agg[1]),
                "p_pos": float(agg[2]),
                "compound": compound,
            }
        )
    return pd.DataFrame(rows)


# ====== 4. Tính sentiment trung bình theo NGÀY ======
def compute_daily_sentiment_from_df(df_articles_with_date, date_col="date"):
    return (
        df_articles_with_date.groupby(date_col)[["p_neg", "p_neu", "p_pos"]]
        .mean()
        .reset_index()
    )


# ====== 5. Xuất JSON ======
def export_daily_json(df_daily, out_path, date_col="date"):
    payload = {
        r[date_col]: [float(r["p_neg"]), float(r["p_neu"]), float(r["p_pos"])]
        for _, r in df_daily.iterrows()
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ====== 6. Main: chạy thử pipeline ======
if __name__ == "__main__":
    input_csv = "/home/namphuong/course_materials/web/dataset/sentences_clean.csv"
    df_sent = pd.read_csv(input_csv)

    # Làm sạch cơ bản
    df_sent = df_sent.dropna(subset=["article_id", "date", "cau"]).copy()
    df_sent["cau"] = df_sent["cau"].astype(str)

    print(f"Loaded {len(df_sent)} sentences from {input_csv}")

    # 1) Sentiment cho từng article
    art_df = compute_article_sentiment_from_df(
        df_sent, article_col="article_id", text_col="cau"
    )

    # 2) Gắn lại cột ngày
    art_df = art_df.merge(
        df_sent[["article_id", "date"]].drop_duplicates(),
        on="article_id",
        how="left",
    )

    # 3) Tính sentiment theo ngày
    daily_df = compute_daily_sentiment_from_df(art_df, date_col="date")

    # 4) Xuất ra file JSON
    out_json = "/home/namphuong/course_materials/web/dataset/daily_scores_vi.json"
    export_daily_json(daily_df, out_json)

    print("Article-level sentiment:")
    print(art_df.head())

    print("Daily-level sentiment:")
    print(daily_df.head())

    print(f"✅ Saved daily sentiment to {out_json}")
