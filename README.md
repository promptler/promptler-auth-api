# Promptler Apple Sign-In Authentication API

A secure FastAPI service for managing Apple Sign-In authentication and user profiles for the Promptler iOS app.

## Features

- **Apple Sign-In Verification**: Verifies Apple identity tokens against Apple's JWKS
- **User Profile Management**: Stores and updates user profiles from Apple Sign-In
- **Device Tracking**: Logs device snapshots for analytics and debugging
- **Secure API**: API key authentication with rate limiting
- **Idempotent Operations**: Safe to retry requests without creating duplicates
- **PostgreSQL Database**: Persistent storage with full transaction support
- **Production Ready**: Includes deployment guide, monitoring, and error tracking

## API Endpoints

### POST /v1/auth/apple

Create or update a user profile from Apple Sign-In.

**Authentication:** Bearer token required

**Request Body:**
```json
{
  "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
  "display_name": "John Appleseed",
  "email": "john@privaterelay.appleid.com",
  "device_profile": {
    "model": "iPhone 14 Pro",
    "name": "John's iPhone",
    "system_name": "iOS",
    "system_version": "17.2",
    "locale": "en_US",
    "region": "US",
    "time_zone": "America/New_York",
    "app_version": "1.0.0",
    "app_build": "42"
  },
  "identity_token": "eyJraWQiOiJBQkNERUZHSCIsImFsZyI6IlJTMjU2In0...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Response (201 Created or 200 OK):**
```json
{
  "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
  "display_name": "John Appleseed",
  "email": "john@privaterelay.appleid.com",
  "latest_device_profile": {
    "model": "iPhone 14 Pro",
    "system_name": "iOS",
    "system_version": "17.2"
  },
  "first_seen_at": "2024-01-15T10:30:00Z",
  "last_updated_at": "2024-01-15T10:30:00Z",
  "created": true
}
```

**Error Responses:**
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Invalid or missing API key, or token verification failed
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### PATCH /v1/auth/apple/{identifier}

Update device metadata for an existing user.

**Authentication:** Bearer token required

**Request Body:**
```json
{
  "device_profile": {
    "model": "iPhone 14 Pro",
    "system_version": "17.3",
    "app_version": "1.0.1",
    "app_build": "43"
  },
  "timestamp": "2024-01-20T15:45:00Z"
}
```

**Response (200 OK):**
```json
{
  "apple_user_id": "001234.a1b2c3d4e5f6g7h8.0123",
  "latest_device_profile": {
    "model": "iPhone 14 Pro",
    "system_version": "17.3",
    "app_version": "1.0.1"
  },
  "last_updated_at": "2024-01-20T15:45:00Z"
}
```

**Error Responses:**
- `404 Not Found`: User not found
- Other errors same as POST endpoint

### GET /health

Health check endpoint (no authentication required).

**Response (200 OK):**
```json
{
  "status": "healthy",
  "environment": "production"
}
```

### GET /v1/auth/health

Authentication service health check (no authentication required).

## Security

### Apple Token Verification

The API verifies Apple identity tokens by:

1. Fetching Apple's public keys from their JWKS endpoint
2. Validating the JWT signature
3. Checking the token hasn't expired
4. Verifying the audience matches your bundle ID
5. Confirming the issuer is Apple
6. Extracting and validating the user identifier

**Important:** In production, always send the `identity_token` to ensure requests are legitimate.

### API Authentication

All endpoints (except health checks) require a Bearer token in the Authorization header:

```
Authorization: Bearer YOUR_API_KEY
```

Generate secure API keys:
```bash
openssl rand -base64 32
```

Store these keys in your iOS app securely (Keychain, not in code).

### Rate Limiting

Default limits:
- 10 requests per minute per endpoint
- 100 requests per hour per endpoint

Limits are applied per IP address. Adjust in `.env`:
```
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100
```

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd promptler_backend
   ```

2. **Create virtual environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL**
   ```bash
   # Create database
   createdb promptler_auth

   # Or with psql:
   psql -c "CREATE DATABASE promptler_auth;"
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

   Minimum required configuration:
   ```env
   DATABASE_URL=postgresql+asyncpg://localhost/promptler_auth
   SYNC_DATABASE_URL=postgresql://localhost/promptler_auth
   API_SECRET_KEY=dev-secret-key-change-in-production
   API_KEYS=dev-key-1,dev-key-2
   APPLE_BUNDLE_ID=com.promptler.app
   APPLE_TEAM_ID=YOUR_TEAM_ID
   APP_ENV=development
   APP_DEBUG=true
   ```

6. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

7. **Run the development server**
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at http://localhost:8000

8. **View API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Create/update user (replace with your API key)
curl -X POST http://localhost:8000/v1/auth/apple \
  -H "Authorization: Bearer dev-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "apple_user_id": "test-user-123",
    "display_name": "Test User",
    "email": "test@example.com",
    "timestamp": "2024-01-15T10:30:00Z"
  }'

# Update device metadata
curl -X PATCH http://localhost:8000/v1/auth/apple/test-user-123 \
  -H "Authorization: Bearer dev-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "device_profile": {
      "model": "iPhone 14 Pro",
      "system_version": "17.3"
    },
    "timestamp": "2024-01-20T15:45:00Z"
  }'
```

