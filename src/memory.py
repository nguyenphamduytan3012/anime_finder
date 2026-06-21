"""Bộ nhớ thể loại yêu thích — lưu lâu dài bằng JSON.

Cơ chế (xem CLAUDE.md mục 1):
- User đánh dấu 'đã xem hết' một anime (watched_episodes >= episodes).
- Trích genres của anime đó -> cộng dồn vào genre_score.
- Genre có điểm cao nhất = thể loại yêu thích -> dùng để gợi ý.
"""
import json
import os
from threading import Lock

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "..", "user_memory.json")
_lock = Lock()


def _empty():
    return {"finished": [], "genre_score": {}}


def load(path=MEMORY_PATH):
    if not os.path.exists(path):
        return _empty()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("finished", [])
        data.setdefault("genre_score", {})
        return data
    except (json.JSONDecodeError, OSError):
        return _empty()


def save(data, path=MEMORY_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def mark_finished(mal_id, title, genres, path=MEMORY_PATH):
    """Đánh dấu một anime đã xem hết -> cộng genre vào bộ nhớ. Trả về memory mới."""
    with _lock:
        data = load(path)
        if any(item["mal_id"] == mal_id for item in data["finished"]):
            return data  # đã ghi nhớ rồi, không cộng trùng

        data["finished"].append({
            "mal_id": int(mal_id),
            "title": title,
            "genres": list(genres),
        })
        for g in genres:
            data["genre_score"][g] = data["genre_score"].get(g, 0) + 1
        save(data, path)
        return data


def top_genres(data, k=5):
    """k thể loại yêu thích nhất (điểm cao nhất)."""
    items = sorted(data["genre_score"].items(), key=lambda x: x[1], reverse=True)
    return [{"name": g, "score": s} for g, s in items[:k]]


def reset(path=MEMORY_PATH):
    with _lock:
        save(_empty(), path)
        return _empty()
