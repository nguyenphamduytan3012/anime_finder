"""Content-based recommender + lọc theo genre.

- TF-IDF trên cột `features` (genres x2 + themes + type)
- Độ tương đồng: cosine, tính theo nhu cầu (1 anime vs toàn bộ) để tránh ma trận 30k x 30k.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


class AnimeRecommender:
    def __init__(self, df):
        self.df = df.reset_index(drop=True)
        self.tfidf = TfidfVectorizer(token_pattern=r"[A-Za-z][A-Za-z\-]+")
        self.matrix = self.tfidf.fit_transform(self.df["features"])
        # map mal_id -> vị trí dòng
        self.id_to_idx = {int(m): i for i, m in enumerate(self.df["mal_id"])}

    # ---------- helpers ----------
    def _to_records(self, sub):
        cols = [
            "mal_id", "display_title", "title", "type", "episodes",
            "score", "members", "genre_list", "image_url", "synopsis",
        ]
        recs = []
        for _, r in sub[cols].iterrows():
            recs.append({
                "mal_id": int(r["mal_id"]),
                "title": r["display_title"],
                "original_title": r["title"],
                "type": r["type"] or "",
                "episodes": None if np_isnan(r["episodes"]) else int(r["episodes"]),
                "score": None if np_isnan(r["score"]) else round(float(r["score"]), 2),
                "members": 0 if np_isnan(r["members"]) else int(r["members"]),
                "genres": r["genre_list"],
                "image_url": r["image_url"] if isinstance(r["image_url"], str) else "",
                "synopsis": (r["synopsis"][:300] + "…") if isinstance(r["synopsis"], str) and len(r["synopsis"]) > 300 else (r["synopsis"] if isinstance(r["synopsis"], str) else ""),
            })
        return recs

    STATUS_MAP = {
        "finished": "Finished Airing",
        "airing": "Currently Airing",
        "upcoming": "Not yet aired",
    }

    # ---------- API ----------
    def search(self, genre, page=1, page_size=30, sort="score",
               type_filter="", status="", year="", min_scored_by=50):
        """Lọc anime theo genre + bộ lọc, có sắp xếp & phân trang.

        Trả về dict: items, total, page, page_size, total_pages.
        """
        mask = self.df["genre_list"].apply(lambda gs: genre in gs)
        sub = self.df[mask].copy()

        if type_filter:
            sub = sub[sub["type"] == type_filter]
        if status and status in self.STATUS_MAP:
            sub = sub[sub["status"] == self.STATUS_MAP[status]]
        if year:
            try:
                sub = sub[sub["year"] == int(year)]
            except (ValueError, TypeError):
                pass

        sub = self._sort(sub, sort, min_scored_by)

        total = len(sub)
        page_size = max(1, int(page_size))
        page = max(1, int(page))
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, total_pages)
        start = (page - 1) * page_size
        return {
            "items": self._to_records(sub.iloc[start:start + page_size]),
            "total": int(total),
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def _sort(self, sub, sort, min_scored_by):
        if sort == "score":
            sub = sub.copy()
            sub["_s"] = sub["score"].where(sub["scored_by"].fillna(0) >= min_scored_by)
            return sub.sort_values(["_s", "members"], ascending=False, na_position="last")
        if sort == "popularity":  # popularity: số nhỏ = phổ biến hơn
            return sub.sort_values("popularity", ascending=True, na_position="last")
        if sort == "members":
            return sub.sort_values("members", ascending=False, na_position="last")
        if sort == "favorites":
            return sub.sort_values("favorites", ascending=False, na_position="last")
        if sort == "newest":
            return sub.sort_values("aired_from", ascending=False, na_position="last")
        if sort == "title":
            return sub.sort_values("display_title", ascending=True, na_position="last")
        return sub

    def get_one(self, mal_id):
        idx = self.id_to_idx.get(int(mal_id))
        if idx is None:
            return None
        return self._to_records(self.df.iloc[[idx]])[0]

    def similar(self, mal_id, n=12):
        """Anime tương tự theo nội dung (cosine similarity)."""
        idx = self.id_to_idx.get(int(mal_id))
        if idx is None:
            return []
        sims = linear_kernel(self.matrix[idx], self.matrix).ravel()
        order = np.argsort(-sims)
        order = [i for i in order if i != idx][:n]
        return self._to_records(self.df.iloc[order])

    def recommend_by_genre_scores(self, genre_score, exclude_ids=None, n=18, min_scored_by=1000):
        """Gợi ý dựa trên 'gu' đã ghi nhớ: cộng điểm theo genre_score của user.

        Mỗi anime nhận điểm = tổng genre_score của các genre mà nó có.
        => anime trùng nhiều genre yêu thích nhất sẽ lên đầu.
        """
        if not genre_score:
            return []
        exclude_ids = set(exclude_ids or [])
        sub = self.df.copy()
        sub["match"] = sub["genre_list"].apply(
            lambda gs: sum(genre_score.get(g, 0) for g in gs)
        )
        sub = sub[(sub["match"] > 0) & (~sub["mal_id"].isin(exclude_ids))]
        sub["_score"] = sub["score"].where(sub["scored_by"].fillna(0) >= min_scored_by)
        sub = sub.sort_values(
            by=["match", "_score", "members"], ascending=False, na_position="last"
        )
        return self._to_records(sub.head(n))


def np_isnan(v):
    try:
        return v is None or (isinstance(v, float) and np.isnan(v))
    except TypeError:
        return False
