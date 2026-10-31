import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from news_service import get_final_news

app = FastAPI(title="Flash News API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/news")
@app.get("/api/news")
def news(refresh: bool = False):
    """Major Indian News Feed (English / National)"""
    return get_final_news(lang="en", force_refresh=refresh)


@app.get("/api/malayalam")
def api_malayalam(refresh: bool = False):
    """Malayalam Flash News Feed API Endpoint"""
    return get_final_news(lang="ml", force_refresh=refresh)


@app.get("/refresh")
def refresh():
    return {
        "news": get_final_news(lang="en", force_refresh=True),
        "malayalam": get_final_news(lang="ml", force_refresh=True),
    }


# Determine frontend static files directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_OUT = os.path.normpath(os.path.join(BASE_DIR, "..", "frontend", "out"))

if os.path.exists(FRONTEND_OUT):
    # Mount Next.js static asset chunks (_next)
    next_dir = os.path.join(FRONTEND_OUT, "_next")
    if os.path.exists(next_dir):
        app.mount("/_next", StaticFiles(directory=next_dir), name="next-assets")

    @app.get("/malayalam")
    def serve_malayalam(request: Request, refresh: bool = False):
        accept = request.headers.get("accept", "")
        if "application/json" in accept:
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
    @app.get("/")
    def root():
        return {"status": "online"}

    @app.get("/malayalam")
    def malayalam(refresh: bool = False):
        return get_final_news(lang="ml", force_refresh=refresh)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
