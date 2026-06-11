FROM python:3.11-slim

WORKDIR /app

# MySQL 클라이언트 빌드 및 타임존 설정을 위한 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# app.main:app 구조에 맞게 경로 지정
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
