"""Load & clean the MyAnimeList anime dataset.

Quy ước (xem CLAUDE.md):
- genres phân tách bằng ký tự '|'
- dedup theo mal_id
- xử lý missing: genres/themes fillna(''), episodes có thể NaN
"""
import os
import pandas as pd

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "anime_dataset.csv")


def split_genres(value):
    """'Action|Sci-Fi' -> ['Action', 'Sci-Fi']; NaN/'' -> []."""
    if not isinstance(value, str) or not value.strip():
        return []
    return [g.strip() for g in value.split("|") if g.strip()]


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
