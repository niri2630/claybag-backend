# ClayBag Backend

FastAPI + PostgreSQL + Alembic

## Setup

```bash
cd claybag-backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Copy env file and configure
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run migrations
alembic upgrade head

# Seed categories + admin user
python seed.py

# Start server
uvicorn app.main:app --reload --port 8000
```

## Default Admin
- Email: admin@claybag.com
- Password: admin123

## API Docs
Visit http://localhost:8000/docs
