FROM python:3.11-slim

WORKDIR /server

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate self-signed SSL certs and initialise the database schema
RUN python generate_cert.py && python setupdb.py

# Run the full test suite — build fails here if any test fails
RUN python -m pytest

EXPOSE 1234

CMD ["python", "server.py", "1234"]