## Database Schema

### users table

| Column                 | Type      | Description                          |
|-----------------------|-----------|--------------------------------------|
| apple_user_id         | VARCHAR   | Primary key, Apple user identifier   |
| display_name          | VARCHAR   | User's display name (optional)       |
| email                 | VARCHAR   | User's email (optional)              |
| latest_device_profile | JSON      | Latest device information            |
| first_seen_at         | TIMESTAMP | When user was first created          |
| last_updated_at       | TIMESTAMP | When user was last updated           |

### device_snapshots table

| Column          | Type      | Description                          |
|----------------|-----------|--------------------------------------|
| id             | VARCHAR   | Primary key, UUID                    |
| apple_user_id  | VARCHAR   | Foreign key to users                 |
| device_model   | VARCHAR   | Device model                         |
| device_name    | VARCHAR   | Device name                          |
| system_name    | VARCHAR   | OS name (iOS)                        |
| system_version | VARCHAR   | OS version                           |
| locale         | VARCHAR   | Locale identifier                    |
| region         | VARCHAR   | Region code                          |
| time_zone      | VARCHAR   | Time zone                            |
| app_version    | VARCHAR   | App version                          |
| app_build      | VARCHAR   | App build number                     |
| raw_profile    | JSON      | Full device profile                  |
| captured_at    | TIMESTAMP | When data was captured on device     |
| created_at     | TIMESTAMP | When snapshot was created in DB      |

## Project Structure

```
promptler_backend/
├── alembic/                    # Database migrations
│   ├── versions/               # Migration scripts
│   └── env.py                  # Alembic configuration
├── app/
│   ├── api/                    # API endpoints
│   │   └── v1/
│   │       └── auth.py         # Authentication routes
│   ├── core/                   # Core utilities
│   │   ├── apple_auth.py       # Apple token verification
│   │   └── security.py         # API authentication
│   ├── models/                 # Database models
│   │   └── user.py             # User and DeviceSnapshot models
│   ├── schemas/                # Pydantic schemas
│   │   └── auth.py             # Request/response schemas
│   ├── config.py               # Configuration management
│   ├── database.py             # Database setup
│   └── main.py                 # FastAPI application
├── .env                        # Environment variables (not in git)
├── .env.example                # Example environment file
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic configuration
├── DEPLOYMENT.md               # Deployment guide
└── README.md                   # This file
```

## Environment Variables

| Variable                | Required | Description                                    |
|------------------------|----------|------------------------------------------------|
| DATABASE_URL           | Yes      | Async PostgreSQL connection string             |
| SYNC_DATABASE_URL      | Yes      | Sync PostgreSQL connection string              |
| API_SECRET_KEY         | Yes      | Secret key for API security                    |
| API_KEYS               | Yes      | Comma-separated list of valid API keys         |
| APPLE_BUNDLE_ID        | Yes      | Your app's bundle identifier                   |
| APPLE_TEAM_ID          | Yes      | Your Apple Developer Team ID                   |
| APPLE_JWKS_URL         | No       | Apple's JWKS endpoint (has default)            |
| APPLE_JWKS_CACHE_TTL   | No       | JWKS cache duration in seconds (default: 3600) |
| RATE_LIMIT_PER_MINUTE  | No       | Rate limit per minute (default: 10)            |
| RATE_LIMIT_PER_HOUR    | No       | Rate limit per hour (default: 100)             |
| APP_ENV                | No       | Environment (production/development)           |
| APP_DEBUG              | No       | Enable debug mode (default: false)             |
| APP_HOST               | No       | Host to bind to (default: 0.0.0.0)             |
| APP_PORT               | No       | Port to bind to (default: 8000)                |
| CORS_ORIGINS           | No       | Comma-separated allowed CORS origins           |
| SENTRY_DSN             | No       | Sentry DSN for error tracking                  |

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment instructions for Hostinger VPS.

Quick deployment checklist:
- [ ] Set up PostgreSQL database
- [ ] Configure environment variables
- [ ] Run database migrations
- [ ] Set up Gunicorn + Uvicorn service
- [ ] Configure Nginx reverse proxy
- [ ] Set up SSL certificates
- [ ] Enable monitoring and logging

## Monitoring

### Logs

Application logs include:
- Request/response logging
- Token verification success/failure
- Database operations
- Error tracking

View logs:
```bash
# Development
tail -f /var/log/promptler/error.log

# Production (systemd)
sudo journalctl -u promptler-auth -f
```

### Metrics to Monitor

- Request rate and response times
- Authentication success/failure rates
- Database connection pool usage
- Token verification latency
- Error rates by endpoint

## Troubleshooting

### Common Issues

**Database connection errors**
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check database credentials in `.env`
- Ensure database exists: `psql -l`

**Token verification fails**
- Check `APPLE_BUNDLE_ID` matches your app
- Verify token is fresh (not expired)
- Check Apple's JWKS endpoint is accessible

**Rate limit errors**
- Reduce request frequency
- Increase limits in `.env` if needed
- Check if IP is being shared (NAT)

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

[Your License Here]

## Support

For issues or questions, contact your development team.

---

**Version:** 1.0.0
**Last Updated:** January 2024
