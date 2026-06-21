"""Anime Favorite Finder — Flask backend.

Serve UI + REST API cho:
- lọc anime theo genre
- gợi ý anime tương tự (content-based)
- ghi nhớ thể loại yêu thích khi user xem hết một bộ
- gợi ý anime dựa trên 'gu' đã ghi nhớ
"""
from flask import Flask, jsonify, render_template, request

from src.data_loader import load_anime, all_genres
from src.recommender import AnimeRecommender
from src import memory

app = Flask(__name__)

print("Loading dataset…")
DF = load_anime()
REC = AnimeRecommender(DF)
GENRES = all_genres(DF)
print(f"Ready: {len(DF)} anime, {len(GENRES)} genres.")


@app.route("/")
def index():
    return render_template("index.html")


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


@app.route("/api/finish", methods=["POST"])
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

    data = memory.mark_finished(item["mal_id"], item["title"], item["genres"])
    return jsonify({
        "finished": True,
        "message": f"「{item['title']}」と{len(item['genres'])}個のジャンルを記録しました。",
        "memory": _memory_payload(data),
    })


@app.route("/api/memory")
def api_memory():
    return jsonify(_memory_payload(memory.load()))


@app.route("/api/memory/reset", methods=["POST"])
def api_memory_reset():
    return jsonify(_memory_payload(memory.reset()))


@app.route("/api/recommend")
def api_recommend():
    data = memory.load()
    finished_ids = [it["mal_id"] for it in data["finished"]]
    recs = REC.recommend_by_genre_scores(
        data["genre_score"], exclude_ids=finished_ids, n=18
    )
    return jsonify({
        "top_genres": memory.top_genres(data),
        "recommendations": recs,
    })


def _memory_payload(data):
    return {
        "finished": data["finished"],
        "genre_score": data["genre_score"],
        "top_genres": memory.top_genres(data),
    }


if __name__ == "__main__":
    import os
    # Chạy local: python app.py. Trên Render dùng gunicorn (xem Procfile/render.yaml).
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    app.run(debug=debug, use_reloader=False, host=host, port=port)
