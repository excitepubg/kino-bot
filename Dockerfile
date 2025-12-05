FROM python:3.11-slim

WORKDIR /app

# Tizim kutubxonalarini o'rnatish
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Kutubxonalarni nusxalash va o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodni nusxalash
COPY . .

# Fayl yozish uchun ruxsatlar
RUN chmod -R 755 /app

# Port
EXPOSE 10000

# Ishga tushirish
CMD ["python", "bot.py"]
