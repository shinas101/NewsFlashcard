"""
FastAPI Server & Next.js Static Export Gateway
- Production REST API endpoints with Stale-While-Revalidate news delivery.
- Serves static Next.js export assets seamlessly from single Heroku dyno.
- Request timing and access logging middleware.
- Structured logging configuration.
"""
import os
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import PORT, LOG_LEVEL, BASE_DIR
from services import get_final_news

# Centralized Logging Setup
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s:%(threadName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NewsFlipcard API server on port %d...", PORT)
    yield
    logger.info("Shutting down NewsFlipcard API server...")


app = FastAPI(
    title="NewsFlipcard API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Logs incoming HTTP requests with latency."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms
    )
    return response


# --- Core API Endpoints ---

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/news")
@app.get("/api/news")
def news(lang: str = "en", refresh: bool = False):
    """News Feed API Endpoint (supports ?lang=en and ?lang=ml)"""
    target_lang = "ml" if lang.lower() in ("ml", "malayalam") else "en"
    return get_final_news(lang=target_lang, force_refresh=refresh)


@app.get("/api/malayalam")
def api_malayalam(refresh: bool = False):
    """Malayalam Flash News Feed API Endpoint"""
    return get_final_news(lang="ml", force_refresh=refresh)


@app.get("/refresh")
def refresh():
    """Forces an immediate refresh of both language pipelines."""
    logger.info("Manual refresh triggered for both feeds.")
    return {
        "news": get_final_news(lang="en", force_refresh=True),
        "malayalam": get_final_news(lang="ml", force_refresh=True),
    }


# --- Frontend Static Files & SPA Routing ---

FRONTEND_OUT = os.path.normpath(os.path.join(BASE_DIR, "..", "frontend", "out"))

if os.path.exists(FRONTEND_OUT):
    logger.info("Serving Next.js frontend export from %s", FRONTEND_OUT)

    # Mount Next.js static asset chunks (_next)
    next_dir = os.path.join(FRONTEND_OUT, "_next")
    if os.path.exists(next_dir):
        app.mount("/_next", StaticFiles(directory=next_dir), name="next-assets")

    @app.get("/malayalam")
    def serve_malayalam(request: Request, refresh: bool = False):
        accept = request.headers.get("accept", "")
        if "application/json" in accept or request.query_params.get("format") == "json":
            return get_final_news(lang="ml", force_refresh=refresh)
        html_file = os.path.join(FRONTEND_OUT, "malayalam.html")
        if os.path.exists(html_file):
            return FileResponse(html_file)
        return get_final_news(lang="ml", force_refresh=refresh)

    @app.get("/embed")
    def serve_embed():
        html_file = os.path.join(FRONTEND_OUT, "embed.html")
        if os.path.exists(html_file):
            return FileResponse(html_file)
        return {"error": "embed page not found"}

    @app.get("/embed.js")
    def serve_embed_js():
        js_file = os.path.join(FRONTEND_OUT, "embed.js")
        if os.path.exists(js_file):
            return FileResponse(js_file, media_type="application/javascript")
        return Response(status_code=404)

    @app.get("/widget.js")
    def serve_widget_js():
        js_file = os.path.join(FRONTEND_OUT, "widget.js")
        if os.path.exists(js_file):
            return FileResponse(js_file, media_type="application/javascript")
        return Response(status_code=404)

    @app.get("/test-embed.html")
    def serve_test_embed():
        html_file = os.path.join(FRONTEND_OUT, "test-embed.html")
        if os.path.exists(html_file):
            return FileResponse(html_file)
        return Response(status_code=404)

    @app.get("/")
    def serve_home():
        html_file = os.path.join(FRONTEND_OUT, "index.html")
        if os.path.exists(html_file):
            return FileResponse(html_file)
        return {"status": "online"}
else:
    logger.warning("Frontend export directory not found at %s. API-only mode active.", FRONTEND_OUT)

    @app.get("/")
    def root():
        return {"status": "online"}

    @app.get("/malayalam")
    def malayalam(refresh: bool = False):
        return get_final_news(lang="ml", force_refresh=refresh)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
