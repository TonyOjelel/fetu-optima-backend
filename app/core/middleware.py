from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.config import settings

def setup_middleware(app: FastAPI) -> None:
    """Setup middleware for the application"""
    
    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
    
    # Add Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add custom security headers
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
    
    # Add request ID
    @app.middleware("http")
    async def add_request_id(request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    
    # Add basic rate limiting
    limiter = {}
    
    @app.middleware("http")
    async def rate_limit(request, call_next):
        client_ip = request.client.host
        
        # Reset counts every hour
        current_hour = datetime.utcnow().hour
        if client_ip in limiter and limiter[client_ip]["hour"] != current_hour:
            limiter[client_ip] = {"count": 0, "hour": current_hour}
        
        # Initialize new clients
        if client_ip not in limiter:
            limiter[client_ip] = {"count": 0, "hour": current_hour}
        
        # Check rate limit
        if limiter[client_ip]["count"] >= 1000:  # 1000 requests per hour
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"}
            )
        
        limiter[client_ip]["count"] += 1
        return await call_next(request)
    
    # Add response compression
    @app.middleware("http")
    async def compress_response(request, call_next):
        response = await call_next(request)
        
        # Check if response should be compressed
        if (
            response.headers.get("content-type", "").startswith("text/")
            or response.headers.get("content-type", "").startswith("application/json")
        ) and len(response.body) > 500:
            response.headers["content-encoding"] = "gzip"
            response.body = gzip.compress(response.body)
        
        return response
