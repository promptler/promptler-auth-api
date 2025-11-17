# Quick Start Guide

Get the Promptler Auth API running in under 5 minutes.

## Prerequisites

- Python 3.11+
- Docker (for PostgreSQL)
- Make (optional, but recommended)

## Quick Start (with Make)

```bash
# 1. Set up development environment
make dev

# 2. Edit .env with your configuration
nano .env

# 3. Start PostgreSQL
make docker-up

# 4. Run database migrations
make upgrade

# 5. Start the server
make run
```

The API will be available at http://localhost:8000

View docs at http://localhost:8000/docs

## Quick Start (without Make)

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Start PostgreSQL
docker-compose up -d

# 5. Run migrations
alembic upgrade head

# 6. Start server
uvicorn app.main:app --reload
```

## Minimum .env Configuration

```env
DATABASE_URL=postgresql+asyncpg://promptler:promptler@localhost:5432/promptler_auth
SYNC_DATABASE_URL=postgresql://promptler:promptler@localhost:5432/promptler_auth
API_SECRET_KEY=dev-secret-key
API_KEYS=dev-key-1,dev-key-2
APPLE_BUNDLE_ID=com.promptler.app
APPLE_TEAM_ID=YOUR_TEAM_ID
APP_ENV=development
APP_DEBUG=true
```

## Test the API

```bash
# Health check
curl http://localhost:8000/health

# Create a test user (replace dev-key-1 with your API key)
curl -X POST http://localhost:8000/v1/auth/apple \
  -H "Authorization: Bearer dev-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "apple_user_id": "test-user-123",
    "display_name": "Test User",
    "email": "test@example.com",
    "timestamp": "2024-01-15T10:30:00Z"
  }'
```

## Next Steps

1. **Production Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
2. **iOS Integration**: See [IOS_INTEGRATION.md](IOS_INTEGRATION.md)
3. **Full Documentation**: See [README.md](README.md)

## Stopping the Server

- Press `Ctrl+C` to stop the development server
- Run `make docker-down` to stop PostgreSQL

## Getting Help

- Run `make help` for available commands
- Check logs for errors
- Review the README.md for detailed documentation

---

**You're ready to go!** 🚀
