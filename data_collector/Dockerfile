FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# 手動実行用なので待機状態を維持
CMD ["tail", "-f", "/dev/null"]