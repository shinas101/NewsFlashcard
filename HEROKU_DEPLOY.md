# News FlipCard - Heroku Deployment Guide

This repository is pre-configured for **single-dyno Heroku deployment** running both the Next.js frontend and FastAPI backend seamlessly.

---

## 🚀 Quick Deploy (Heroku CLI)

### 1. Login & Create Heroku App
```bash
heroku login
heroku create my-news-flipcard
```

### 2. Add Buildpacks (Node.js + Python)
The Node.js buildpack builds the Next.js static assets into `frontend/out`, then the Python buildpack sets up the FastAPI server with local T5 summarizer:
```bash
heroku buildpacks:add heroku/nodejs
heroku buildpacks:add heroku/python
```

### 3. Deploy
```bash
git add .
git commit -m "Deploy News FlipCard to Heroku"
git push heroku main
```

### 4. Open Your Live App
```bash
heroku open
```

---

## ⚡ What Heroku Runs
- **Single Dyno**: The FastAPI server automatically binds to `$PORT` and serves both the API and the static Next.js export from a single process (`Procfile`).
- **Endpoints**:
  - `https://<app>.herokuapp.com/` — India National FlipCard Deck
  - `https://<app>.herokuapp.com/malayalam` — Malayalam FlipCard Deck
  - `https://<app>.herokuapp.com/embed` — Responsive embed view for external sites
  - `https://<app>.herokuapp.com/news` or `/api/news` — English News JSON API
  - `https://<app>.herokuapp.com/api/malayalam` — Malayalam News JSON API
  - `https://<app>.herokuapp.com/health` — Health check endpoint
- **Caching**: Runs embedded redislite/SQLite out of the box with zero setup. If you provision `heroku-redis`, it connects to `REDIS_URL` automatically.
- **T5 Summarizer**: Runs `google-t5/t5-small` locally with PyTorch CPU-only wheels, staying well within Heroku's 500MB slug limit.

