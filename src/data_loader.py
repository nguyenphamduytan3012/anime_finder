"""Load & clean the MyAnimeList anime dataset.

Quy ước (xem CLAUDE.md):
- genres phân tách bằng ký tự '|'
- dedup theo mal_id
- xử lý missing: genres/themes fillna(''), episodes có thể NaN
"""
import os
import re
import unicodedata

import pandas as pd

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "anime_dataset.csv")


def split_genres(value):
    """'Action|Sci-Fi' -> ['Action', 'Sci-Fi']; NaN/'' -> []."""
    if not isinstance(value, str) or not value.strip():
        return []
    return [g.strip() for g in value.split("|") if g.strip()]


# ===== Chuẩn hoá text cho tìm kiếm theo TÊN (tiếng Nhật + tiếng Anh) =====
# Mục tiêu: gõ "進撃の巨人" / "shingeki" / "Attack on Titan" / "ｱﾀｯｸ" đều khớp.
_NON_WORD_RE = re.compile(r"[^0-9a-z぀-ヿ一-鿿]+")


def _katakana_to_hiragana(text):
    """カタカナ -> ひらがな (để 'ガンダム' và 'がんだむ' khớp nhau)."""
    out = []
    for ch in text:
        code = ord(ch)
        # dải Katakana ゠-ヶ (0x30A1-0x30F6) -> Hiragana (-0x60)
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)


def normalize_search_text(value):
    """Chuẩn hoá chuỗi để so khớp: NFKC → lowercase → katakana→hiragana → bỏ ký tự thừa.

    - NFKC: nửa-độ-rộng ｱ → ア, chữ số/chữ cái full-width → half-width
    - bỏ khoảng trắng, dấu câu (: - ~ ・ …) để "Re:Zero" khớp "re zero"
    """
    if not isinstance(value, str) or not value:
        return ""
    text = unicodedata.normalize("NFKC", value).lower()
    text = _katakana_to_hiragana(text)
    return _NON_WORD_RE.sub("", text)


def load_anime(path=DATA_PATH):
    """Đọc CSV, làm sạch, trả về DataFrame đã sẵn sàng cho recommender."""
    df = pd.read_csv(path, encoding="utf-8")

    # Bỏ dòng trùng mal_id (vd 64012 xuất hiện 2 lần)
    df = df.drop_duplicates(subset="mal_id").reset_index(drop=True)

    # Chuẩn hoá các cột text dùng để lọc / gợi ý
    for col in ["genres", "themes", "demographics", "type", "source"]:
        if col in df.columns:
            df[col] = df[col].fillna("")

    # Bỏ toàn bộ anime gắn nhãn Hentai (yêu cầu chủ dự án — làm sạch portfolio)
    df = df[~df["genres"].str.contains("Hentai", na=False)].reset_index(drop=True)

    # title_english trống -> dùng title gốc
    df["display_title"] = df["title_english"].where(
        df["title_english"].notna() & (df["title_english"] != ""), df["title"]
    )

    # Danh sách genre dạng list cho mỗi anime
    df["genre_list"] = df["genres"].apply(split_genres)
    df["theme_list"] = df["themes"].apply(split_genres)

    # ---- Index tìm kiếm theo TÊN (tiếng Nhật + tiếng Anh) ----
    # Giữ 3 cột tên riêng biệt để chấm điểm khớp, và 1 cột gộp đã chuẩn hoá để lọc nhanh.
    for col in ["title", "title_english", "title_japanese"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("")

    df["search_romaji"] = df["title"].apply(normalize_search_text)
    df["search_english"] = df["title_english"].apply(normalize_search_text)
    df["search_japanese"] = df["title_japanese"].apply(normalize_search_text)
    # '|' làm dấu ngăn để không khớp nhầm qua ranh giới giữa 2 tên
    df["search_all"] = (
        df["search_romaji"] + "|" + df["search_english"] + "|" + df["search_japanese"]
    )

    # Chuỗi feature cho TF-IDF: nhân đôi genres để genres có trọng số cao hơn themes/type
    df["features"] = (
        df["genres"].str.replace("|", " ", regex=False) + " "
        + df["genres"].str.replace("|", " ", regex=False) + " "
        + df["themes"].str.replace("|", " ", regex=False) + " "
        + df["type"]
    ).str.strip()

    # Ép kiểu số an toàn cho việc xếp hạng
    for col in ["score", "scored_by", "members", "popularity", "episodes", "favorites"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def all_genres(df):
    """Danh sách tất cả genre (đã loại trùng) kèm số lượng, sắp theo độ phổ biến."""
    counts = df.explode("genre_list")["genre_list"].value_counts()
    counts = counts[counts.index != ""]
    return [{"name": g, "count": int(c)} for g, c in counts.items()]


if __name__ == "__main__":
    d = load_anime()
    print("Rows:", len(d))
    print("Genres:", len(all_genres(d)))
    print(d[["mal_id", "display_title", "genre_list", "episodes", "score"]].head())
