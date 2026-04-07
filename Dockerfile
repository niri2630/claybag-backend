FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt boto3

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run alembic migrations then start uvicorn.
# Migrations are idempotent — alembic skips ones already applied.
# If migrations fail the container exits and ECS rolls back to the previous task.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
