# talentflow-ai-backend-bak/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（pdfplumber 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 只复制代码，不复制模型和 data/
COPY app/ ./app/
COPY .env ./

# 创建挂载点（模型和数据文件通过 Volume 挂载）
RUN mkdir -p /app/data/models /app/data/faiss_db /app/data/uploads

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
