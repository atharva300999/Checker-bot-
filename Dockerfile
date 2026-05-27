FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data

CMD python -c "from web_server import start; start(); import asyncio; from bot import main; asyncio.run(main())"
