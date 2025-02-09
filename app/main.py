from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from app.core.config import settings
from app.core.middleware import setup_middleware
from app.api.v1.api import api_router
from app.core.exceptions import CustomException
from app.websockets.server import websocket_endpoint
import prometheus_client
from prometheus_client import Counter, Histogram
import time
from fastapi import Response

# Initialize metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Initialize Sentry for error tracking
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    traces_sample_rate=1.0
)

app = FastAPI(
    title="FETU Optima API",
    description="Backend API for FETU Optima intellectual challenge platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Setup middleware
setup_middleware(app)

# Add Sentry middleware
app.add_middleware(SentryAsgiMiddleware)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Add WebSocket endpoint
app.add_websocket_route("/ws", websocket_endpoint)

# Custom exception handler
@app.exception_handler(CustomException)
async def custom_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(
        media_type="text/plain",
        content=prometheus_client.generate_latest()
    )

# Request metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record request count and latency
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(time.time() - start_time)
    
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Initialize database connection
    from app.core.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize Redis connection
    from app.core.cache import redis_pool
    await redis_pool.initialize()

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Close database connection
    from app.core.database import engine
    await engine.dispose()
    
    # Close Redis connection
    from app.core.cache import redis_pool
    await redis_pool.close()
