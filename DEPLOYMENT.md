# Deployment Guide for Hostinger VPS

This guide walks through deploying the Promptler Apple Sign-In API to a Hostinger VPS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [PostgreSQL Installation](#postgresql-installation)
4. [Application Deployment](#application-deployment)
5. [Nginx Reverse Proxy](#nginx-reverse-proxy)
6. [SSL Certificates](#ssl-certificates)
7. [Systemd Service](#systemd-service)
8. [Environment Configuration](#environment-configuration)
9. [Database Migrations](#database-migrations)
10. [Testing](#testing)
11. [Monitoring](#monitoring)
12. [Troubleshooting](#troubleshooting)

## Prerequisites

- Hostinger VPS with Ubuntu 20.04 or later
- Root or sudo access
- Domain name pointing to your VPS IP
- SSH access configured

## Server Setup

### 1. Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Required System Packages

```bash
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    nginx \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    build-essential \
    certbot \
    python3-certbot-nginx
```

### 3. Create Application User

```bash
sudo adduser --system --group --home /opt/promptler promptler
```

## PostgreSQL Installation

### 1. Configure PostgreSQL

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE promptler_auth;
CREATE USER promptler_user WITH ENCRYPTED PASSWORD 'your-secure-password-here';
GRANT ALL PRIVILEGES ON DATABASE promptler_auth TO promptler_user;
\c promptler_auth
GRANT ALL ON SCHEMA public TO promptler_user;
EOF
```

### 2. Configure PostgreSQL Authentication

Edit `/etc/postgresql/*/main/pg_hba.conf` and ensure local connections use md5:

```
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

## Application Deployment

### 1. Clone Repository

```bash
sudo mkdir -p /opt/promptler
sudo chown promptler:promptler /opt/promptler

# As promptler user
sudo -u promptler git clone <your-repo-url> /opt/promptler/app
cd /opt/promptler/app
```

### 2. Create Python Virtual Environment

```bash
sudo -u promptler python3.11 -m venv /opt/promptler/venv
```

### 3. Install Python Dependencies

```bash
sudo -u promptler /opt/promptler/venv/bin/pip install --upgrade pip
sudo -u promptler /opt/promptler/venv/bin/pip install -r requirements.txt
```

### 4. Create Environment File

```bash
sudo -u promptler nano /opt/promptler/.env
```

Add the following configuration (replace with your actual values):

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://promptler_user:your-secure-password-here@localhost:5432/promptler_auth
SYNC_DATABASE_URL=postgresql://promptler_user:your-secure-password-here@localhost:5432/promptler_auth

# API Security - Generate strong random keys
API_SECRET_KEY=<generate-with-openssl-rand-base64-32>
API_KEYS=<key1>,<key2>,<key3>

# Apple Sign-In Configuration
APPLE_BUNDLE_ID=com.promptler.app
APPLE_TEAM_ID=YOUR_TEAM_ID
APPLE_JWKS_URL=https://appleid.apple.com/auth/keys
APPLE_JWKS_CACHE_TTL=3600

# Rate Limiting
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100

# Application
APP_ENV=production
APP_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Optional: Sentry for error tracking
# SENTRY_DSN=your-sentry-dsn-here
```

### 5. Generate Secure API Keys

```bash
# Generate API secret key
openssl rand -base64 32

# Generate API keys for iOS app (save these for your app)
openssl rand -base64 32
openssl rand -base64 32
```

### 6. Set Proper Permissions

```bash
sudo chown promptler:promptler /opt/promptler/.env
sudo chmod 600 /opt/promptler/.env
```

## Database Migrations

### 1. Run Initial Migration

```bash
cd /opt/promptler/app
sudo -u promptler /opt/promptler/venv/bin/alembic upgrade head
```

### 2. Verify Database Schema

```bash
sudo -u postgres psql -d promptler_auth -c "\dt"
```

You should see `users` and `device_snapshots` tables.

## Systemd Service

### 1. Create Systemd Service File

```bash
sudo nano /etc/systemd/system/promptler-auth.service
```

Add the following content:

```ini
[Unit]
Description=Promptler Apple Sign-In Authentication API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=promptler
Group=promptler
WorkingDirectory=/opt/promptler/app
Environment="PATH=/opt/promptler/venv/bin"
EnvironmentFile=/opt/promptler/.env
ExecStart=/opt/promptler/venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --access-logfile /var/log/promptler/access.log \
    --error-logfile /var/log/promptler/error.log \
    --log-level info \
    app.main:app

# Restart policy
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/promptler

[Install]
WantedBy=multi-user.target
```

### 2. Create Log Directory

```bash
sudo mkdir -p /var/log/promptler
sudo chown promptler:promptler /var/log/promptler
```

### 3. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable promptler-auth
sudo systemctl start promptler-auth
sudo systemctl status promptler-auth
```

## Nginx Reverse Proxy

### 1. Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/promptler-auth
```

Add the following configuration:

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth_burst:10m rate=100r/m;

upstream promptler_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name auth.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name auth.yourdomain.com;

    # SSL certificates (will be configured by Certbot)
    # ssl_certificate /etc/letsencrypt/live/auth.yourdomain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/auth.yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/promptler-auth-access.log;
    error_log /var/log/nginx/promptler-auth-error.log;

    # Max body size for requests
    client_max_body_size 1M;

    # Proxy settings
    location / {
        # Rate limiting
        limit_req zone=auth_limit burst=20 nodelay;
        limit_req zone=auth_burst;

        proxy_pass http://promptler_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }

    # Health check endpoint (no rate limiting)
    location /health {
        proxy_pass http://promptler_backend;
        access_log off;
    }
}
```

### 2. Enable Nginx Configuration

```bash
sudo ln -s /etc/nginx/sites-available/promptler-auth /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL Certificates

### 1. Obtain SSL Certificate with Let's Encrypt

```bash
sudo certbot --nginx -d auth.yourdomain.com
```

Follow the prompts to configure HTTPS.

### 2. Auto-Renewal

Certbot automatically sets up renewal. Test it:

```bash
sudo certbot renew --dry-run
```

## Testing

### 1. Test Application Directly

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "production"
}
```

### 2. Test Through Nginx

```bash
curl https://auth.yourdomain.com/health
```

### 3. Test Authentication Endpoint

```bash
curl -X POST https://auth.yourdomain.com/v1/auth/apple \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "apple_user_id": "test-user-123",
    "timestamp": "2024-01-15T10:30:00Z"
  }'
```

Should return 401 if token verification is required, or create a user if token is optional.

## Monitoring

### 1. Check Service Status

```bash
sudo systemctl status promptler-auth
```

### 2. View Application Logs

```bash
# Real-time logs
sudo journalctl -u promptler-auth -f

# Recent logs
sudo journalctl -u promptler-auth -n 100

# Gunicorn logs
sudo tail -f /var/log/promptler/error.log
sudo tail -f /var/log/promptler/access.log
```

### 3. Check Nginx Logs

```bash
sudo tail -f /var/log/nginx/promptler-auth-error.log
sudo tail -f /var/log/nginx/promptler-auth-access.log
```

### 4. Monitor Database

```bash
sudo -u postgres psql -d promptler_auth -c "SELECT COUNT(*) FROM users;"
sudo -u postgres psql -d promptler_auth -c "SELECT COUNT(*) FROM device_snapshots;"
```

### 5. Set Up Log Rotation

Create `/etc/logrotate.d/promptler`:

```
/var/log/promptler/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 promptler promptler
    sharedscripts
    postrotate
        systemctl reload promptler-auth > /dev/null 2>&1 || true
    endscript
}
```

## Troubleshooting

### Service Won't Start

```bash
# Check detailed error messages
sudo journalctl -u promptler-auth -n 50 --no-pager

# Check if port is already in use
sudo netstat -tulpn | grep 8000

# Verify environment file
sudo -u promptler cat /opt/promptler/.env

# Test Python imports
sudo -u promptler /opt/promptler/venv/bin/python -c "from app.main import app; print('OK')"
```

### Database Connection Issues

```bash
# Test database connection
sudo -u postgres psql -d promptler_auth -c "SELECT version();"

# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify credentials
sudo -u promptler psql -h localhost -U promptler_user -d promptler_auth
```

### Nginx Issues

```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx error logs
sudo tail -100 /var/log/nginx/error.log

# Restart Nginx
sudo systemctl restart nginx
```

### SSL Certificate Issues

```bash
# Renew certificates manually
sudo certbot renew

# Check certificate expiration
sudo certbot certificates
```

## Updating the Application

### 1. Pull Latest Code

```bash
sudo -u promptler git -C /opt/promptler/app pull origin main
```

### 2. Update Dependencies

```bash
sudo -u promptler /opt/promptler/venv/bin/pip install -r /opt/promptler/app/requirements.txt
```

### 3. Run Migrations

```bash
cd /opt/promptler/app
sudo -u promptler /opt/promptler/venv/bin/alembic upgrade head
```

### 4. Restart Service

```bash
sudo systemctl restart promptler-auth
```

## Security Checklist

- [ ] Strong PostgreSQL password configured
- [ ] API keys are long, random, and kept secret
- [ ] `.env` file has restricted permissions (600)
- [ ] SSL/TLS certificates are valid and auto-renewing
- [ ] Rate limiting is configured
- [ ] Firewall (UFW) is enabled and configured
- [ ] Sentry or error tracking is configured (optional)
- [ ] Regular backups of database are configured
- [ ] Security headers are enabled in Nginx
- [ ] Application runs as non-root user

## Backup Strategy

### Database Backup Script

Create `/opt/promptler/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/promptler/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="promptler_auth_${DATE}.sql.gz"

mkdir -p $BACKUP_DIR
sudo -u postgres pg_dump promptler_auth | gzip > "${BACKUP_DIR}/${FILENAME}"

# Keep only last 30 days
find $BACKUP_DIR -name "promptler_auth_*.sql.gz" -mtime +30 -delete
```

Add to crontab:

```bash
sudo crontab -e
# Add: 0 2 * * * /opt/promptler/backup.sh
```

## Performance Tuning

### Gunicorn Workers

Calculate optimal workers:
```
workers = (2 x CPU cores) + 1
```

Edit `/etc/systemd/system/promptler-auth.service` and adjust `--workers`.

### PostgreSQL

Edit `/etc/postgresql/*/main/postgresql.conf`:

```
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
max_connections = 100
```

Restart PostgreSQL after changes.

## Support

For issues or questions:
- Check application logs: `sudo journalctl -u promptler-auth -f`
- Review this guide's troubleshooting section
- Contact your development team

---

**Last Updated:** January 2024
