FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data

EXPOSE 8080

CMD gunicorn web_server:app --bind 0.0.0.0:$PORT --timeout 120 & python bot.py
