# Use an official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /server

# Copy dependency list first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Run the server.py listening on port 1234
CMD ["python", "server.py", "1234"] 
