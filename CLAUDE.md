# CLAUDE.md

Tài liệu hướng dẫn cho Claude Code khi làm việc trong repo này. Viết bằng tiếng Việt để chủ dự án dễ theo dõi; code/lệnh giữ nguyên tiếng Anh.

## 1. Mục tiêu dự án

Một **web app gợi ý anime** (project portfolio cho phỏng vấn). Luồng sản phẩm mong muốn:

1. Người dùng **nhập / chọn một thể loại (genre)** → app hiển thị danh sách anime thuộc thể loại đó.
2. Khi người dùng chọn một anime → app **gợi ý thêm các anime tương tự** (content-based).
3. **Cơ chế ghi nhớ thể loại yêu thích (điểm khác biệt chính của dự án):**
   - Một anime có **nhiều genre**. Khi người dùng **xem hết** một bộ (đánh dấu "đã xem hết" / finished), app coi đó là tín hiệu *thích thật sự* → **lưu toàn bộ các genre của bộ đó vào bộ nhớ (memory)**.
   - Mỗi lần người dùng chọn/xem hết thêm anime khác → **tiếp tục cộng dồn các genre vào bộ nhớ**.
   - Bộ nhớ phải **so sánh nhiều lượt xem**, tìm ra **các genre lặp lại nhiều nhất** (overlap) → suy ra "gu" thật sự của user → ưu tiên gợi ý anime khớp với các genre đó.

> Tóm tắt cơ chế memory: `finished_anime[]` → trích `genres` → đếm tần suất từng genre (`genre_score{}`) → genre có điểm cao nhất = thể loại yêu thích → re-rank gợi ý theo các genre này.

4. **Dynamic theming (giao diện đổi màu theo thể loại):** Giao diện đổi **màu sắc + font + hiệu ứng** theo nhóm thể loại đang xem — 4 trạng thái: Trang chủ (Neutral), Action/Fantasy (Neon), Romance (Soft), Horror (Dark/Mystic). Chi tiết mã màu & font xem **[DESIGN.md](DESIGN.md)**.

## 2. Tài liệu tham khảo

- **[anime_recommendation_system_guide.md](anime_recommendation_system_guide.md)** — hướng dẫn gốc xây hệ thống hybrid recommender (Content-Based TF-IDF + Collaborative SVD + Streamlit). Dùng làm nền kỹ thuật. **Lưu ý:** guide giả định có file `rating.csv` (lịch sử rating của user) cho phần Collaborative Filtering — dataset hiện tại **chưa có** file này (xem mục 3). Phần memory ở mục 1 thay thế/bổ sung cho collaborative khi chưa có dữ liệu rating.
- **[DESIGN.md](DESIGN.md)** — hệ thống màu sắc & dynamic theming (4 theme theo thể loại). Tham chiếu khi build UI.

## 3. Dữ liệu (`data/`)

Dữ liệu cào từ **MyAnimeList (MAL)**.

### `data/anime_dataset.csv` — 30.075 dòng × 29 cột
Các cột quan trọng cho recommender:
- `mal_id`, `title`, `title_english`, `title_japanese`, `image_url`, `synopsis`
- `genres` — **chuỗi phân tách bằng `|`** (vd `Action|Adventure|Sci-Fi`). **Đây là cột lõi để lọc & gợi ý.**
- `themes`, `demographics` — bổ trợ cho genres.
- `type` (TV/Movie/OVA/ONA/Music...), `source`, `episodes`, `status`, `duration`, `rating`
- `score`, `scored_by`, `rank`, `popularity`, `members`, `favorites` — dùng để xếp hạng / tie-break.
- `season`, `year`, `studios`, `producers`, `licensors`

### `data/manga_dataset.csv` — 24 cột
Tương tự nhưng đặc thù manga: có `chapters`, `volumes`, `authors`, `serializations` thay cho các cột anime. **Hiện chưa dùng cho web app** — chỉ giữ để mở rộng sau.

### Lưu ý chất lượng dữ liệu (missing values đáng chú ý)
- `licensors` thiếu ~83%, `season`/`year` thiếu ~78%, `demographics` thiếu ~63%, `aired_to` thiếu ~61%.
- `score`/`scored_by` thiếu ~34% (10.183 dòng) → khi rank theo score phải `dropna`/`fillna`.
- `genres` thiếu 6.394 dòng (~21%) → khi lọc theo genre cần `fillna('')` rồi mới `.str.split('|')`.
- **Có dòng trùng `mal_id`** (vd `mal_id=64012` lặp 2 lần) → cần `drop_duplicates` theo `mal_id` khi cần.
- Phân tách genre là ký tự **`|`**, KHÔNG phải `, ` như trong guide gốc.

## 4. Trạng thái hiện tại của code

- **[main.py](main.py)** — script nháp, chỉ `read_csv` + `head()`.
- **[eda.ipynb](eda.ipynb)** — notebook EDA cơ bản: `shape`, `columns`, `isnull().sum()`. Chưa có chart.
- Chưa có app web, chưa có module recommender, chưa có `requirements.txt`.

## 5. Kiến trúc đề xuất (khi build)

