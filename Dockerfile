FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY app/ ./app/

# 复制前端构建产物（供后端main.py静态托管）
COPY frontend/ ./frontend/

EXPOSE 8000

# Zeabur 会通过环境变量注入数据库连接
# 在 Zeabur 控制台设置：
# DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
# 或者使用 Zeabur PostgreSQL 插件自动注入

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
