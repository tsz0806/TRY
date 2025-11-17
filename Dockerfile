# 使用官方 Python 映像
FROM python:3.11-slim

# 將工作目錄設定為 /app
WORKDIR /app

# 複製依賴文件
COPY requirements.txt .

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼到工作目錄
COPY . .

# 暴露端口 (Hugging Face 會自動處理端口映射)
EXPOSE 7860

# 啟動命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
