"""Khởi tạo SQLAlchemy (đối tượng db dùng chung toàn app).

Tách riêng để tránh import vòng: models.py và app.py đều import `db` từ đây.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def normalize_db_url(url):
    """Chuẩn hoá DATABASE_URL về driver psycopg2.

    Render/Heroku cấp URL dạng 'postgres://...' — SQLAlchemy 2.x không nhận
    scheme này, cần 'postgresql+psycopg2://...'.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url
