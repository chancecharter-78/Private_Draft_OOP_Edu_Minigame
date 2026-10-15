# Use a lightweight, official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to take advantage of Docker's layer caching
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the remaining application files into the container root
COPY . .

# Inform Docker that the application container expects web traffic routing
EXPOSE 8080

# Execute Streamlit using the dynamic port variable injected by Render
CMD ["sh", "-c", "streamlit run nierva_app.py --server.port=${PORT} --server.address=0.0.0.0 --server.enableCORS=false --server.enableWebsocketCompression=false"]
