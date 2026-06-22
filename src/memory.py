"""Bộ nhớ thể loại yêu thích — theo TỪNG user, lưu trong DB.

Cơ chế (xem CLAUDE.md mục 1):
- User đánh dấu 'đã xem hết' một anime -> thêm 1 dòng vào finished_anime.
- genre_score = đếm tần suất genre trên TẤT CẢ bộ đã xem hết của user đó,
  tính on-the-fly bằng cách tra genres của từng mal_id trong dataset.
- Genre điểm cao nhất = thể loại yêu thích -> dùng để gợi ý.

`genres_of` là một callable mal_id -> list[str] (do recommender cung cấp),
giúp memory KHÔNG phụ thuộc trực tiếp vào pandas/dataset.
"""
from .database import db
from .models import FinishedAnime


def mark_finished(user_id, mal_id, title):
    """Thêm anime vào danh sách đã xem hết của user. Trả True nếu mới thêm."""
    exists = FinishedAnime.query.filter_by(user_id=user_id, mal_id=mal_id).first()
    if exists:
        return False
    db.session.add(FinishedAnime(user_id=user_id, mal_id=int(mal_id), title=title))
    db.session.commit()
    return True


def finished_list(user_id):
    rows = (FinishedAnime.query
            .filter_by(user_id=user_id)
            .order_by(FinishedAnime.finished_at.desc())
            .all())
    return [{"mal_id": r.mal_id, "title": r.title} for r in rows]


def genre_scores(user_id, genres_of):
    """Đếm tần suất genre trên các bộ user đã xem hết. genres_of: mal_id -> list."""
    scores = {}
    for r in FinishedAnime.query.filter_by(user_id=user_id).all():
        for g in genres_of(r.mal_id):
            scores[g] = scores.get(g, 0) + 1
    return scores


def top_genres(scores, k=5):
    items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"name": g, "score": s} for g, s in items[:k]]


def reset(user_id):
    """Xoá toàn bộ lịch sử đã xem hết của user."""
    FinishedAnime.query.filter_by(user_id=user_id).delete()
    db.session.commit()
