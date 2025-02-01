# Используем минималистичный образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости, сначала копируем только requirements.txt для кеширования слоев
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Запускаем основной скрипт
CMD ["python", "main.py"]