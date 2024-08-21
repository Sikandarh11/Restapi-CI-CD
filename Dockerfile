FROM python:3.9-slim

# Install system dependencies for cryptography
RUN apt-get update && apt-get install -y \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Environment variables
ENV MONGO_URI='mongodb+srv://your_username:your_password@cluster0.mo69b0z.mongodb.net/myDB?retryWrites=true&w=majority'

# Command to run the app
CMD ["python", "app.py"]
