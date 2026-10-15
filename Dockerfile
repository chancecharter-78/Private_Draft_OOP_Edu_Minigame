FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to use Docker's caching layers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run defaults to web port 8080
EXPOSE 8080

# Crucial Streamlit flags to prevent WebSocket errors and connection issues on Cloud Run
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.enableCORS=false --server.enableWebsocketCompression=false --server.enableXsrfProtection=false"]
