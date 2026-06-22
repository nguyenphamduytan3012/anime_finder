"""Bảng dữ liệu (SQLAlchemy models).

- users: tài khoản người dùng (mật khẩu LƯU DẠNG BĂM, không bao giờ lưu thô).
- finished_anime: các bộ mỗi user đã xem hết (1 user -> nhiều dòng).

Lưu ý thiết kế: KHÔNG có bảng genre_score. Điểm gu được TÍNH on-the-fly từ
danh sách finished_anime + genres trong dataset (single source of truth).
'title' lưu kèm là denormalize có chủ đích để hiển thị nhanh, khỏi tra dataset.
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .database import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    finished = db.relationship(
        "FinishedAnime", backref="user",
        cascade="all, delete-orphan", lazy="dynamic",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class FinishedAnime(db.Model):
    __tablename__ = "finished_anime"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    mal_id = db.Column(db.Integer, nullable=False)        # tham chiếu anime trong dataset CSV
    title = db.Column(db.String(255))
    finished_at = db.Column(db.DateTime, default=datetime.utcnow)

    # chặn một user đánh dấu trùng cùng một anime
    __table_args__ = (
        db.UniqueConstraint("user_id", "mal_id", name="uq_user_anime"),
    )
