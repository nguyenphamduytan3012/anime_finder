"""Anime Favorite Finder — Flask backend.

Serve UI + REST API:
- lọc anime theo genre (phân trang + filter)
- gợi ý anime tương tự (content-based)
- AUTH: đăng ký / đăng nhập / đăng xuất (Flask-Login)
- ghi nhớ thể loại yêu thích THEO TỪNG USER (DB) khi xem hết một bộ
- gợi ý anime dựa trên 'gu' đã ghi nhớ của user đang đăng nhập
"""
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user,
)

from src.data_loader import load_anime, all_genres
from src.recommender import AnimeRecommender
from src.database import db, normalize_db_url
from src.models import User
from src import memory

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = normalize_db_url(
    os.environ.get("DATABASE_URL", "postgresql+psycopg2://anime:anime@localhost:5432/animedb")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def _unauthorized():
    return jsonify({"error": "ログインが必要です。", "auth_required": True}), 401


# ----- tải dataset + tạo bảng -----
print("Loading dataset…")
DF = load_anime()
REC = AnimeRecommender(DF)
GENRES = all_genres(DF)
with app.app_context():
    db.create_all()
print(f"Ready: {len(DF)} anime, {len(GENRES)} genres.")


# ===================== UI =====================
@app.route("/")
def index():
    return render_template("index.html")


# ===================== AUTH =====================
@app.route("/api/register", methods=["POST"])
def api_register():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if len(username) < 3 or len(password) < 4:
        return jsonify({"error": "ユーザー名は3文字以上、パスワードは4文字以上にしてください。"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "このユーザー名は既に使われています。"}), 409
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"username": user.username})


@app.route("/api/login", methods=["POST"])
def api_login():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "ユーザー名またはパスワードが違います。"}), 401
    login_user(user)
    return jsonify({"username": user.username})


@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me():
    if current_user.is_authenticated:
        return jsonify({"username": current_user.username})
    return jsonify({"username": None})


# ===================== ANIME =====================
@app.route("/api/genres")
def api_genres():
    return jsonify(GENRES)


@app.route("/api/anime")
def api_anime():
    genre = request.args.get("genre", "").strip()
    if not genre:
        return jsonify({"error": "missing genre"}), 400

    def _int(name, default):
        try:
            return int(request.args.get(name, default))
        except (ValueError, TypeError):
            return default

    return jsonify(REC.search(
        genre,
        page=_int("page", 1),
        page_size=_int("page_size", 30),
        sort=request.args.get("sort", "score"),
        type_filter=request.args.get("type", ""),
        status=request.args.get("status", ""),
        year=request.args.get("year", ""),
    ))


@app.route("/api/anime/<int:mal_id>")
def api_anime_detail(mal_id):
    item = REC.get_one(mal_id)
    if item is None:
        return jsonify({"error": "not found"}), 404
    item["similar"] = REC.similar(mal_id, n=12)
    return jsonify(item)


# ===================== MEMORY (per-user) =====================
@app.route("/api/finish", methods=["POST"])
@login_required
def api_finish():
    """Đánh dấu đã xem hết. Body: {mal_id, watched_episodes}."""
    body = request.get_json(force=True, silent=True) or {}
    mal_id = body.get("mal_id")
    watched = body.get("watched_episodes")
    item = REC.get_one(mal_id) if mal_id is not None else None
    if item is None:
        return jsonify({"error": "anime not found"}), 404

    total = item["episodes"]
    # finished khi xem >= tổng số tập; nếu episodes không rõ -> coi như đã xác nhận
    if total is not None:
        try:
            if int(watched) < int(total):
                return jsonify({
                    "finished": False,
                    "message": f"{watched}/{total}話まで視聴 — まだ完了していません。",
                }), 200
        except (TypeError, ValueError):
            return jsonify({"error": "watched_episodes が不正です"}), 400

    added = memory.mark_finished(current_user.id, item["mal_id"], item["title"])
    msg = (f"「{item['title']}」と{len(item['genres'])}個のジャンルを記録しました。"
           if added else f"「{item['title']}」は既に記録済みです。")
    return jsonify({
        "finished": True,
        "message": msg,
        "memory": _memory_payload(current_user.id),
    })


@app.route("/api/memory")
@login_required
def api_memory():
    return jsonify(_memory_payload(current_user.id))


@app.route("/api/memory/reset", methods=["POST"])
@login_required
def api_memory_reset():
    memory.reset(current_user.id)
    return jsonify(_memory_payload(current_user.id))


@app.route("/api/recommend")
@login_required
def api_recommend():
    scores = memory.genre_scores(current_user.id, REC.genres_of)
    finished_ids = [it["mal_id"] for it in memory.finished_list(current_user.id)]
    recs = REC.recommend_by_genre_scores(scores, exclude_ids=finished_ids, n=18)
    return jsonify({
        "top_genres": memory.top_genres(scores),
        "recommendations": recs,
    })


def _memory_payload(user_id):
    scores = memory.genre_scores(user_id, REC.genres_of)
    return {
        "finished": memory.finished_list(user_id),
        "genre_score": scores,
        "top_genres": memory.top_genres(scores),
    }


if __name__ == "__main__":
    # Chạy local: python app.py. Trên Render dùng gunicorn (xem Procfile/render.yaml).
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    app.run(debug=debug, use_reloader=False, host=host, port=port)
