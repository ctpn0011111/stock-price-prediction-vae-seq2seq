🚀 Project Setup & Documentation

1. 📦 Install Dependencies
pip install -r requirements.txt

2. ▶️ Run the Program (main.py)
python main.py

3. 🌐 Launch the Web Interface
uvicorn web.app:app --reload --port 8000
Then open your browser and go to 👉 http://127.0.0.1:8000

4. 🔍 Overview of PhoBERT Model

PhoBERT for Sentiment Analysis

PhoBERT is a pre-trained language model for Vietnamese, based on the RoBERTa architecture, trained on large-scale Vietnamese text corpora.

It is highly effective for several NLP tasks, including:

Sentiment Analysis

Text Classification

Part-of-Speech Tagging

Other Natural Language Processing applications

📖 Documentation: https://huggingface.co/vinai/phobert-base


5. 🎨 VAE Seq2Seq Model (Variational AutoEncoder - Sequence to Sequence)
Variational Autoencoder (VAE) combined with Sequence-to-Sequence (Seq2Seq) is applied for sequence generation tasks (e.g., text generation).

VAE: Encodes input into a latent space, enabling the generation of new, diverse data that follows the original distribution.

Seq2Seq: Encodes an input sequence into a hidden vector (encoder) and reconstructs or generates an output sequence (decoder).

VAE + Seq2Seq: Together, they allow the model to both learn latent representations and generate more creative, diverse sequences.

Reference Paper: https://arxiv.org/abs/1511.06349

1. 📦 Cài đặt các thư viện

pip install -r requirements.txt

2. ▶️ Chạy chương trình (file main.py)

\*\* Bỏ comment ở bước 5 (để tạo sentiment)
python main.py

3. 🌐 Hiển thị giao diện web

uvicorn web.app:app --reload --port 8000
truy cập trang web: http://127.0.0.1:8000

4. 🔍 Tổng quan về model PhoBERT
PhoBERT cho Sentiment Analysis
PhoBERT là một pre-trained language model cho tiếng Việt, được xây dựng dựa trên kiến trúc RoBERTa và huấn luyện trên dữ liệu tiếng Việt lớn. 
Model này rất mạnh cho các tác vụ NLP như phân loại cảm xúc (sentiment analysis), 
phân loại văn bản, gán nhãn từ loại, và nhiều ứng dụng khác trong xử lý ngôn ngữ tự nhiên.

Link tài liệu: https://huggingface.co/vinai/phobert-base

5. 🎨 Model VAE Seq2Seq (Variational AutoEncoder - Sequence to Sequence)
Variational Autoencoder (VAE) kết hợp với kiến trúc Sequence-to-Sequence (Seq2Seq) được dùng để sinh chuỗi dữ liệu (ví dụ: sinh văn bản).
VAE giúp mô hình hóa dữ liệu đầu vào trong một latent space (không gian tiềm ẩn), từ đó có thể sinh ra dữ liệu mới có tính đa dạng và gần với phân phối gốc.
Seq2Seq cung cấp khả năng mã hóa một chuỗi đầu vào thành vector ẩn (encoder), sau đó giải mã thành chuỗi đầu ra (decoder). 
Khi kết hợp với VAE, mô hình có thể vừa học được biểu diễn tiềm ẩn, vừa sinh ra các chuỗi mới một cách sáng tạo.