Stack đã chốt: **Flask (backend Python) + HTML/CSS/JS (frontend)** — backend giữ recommender + memory bằng pandas/sklearn, frontend toàn quyền làm dynamic theming đúng [DESIGN.md] (Streamlit không đáp ứng được neon/vignette/custom font).

```
Favorite_anime/
├── data/                  # CSV gốc (giữ nguyên)
├── eda.ipynb              # phân tích, chart cho README
├── src/
│   ├── data_loader.py     # load + clean (parse genres bằng '|', dedup mal_id)
│   ├── recommender.py     # content-based: TF-IDF(genres+themes+type) + cosine similarity
│   └── memory.py          # cơ chế ghi nhớ genre yêu thích (mục 1) — đọc/ghi user_memory.json
├── templates/index.html   # giao diện chính
├── static/css/style.css   # 4 theme (CSS variables + class theme-*)
├── static/js/app.js       # gọi API, đổi theme theo genre, render anime
├── app.py                 # Flask: serve UI + REST API (/api/genres, /api/anime, /api/similar, /api/finish, /api/memory, /api/recommend)
└── requirements.txt
```

**Quyết định đã chốt với chủ dự án:**
- **Xác định "đã xem hết": theo số tập.** User nhập số tập đã xem cho một anime; nếu `số_tập_đã_xem >= episodes` (và `episodes` hợp lệ, không NaN) → coi là *finished* → trích `genres` của bộ đó cộng vào memory. Lưu ý nhiều bộ có `episodes = NaN` (839 dòng) hoặc đang phát sóng → cần xử lý riêng (cho phép user tự xác nhận hoặc bỏ qua).
- **Bộ nhớ lưu lâu dài bằng file JSON** (không dùng session tạm). `memory.py` đọc/ghi file vd `user_memory.json` với cấu trúc kiểu:
  ```json
  {
    "finished": [{"mal_id": 1, "title": "Cowboy Bebop", "genres": ["Action","Sci-Fi"]}],
    "genre_score": {"Action": 2, "Sci-Fi": 1}
  }
  ```
  Mỗi lần đánh dấu finished → cập nhật `finished[]` + cộng dồn `genre_score{}` → ghi lại file. Khi gợi ý → đọc `genre_score`, lấy các genre điểm cao nhất để re-rank.

## 6. Môi trường & lệnh

- OS: **Windows 11**, shell mặc định **PowerShell** (chú ý cú pháp). Bash tool dùng cho POSIX.
- Đường dẫn project chứa dấu tiếng Việt/space ("Nhập khẩu") → luôn quote path.
- CSV đọc bằng `encoding="utf-8"`.

```bash
# Môi trường ảo
python -m venv anime-rec-env
anime-rec-env\Scripts\activate        # Windows PowerShell

pip install -r requirements.txt       # flask, pandas, numpy, scikit-learn
# scikit-surprise chỉ cần nếu/khi có rating.csv cho collaborative filtering

python app.py                         # chạy app → http://127.0.0.1:5000
```

## 7. Quy ước screenshot (BẮT BUỘC)

**Mỗi khi build xong một thứ gì đó chạy được (app/trang/tính năng có giao diện), phải chụp màn hình kết quả và lưu vào folder `screenshot/`.**
- Đặt tên file mô tả: `screenshot/<tinh-nang>-<theme>.png` (vd `home-neutral.png`, `search-horror.png`).
- Nếu có dynamic theming → chụp đủ các theme đã build để minh hoạ (Neutral / Action / Romance / Horror).
- Các screenshot này cũng dùng cho README/CV sau này.

## 8. Quy ước khi làm việc

- Parse genre: `df['genres'].fillna('').str.split('|')` — luôn dùng `|`.
- Khi rank/gợi ý: ưu tiên `score` cao nhưng **lọc bỏ** dòng `scored_by` quá thấp (tránh điểm ảo); cân nhắc `popularity`/`members` để tie-break.
- **Ngôn ngữ UI = tiếng Nhật hoàn toàn** (đã chốt). Mọi chữ trên web là tiếng Nhật; tên genre map sang tiếng Nhật trong `app.js` (`GENRE_JP`), giá trị genre gửi API vẫn giữ tiếng Anh (khớp dữ liệu). Thông báo API (`/api/finish`) cũng tiếng Nhật. Giải thích cho chủ dự án vẫn dùng tiếng Việt; README cuối cùng nên có bản tiếng Anh cho CV.
- **Đã bỏ toàn bộ anime nhãn `Hentai`** ngay trong `data_loader.py` (yêu cầu chủ dự án) → còn ~28.318 dòng, 20 genre.
- "Đã xem hết" = theo số tập (`watched >= episodes`); memory lưu lâu dài bằng JSON theo user (đã chốt, xem mục 5).
- **`/api/anime` có phân trang + lọc:** params `genre, page, page_size(=30), sort(score|popularity|members|favorites|newest|title), type, status(finished|airing|upcoming), year` → trả `{items, total, page, page_size, total_pages}`. Frontend có thanh lọc (dưới tiêu đề "ジャンル：…") + thanh phân trang.
