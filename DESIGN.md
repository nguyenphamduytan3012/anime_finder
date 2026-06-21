# 🎨 Hệ thống Màu sắc & Dynamic Theming

Website **đổi màu/phong cách động theo thể loại (genre)** người dùng đang chọn. Có 4 trạng thái:
**Trang chủ (Neutral)** + 3 nhóm thể loại: **Action/Fantasy**, **Romance/Học đường**, **Horror/Bí ẩn**.

Khi user chọn genre → app áp dụng theme tương ứng (đổi `--bg`, `--primary`, `--secondary`, font, hiệu ứng). Nên triển khai bằng **CSS variables + class `theme-*` trên `<body>`**, đổi class theo genre đã chọn.

---

## 1. Trang chủ — Base Neutral (Xám than & Xanh sâu)
**Mục tiêu:** nền tảng vững chãi, chuyên nghiệp, làm nổi bật poster anime.

| Thành phần | Mã Hex | Ghi chú |
|---|---|---|
| Nền chính (Background) | `#121417` | Deep Charcoal |
| Nền phụ (Surface/Card) | `#1E2126` | Lighter Grey (thẻ phim) |
| Màu nhấn (Accent) | `#3B82F6` | Electric Blue |
| Văn bản chính | `#FFFFFF` | Pure White |
| Văn bản phụ | `#9CA3AF` | Muted Grey |

---

## 2. Action & Fantasy — Gaming / Cyberpunk Neon
**Mục tiêu:** mạnh mẽ, năng động, tương lai (Cyberpunk/Neon).
**Genre map:** Action, Adventure, Fantasy, Sci-Fi, Super Power, Mecha, Military.

| Thành phần | Mã Hex | Ghi chú |
|---|---|---|
| Nền (Gradient Base) | `#0F051D` | Deep Purple Black |
| Màu chủ đạo (Primary) | `#FF0055` | Neon Pink/Red |
| Màu bổ trợ (Secondary) | `#00F2FF` | Cyber Cyan |
| Glow / Shadow | `rgba(255, 0, 85, 0.5)` | Phát sáng cho nút bấm |
| Font | `M PLUS 1p` (800) | Gothic Nhật, dày, cứng cáp |

---

## 3. Romance & Học đường — Vibrant / Soft
**Mục tiêu:** rực rỡ, nhẹ nhàng, tích cực, ấm áp.
**Genre map:** Romance, Slice of Life, School, Shoujo, Comedy (lãng mạn), Music.

| Thành phần | Mã Hex | Ghi chú |
|---|---|---|
| Nền (Main BG) | `#FFF5F7` | Soft Sakura White |
| Màu chủ đạo (Primary) | `#FF85A2` | Pastel Pink |
| Màu bổ trợ (Secondary) | `#70D6FF` | Sky Blue |
| Văn bản (Text) | `#4A4A4A` | Dark Grey (tránh đen thuần) |
| Font | `M PLUS Rounded 1c` | Bo tròn, dễ thương |

---

## 4. Horror & Bí ẩn — Dark / Mystic
**Mục tiêu:** u ám, kịch tính, tò mò, hơi đáng sợ.
**Genre map:** Horror, Mystery, Thriller, Supernatural, Psychological, Demons, Gore.

| Thành phần | Mã Hex | Ghi chú |
|---|---|---|
| Nền chính (Background) | `#050505` | Absolute Black |
| Màu nhấn (Accent) | `#8B0000` | Blood Red |
| Màu bổ trợ (Secondary) | `#4B0082` | Indigo |
| Hiệu ứng đặc biệt | `Vignette` | Tối dần ở 4 góc màn hình |
| Font | `Hina Mincho` | Mincho Nhật, thanh mảnh, u ám |

---

## Ghi chú triển khai
- Một anime có nhiều genre → **chọn theme theo genre ưu tiên cao nhất** trong danh sách (thứ tự ưu tiên: Horror > Action/Fantasy > Romance > Neutral), hoặc theo genre user vừa chọn để tìm.
- Fonts lấy từ **Google Fonts**, dùng **font Nhật có hỗ trợ tiếng Việt**: `M PLUS 1p`, `M PLUS Rounded 1c`, `Hina Mincho`. (Các font Nhật như Mochiy Pop, Zen Maru, Creepster… KHÔNG có glyph tiếng Việt → vỡ dấu, không dùng.)
- Hiệu ứng glow = `box-shadow` với màu glow; vignette = lớp overlay `radial-gradient` phủ toàn màn hình.
- Mọi màu nên khai báo dưới dạng **CSS custom properties** để chuyển theme mượt (`transition` trên `background-color`/`color`).
