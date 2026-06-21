# Hướng dẫn: Xây dựng Anime Recommendation System
### Collaborative Filtering + Content-Based Filtering (Hybrid)

> **Mục tiêu cuối:** Một web app demo nhỏ, nơi người dùng chọn một anime họ thích, hệ thống gợi ý ra 5-10 anime tương tự + một hệ thống gợi ý dựa trên rating của user khác. Đẩy code lên GitHub với README chuyên nghiệp.

**Thời gian gợi ý:** 3-4 tuần, làm song song với khóa Andrew Ng (khoảng 1-1.5 giờ/buổi, 3-4 buổi/tuần).

---

## 0. Chuẩn bị môi trường

```bash
# Tạo virtual environment
python -m venv anime-rec-env
source anime-rec-env/bin/activate   # Mac/Linux
# anime-rec-env\Scripts\activate    # Windows

# Cài thư viện cần thiết
pip install pandas numpy scikit-learn scikit-surprise streamlit matplotlib seaborn
```

> 💡 Nếu `scikit-surprise` lỗi khi cài trên Windows, cần cài `Microsoft C++ Build Tools` trước, hoặc dùng Google Colab để tránh vấn đề môi trường hoàn toàn.

---

## 1. Dataset

Dùng dataset **MyAnimeList** trên Kaggle — rất phổ biến, sạch tương đối, có đủ 2 phần cần thiết:

- **anime.csv** — thông tin anime (genre, type, episodes, rating, synopsis)
- **rating.csv** hoặc **animelist.csv** — lịch sử rating của user (user_id, anime_id, rating)

Tìm trên Kaggle với từ khóa: `"Anime Recommendation Database"` hoặc `"MyAnimeList Dataset"`. Download và đặt vào thư mục `data/`.

```python
import pandas as pd

anime = pd.read_csv("data/anime.csv")
ratings = pd.read_csv("data/rating.csv")

print(anime.shape, ratings.shape)
print(anime.head())
print(ratings.head())
```

---

## 2. Phase 1 — EDA (Exploratory Data Analysis)

Trước khi xây model, hiểu dữ liệu của bạn. Đây cũng là phần dễ nhất để bắt đầu.

```python
# Kiểm tra missing values
print(anime.isnull().sum())

# Phân bố rating
import matplotlib.pyplot as plt
anime['rating'].hist(bins=30)
plt.title("Distribution of Anime Ratings")
plt.show()

# Top 10 genre phổ biến nhất
genre_counts = anime['genre'].str.split(', ').explode().value_counts()
print(genre_counts.head(10))

# Loại bỏ rating = -1 (nghĩa là user xem nhưng không rate)
ratings = ratings[ratings['rating'] != -1]
```

**Output cần có:** vài chart đơn giản (distribution rating, top genres, số lượng anime theo type TV/Movie/OVA). Lưu lại các hình này — sẽ dùng cho README sau.

---

## 3. Phase 2 — Content-Based Filtering

**Ý tưởng:** Nếu bạn thích anime A, gợi ý những anime "giống" A về nội dung (genre, synopsis, type).

### 3.1. Xử lý văn bản (genres + synopsis)

```python
from sklearn.feature_extraction.text import TfidfVectorizer

# Kết hợp genre + type thành một chuỗi "features"
anime['genre'] = anime['genre'].fillna('')
anime['features'] = anime['genre'] + ' ' + anime['type'].fillna('')

tfidf = TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf.fit_transform(anime['features'])

print(tfidf_matrix.shape)  # (số anime, số từ vựng)
```

### 3.2. Tính độ tương đồng (Cosine Similarity)

```python
from sklearn.metrics.pairwise import cosine_similarity

cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

# Tạo mapping từ tên anime -> index
indices = pd.Series(anime.index, index=anime['name']).drop_duplicates()

def get_content_recommendations(title, n=10):
    idx = indices[title]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:n+1]  # bỏ chính nó
    anime_indices = [i[0] for i in sim_scores]
    return anime['name'].iloc[anime_indices]

print(get_content_recommendations("Naruto"))
```

> 🎯 **Hiểu bản chất:** TF-IDF biến genre/synopsis thành vector số. Cosine similarity đo "góc" giữa 2 vector — góc nhỏ = giống nhau. Đây chính là kỹ thuật nền tảng của rất nhiều hệ thống search & recommendation thực tế.

---

## 4. Phase 3 — Collaborative Filtering

**Ý tưởng:** Nếu nhiều user có gu giống bạn đã thích anime B, gợi ý B cho bạn — không cần biết B nói về gì.

Dùng thư viện **Surprise** với thuật toán **SVD (Matrix Factorization)** — chuẩn công nghiệp, đơn giản nhưng hiệu quả.

```python
from surprise import SVD, Dataset, Reader
from surprise.model_selection import train_test_split, cross_validate

# Surprise cần format: user, item, rating
reader = Reader(rating_scale=(1, 10))
data = Dataset.load_from_df(ratings[['user_id', 'anime_id', 'rating']], reader)

# Train/test split
trainset, testset = train_test_split(data, test_size=0.2, random_state=42)

# Train model SVD
model = SVD(n_factors=50, random_state=42)
model.fit(trainset)

# Đánh giá
predictions = model.test(testset)
from surprise import accuracy
accuracy.rmse(predictions)
```

### 4.1. Gợi ý cho một user cụ thể

