FROM python:3.11-slim

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# 入出力ディレクトリの作成
RUN mkdir -p /app/input /app/output

# 非rootユーザーの作成と切り替え（セキュリティ向上）
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["python", "main.py"]
