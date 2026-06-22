# 🎬 Anime Finder — Genre-based Recommender with Taste Memory

A web app that recommends anime by genre, suggests similar titles, and **learns your taste**:
when you finish watching a series, the app remembers its genres and re-ranks recommendations
toward the genres that overlap most across everything you've finished. The UI is fully in
**Japanese** and dynamically re-themes (colors, fonts, effects) based on the selected genre.

> Built as a portfolio project. Data scraped from MyAnimeList (~28k titles).

## ✨ Features

- **Browse by genre** — pick any of 20 genres; results are paginated across *all* matching titles
  (e.g. Comedy → 7,800+ titles, 260+ pages), not a fixed top-N.
- **Filtering & sorting** — by type (TV/Movie/OVA/…), status (airing/finished/upcoming), year,
  and sort (score / popularity / members / favorites / newest / title).
- **Content-based similarity** — TF-IDF over genres + themes + type, cosine similarity to find
  similar anime for any title.
- **User accounts** — register / login with hashed passwords (Werkzeug) and server-side
  sessions (Flask-Login). Each user has their **own** taste memory.
- **Taste memory (the core idea)** — marking a series as *finished* (watched episodes ≥ total)
  records it for that user in PostgreSQL. Genres that recur across finished shows rise to the top
  and drive a personalized "For You" ranking. (`genre_score` is computed on the fly from the
  finished list — single source of truth, no redundant table.)
- **Dynamic theming** — 4 themes that switch by genre group: Neutral (home), Action/Fantasy
  (cyberpunk neon), Romance (soft sakura), Horror (dark mystic + vignette). See [DESIGN.md](DESIGN.md).

## 🖼 Screenshots

| Home (Neutral) | Action | Romance | Horror |
|---|---|---|---|
| ![home](screenshot/home-neutral.png) | ![action](screenshot/genre-action.png) | ![romance](screenshot/genre-romance.png) | ![horror](screenshot/genre-horror.png) |

Filtering + pagination: ![filter](screenshot/filter-pagination-action.png)

## 🛠 Tech Stack

- **Backend:** Python, Flask, pandas, scikit-learn (TF-IDF + cosine similarity)
- **Auth & DB:** Flask-Login, Flask-SQLAlchemy, PostgreSQL (psycopg2), Werkzeug password hashing
- **Frontend:** vanilla HTML/CSS/JS (CSS variables for theming, Google Fonts: M PLUS 1p,
  M PLUS Rounded 1c, Hina Mincho)
- **Serving:** gunicorn (production), deployed on Render

## 🧩 Architecture

```
src/data_loader.py   # load + clean CSV (parse genres by '|', dedup mal_id, drop Hentai)
src/recommender.py   # TF-IDF + cosine similarity; genre search w/ filter, sort, pagination
src/database.py      # SQLAlchemy init + DATABASE_URL normalization
src/models.py        # User, FinishedAnime (1 user -> many finished)
src/memory.py        # per-user taste memory in DB; genre_score computed on the fly
app.py               # Flask: serves UI + REST API + Flask-Login auth
templates/ static/   # frontend (4 dynamic themes + auth UI)
```

REST API: `/api/genres`, `/api/anime?genre=&page=&sort=&type=&status=&year=`,
`/api/anime/<id>` (detail + similar), `/api/register`, `/api/login`, `/api/logout`, `/api/me`,
`/api/finish`, `/api/memory`, `/api/recommend` (memory/finish/recommend require auth).

## 🚀 Run locally

```bash
pip install -r requirements.txt

# PostgreSQL via Docker (needs Docker Desktop running)
docker run -d --name anime-pg -e POSTGRES_USER=anime -e POSTGRES_PASSWORD=anime \
  -e POSTGRES_DB=animedb -p 5432:5432 -v anime_pgdata:/var/lib/postgresql/data postgres:16

cp .env.example .env                # set DATABASE_URL + SECRET_KEY
python app.py                       # auto-creates tables → http://127.0.0.1:5000
```

## ☁️ Deploy (Render)

1. Push this repo to GitHub.
2. On [render.com](https://render.com) → **New** → **Blueprint** → connect the repo.
   Render reads [render.yaml](render.yaml), which provisions a free **PostgreSQL** database,
   wires `DATABASE_URL`, and generates `SECRET_KEY` automatically.
3. (Manual alternative) create a Web Service + a PostgreSQL instance, then set:
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
   - **Env:** `DATABASE_URL` (from the DB), `SECRET_KEY` (a long random string)
4. Deploy → public `https://<name>.onrender.com` URL.

> Note: on the free tier the web service sleeps after inactivity (first request ~30–60s to wake).
> User accounts & taste memory persist in PostgreSQL.

## 💡 Future improvements

- Collaborative filtering once a `rating.csv` is available (hybrid with the content model).
- Swap TF-IDF for neural embeddings + a vector index (FAISS) for semantic similarity.
- Extra filters (theme/demographic); "currently watching" progress tracking.
