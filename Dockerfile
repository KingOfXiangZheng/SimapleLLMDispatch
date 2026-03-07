# Stage 1: Build the frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/public
COPY public/package*.json ./
RUN npm install
COPY public/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/public/dist /app/public/dist

ENV PORT=3100
ENV DB_PATH=/app/data/llm_dispatcher.db

EXPOSE 3100
VOLUME ["/app/data"]

CMD ["python", "app.py"]
