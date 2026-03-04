FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=3000
ENV DB_PATH=/app/data/llm_dispatcher.db

EXPOSE 3000

VOLUME ["/app/data"]

CMD ["python", "app.py"]
