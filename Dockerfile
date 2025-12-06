FROM python:3.11-slim

WORKDIR /app

# Tizim kutubxonalarini o'rnatish (Fly.io da kerak bo'lishi mumkin)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Kutubxonalarni nusxalash va o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodni nusxalash
COPY . .

# Fayl yozish uchun ruxsatlar
RUN chmod -R 755 /app

# PORT o'zgaruvchisi (Fly.io 8080 ishlatadi)
ENV PORT=8080
EXPOSE 8080

# Ishga tushirish (Fly.io uchun)
CMD ["python", "bot.py"]