```python
def get_collab_recommendations(user_id, n=10):
    # Lấy danh sách anime user chưa xem
    watched = ratings[ratings['user_id'] == user_id]['anime_id'].tolist()
    not_watched = anime[~anime['anime_id'].isin(watched)]['anime_id']

    predictions = []
    for anime_id in not_watched:
        pred = model.predict(user_id, anime_id)
        predictions.append((anime_id, pred.est))

    predictions.sort(key=lambda x: x[1], reverse=True)
    top_ids = [p[0] for p in predictions[:n]]
    return anime[anime['anime_id'].isin(top_ids)]['name']

print(get_collab_recommendations(user_id=5))
```

> 🎯 **Hiểu bản chất:** SVD "phân rã" ma trận user-item thành các yếu tố ẩn (latent factors) — ví dụ ngầm hiểu "mức độ thích action", "mức độ thích romance" của từng user và từng anime, dù không có nhãn rõ ràng nào nói vậy.

---

## 5. Phase 4 — Hybrid Recommender (Kết hợp 2 phương pháp)

Đây là phần làm portfolio của bạn **nổi bật hẳn** — vì hầu hết sinh viên chỉ làm 1 trong 2.

```python
def hybrid_recommend(user_id, title, n=10, content_weight=0.5):
    # Lấy gợi ý content-based (set lớn hơn để có không gian re-rank)
    content_recs = get_content_recommendations(title, n=30)
    content_anime_ids = anime[anime['name'].isin(content_recs)]['anime_id'].tolist()

    # Dự đoán rating collaborative cho các anime này
    scores = []
    for anime_id in content_anime_ids:
        pred = model.predict(user_id, anime_id)
        scores.append((anime_id, pred.est))

    scores.sort(key=lambda x: x[1], reverse=True)
    top_ids = [s[0] for s in scores[:n]]
    return anime[anime['anime_id'].isin(top_ids)]['name']
```

**Cách giải thích trong phỏng vấn:** "Tôi dùng content-based để tạo ra một candidate pool liên quan về nội dung, sau đó dùng collaborative filtering để re-rank theo sở thích cá nhân của user." — đây chính xác là cách nhiều hệ thống recommendation thực tế (Netflix, Spotify) hoạt động ở mức đơn giản hóa.

---

## 6. Phase 5 — Demo App với Streamlit

```python
# app.py
import streamlit as st

st.title("🎬 Anime Recommendation System")
st.write("Chọn một anime bạn thích, hệ thống sẽ gợi ý những anime tương tự!")

anime_list = anime['name'].dropna().unique()
selected = st.selectbox("Chọn anime:", sorted(anime_list))

if st.button("Gợi ý"):
    recs = get_content_recommendations(selected, n=10)
    st.subheader("Có thể bạn cũng sẽ thích:")
    for r in recs:
        st.write(f"- {r}")
```

Chạy local:
```bash
streamlit run app.py
```

---

## 7. Phase 6 — Deploy (miễn phí)

Lựa chọn đơn giản nhất: **Streamlit Community Cloud**

1. Push code lên GitHub (bao gồm `app.py`, `requirements.txt`, và file model/data đã xử lý — nếu data quá lớn, dùng sample nhỏ hơn ~5000 anime)
2. Vào [share.streamlit.io](https://share.streamlit.io), connect với GitHub repo
3. Deploy — có link demo trực tiếp để dán vào CV/LinkedIn

```txt
# requirements.txt
pandas
numpy
scikit-learn
scikit-surprise
streamlit
```

---

## 8. README Template (Tiếng Anh — quan trọng cho CV)

```markdown
# Anime Recommendation System

A hybrid recommendation system combining content-based filtering (TF-IDF +
cosine similarity) and collaborative filtering (SVD matrix factorization)
to recommend anime titles.

## 🎯 Problem
With over 15,000 anime titles available, users struggle to discover new
shows that match their taste. This project builds a recommender that
suggests titles based on both content similarity and user rating patterns.

## 🛠 Approach
- **Content-Based**: TF-IDF vectorization of genre/type metadata + cosine
  similarity to find similar anime.
- **Collaborative Filtering**: SVD matrix factorization (Surprise library)
  trained on ~7M user ratings.
- **Hybrid**: Content similarity generates candidates, collaborative
  filtering re-ranks by predicted user preference.

## 📊 Results
- RMSE on test set: X.XX
- Demo: [live link]

## 🔍 Tech Stack
Python, Pandas, Scikit-learn, Surprise, Streamlit

## 💡 Lessons Learned
[Viết 2-3 câu về điều bạn học được — khó khăn gì, cách giải quyết ra sao]

## 🚀 Future Improvements
- Deep learning-based embeddings (Neural Collaborative Filtering)
- Cold-start handling for new users
```

> 📌 Phần "Lessons Learned" và "Future Improvements" **rất quan trọng** — nó cho thấy bạn hiểu sâu, không chỉ copy code.

---

## 9. Lộ trình theo tuần

| Tuần | Việc cần làm |
|------|--------------|
| Tuần 1 | Download dataset, EDA, vẽ chart, viết nhận xét |
| Tuần 2 | Xây content-based filtering, test với vài anime quen |
| Tuần 3 | Xây collaborative filtering (SVD), đánh giá RMSE |
| Tuần 4 | Hybrid + Streamlit app + deploy + viết README |

---

## 10. Mở rộng (nếu muốn nâng cấp sau này)

- Thử **Neural Collaborative Filtering** (dùng embedding + neural net thay SVD) — liên kết với phần Neural Networks trong khóa Andrew Ng
- Thêm **cold-start**: gợi ý cho user mới chưa có rating (dựa vào content-based thuần)
- Thêm **explainability**: hiển thị "vì sao gợi ý cái này" (ví dụ: "vì bạn thích Naruto, đây cũng là anime hành động/siêu nhiên")

---

**Chúc bạn build vui vẻ! Nếu vướng ở bước nào, hỏi mình ngay — mình có thể debug code cùng bạn.**
