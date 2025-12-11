"""
Main FastAPI application for Promptler Apple Sign-In authentication
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api.v1 import auth, events
from app.database import async_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.APP_DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Optional: Initialize Sentry for error tracking
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            traces_sample_rate=0.1 if settings.APP_ENV == "production" else 1.0
        )
        logger.info("Sentry error tracking initialized")
    except ImportError:
        logger.warning("Sentry SDK not installed, skipping error tracking")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events (startup/shutdown)
    """
    # Startup
    logger.info(f"Starting Promptler Auth Service v{app.version}")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.APP_DEBUG}")

    yield

    # Shutdown
    logger.info("Shutting down Promptler Auth Service")
    await async_engine.dispose()
    logger.info("Database connections closed")


# Initialize FastAPI app
app = FastAPI(
    title="Promptler Apple Sign-In API",
    description="Secure REST API for managing Apple Sign-In authentication and user profiles",
    version="1.0.0",
    docs_url="/docs" if settings.APP_DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.APP_DEBUG else None,
    lifespan=lifespan
)

# Add CORS middleware
if settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {settings.cors_origins_list}")

# Add rate limit handler (use auth limiter for all endpoints)
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler for validation errors
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(f"Validation error on {request.url.path}: {errors}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors
    """
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)

    # Don't expose internal errors in production
    detail = str(exc) if settings.APP_DEBUG else "Internal server error"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail}
    )


# Include routers
app.include_router(auth.router, prefix="/v1")
app.include_router(events.router, prefix="/v1")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "service": "Promptler Apple Sign-In API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.APP_DEBUG else "disabled"
    }


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.APP_ENV
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level="info"
    )
