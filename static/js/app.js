"use strict";

// ===== Genre -> theme (xem DESIGN.md). Giá trị genre giữ tiếng Anh (khớp dữ liệu) =====
const THEME_MAP = {
  action: ["Action", "Adventure", "Fantasy", "Sci-Fi", "Super Power", "Mecha", "Military", "Martial Arts"],
  romance: ["Romance", "Slice of Life", "School", "Shoujo", "Comedy", "Music", "Josei"],
  horror: ["Horror", "Mystery", "Thriller", "Supernatural", "Psychological", "Demons", "Gore", "Dementia"],
};
const THEME_PRIORITY = ["horror", "action", "romance"];

// ===== Hiển thị tên tiếng Nhật cho genre / type =====
const GENRE_JP = {
  "Action": "アクション", "Adventure": "アドベンチャー", "Comedy": "コメディ", "Drama": "ドラマ",
  "Fantasy": "ファンタジー", "Sci-Fi": "SF", "Romance": "恋愛", "Slice of Life": "日常",
  "Supernatural": "超自然", "Mystery": "ミステリー", "Horror": "ホラー", "Sports": "スポーツ",
  "Suspense": "サスペンス", "Award Winning": "受賞作", "Avant Garde": "アヴァンギャルド",
  "Gourmet": "グルメ", "Ecchi": "エッチ", "Boys Love": "ボーイズラブ", "Girls Love": "ガールズラブ",
  "Erotica": "エロティカ",
};
const TYPE_JP = { "TV": "TV", "Movie": "映画", "OVA": "OVA", "ONA": "ONA", "Special": "スペシャル",
  "Music": "音楽", "TV Special": "TVスペシャル", "CM": "CM", "PV": "PV" };
const jpGenre = (g) => GENRE_JP[g] || g;
const jpType = (t) => TYPE_JP[t] || t || "?";

function themeForGenre(genre) {
  for (const t of THEME_PRIORITY) if (THEME_MAP[t].includes(genre)) return t;
  return "neutral";
}
const applyTheme = (theme) => (document.body.className = "theme-" + theme);

// ===== Helpers =====
const $ = (sel) => document.querySelector(sel);
const api = (url, opts) => fetch(url, opts).then((r) => r.json());
const PLACEHOLDER = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='150' height='225'><rect width='100%25' height='100%25' fill='%23333'/></svg>";

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), 3200);
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function cardHTML(a) {
  const img = a.image_url || PLACEHOLDER;
  const score = a.score ? `<div class="score-badge">★ ${a.score}</div>` : "";
  const eps = a.episodes ? `${a.episodes}話` : "?話";
  return `<div class="card" data-id="${a.mal_id}">
    ${score}
    <img loading="lazy" src="${img}" onerror="this.src='${PLACEHOLDER}'" alt="">
    <div class="card-body">
      <div class="card-title">${escapeHtml(a.title)}</div>
      <div class="card-meta"><span>${jpType(a.type)}</span><span>${eps}</span></div>
    </div>
  </div>`;
}

// ===== State =====
const state = { genre: null, page: 1, sort: "score", type: "", status: "", year: "" };

// ===== Auth =====
let CURRENT_USER = null;
let authMode = "login";

async function loadMe() {
  const me = await api("/api/me");
  CURRENT_USER = me.username;
  renderAuthBar();
}

function renderAuthBar() {
  const bar = $("#authBar");
  if (CURRENT_USER) {
    bar.innerHTML = `<span class="auth-hello">こんにちは、<b>${escapeHtml(CURRENT_USER)}</b></span>
      <button class="auth-btn" data-act="logout">ログアウト</button>`;
  } else {
    bar.innerHTML = `<button class="auth-btn" data-act="login">ログイン</button>
      <button class="auth-btn primary" data-act="register">新規登録</button>`;
  }
}

function openAuth(mode) {
  authMode = mode;
  $("#authError").textContent = "";
  $("#authUser").value = "";
  $("#authPass").value = "";
  $("#authTitle").textContent = mode === "login" ? "ログイン" : "新規登録";
  $("#authSubmit").textContent = mode === "login" ? "ログイン" : "登録する";
  $("#authSwitchText").textContent =
    mode === "login" ? "アカウントをお持ちでないですか？" : "既にアカウントをお持ちですか？";
  $("#authSwitch").textContent = mode === "login" ? "新規登録" : "ログイン";
  $("#authModal").classList.remove("hidden");
  $("#authUser").focus();
}

async function submitAuth(e) {
  e.preventDefault();
  const username = $("#authUser").value.trim();
  const password = $("#authPass").value;
  const res = await api("/api/" + authMode, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (res.error) {
    $("#authError").textContent = res.error;
    return;
  }
  CURRENT_USER = res.username;
  $("#authModal").classList.add("hidden");
  renderAuthBar();
  toast(authMode === "login" ? "ログインしました。" : "アカウントを作成しました。");
  refreshUserData();
}

async function logout() {
  await api("/api/logout", { method: "POST" });
  CURRENT_USER = null;
  renderAuthBar();
  renderLoginPrompt();
  toast("ログアウトしました。");
}

async function refreshUserData() {
  if (!CURRENT_USER) return renderLoginPrompt();
  renderMemory(await api("/api/memory"));
  loadRecommendations();
}

function renderLoginPrompt() {
  $("#topGenres").innerHTML = `<p class="hint">ログインすると、見終わったアニメから「好み」を記録できます。</p>`;
  $("#recoList").innerHTML = `<p class="hint">ログインすると、おすすめが表示されます。</p>`;
}

async function showGenre(genre) {
  state.genre = genre;
  state.page = 1;
  history.replaceState(null, "", "#genre=" + encodeURIComponent(genre));
  applyTheme(themeForGenre(genre));
  document.querySelectorAll(".chip").forEach((c) =>
    c.classList.toggle("active", c.dataset.genre === genre)
  );
  $("#resultTitle").textContent = `ジャンル：${jpGenre(genre)}`;
  $("#filterBar").classList.remove("hidden");
  await fetchAnime();
}

async function fetchAnime() {
  const grid = $("#animeGrid");
  grid.innerHTML = `<p class="hint">読み込み中…</p>`;
  $("#pagination").innerHTML = "";
  const q = new URLSearchParams({
    genre: state.genre, page: state.page, sort: state.sort,
    type: state.type, status: state.status, year: state.year,
  });
  const data = await api(`/api/anime?${q}`);
  if (!data.items || !data.items.length) {
    grid.innerHTML = `<p class="hint">該当するアニメが見つかりません。</p>`;
    return;
  }
  grid.innerHTML = data.items.map(cardHTML).join("");
  renderPagination(data.total_pages, data.page, data.total);
}

function renderPagination(totalPages, page, total) {
  const box = $("#pagination");
  if (totalPages <= 1) {
    box.innerHTML = `<div class="info">全 ${total.toLocaleString()} 件</div>`;
    return;
  }
  const btn = (p, label, o = {}) =>
    `<button data-page="${p}" class="${o.active ? "active" : ""}" ${o.disabled ? "disabled" : ""}>${label ?? p}</button>`;
  let html = `<div class="info">全 ${total.toLocaleString()} 件 ・ ${page} / ${totalPages} ページ</div>`;
  html += btn(1, "«", { disabled: page === 1 });
  html += btn(page - 1, "‹", { disabled: page === 1 });
  const start = Math.max(1, page - 2), end = Math.min(totalPages, page + 2);
  if (start > 1) html += `<span class="dots">…</span>`;
  for (let p = start; p <= end; p++) html += btn(p, null, { active: p === page });
  if (end < totalPages) html += `<span class="dots">…</span>`;
  html += btn(page + 1, "›", { disabled: page === totalPages });
  html += btn(totalPages, "»", { disabled: page === totalPages });
  box.innerHTML = html;
}

// ===== Modal chi tiết =====
async function openDetail(malId) {
  const a = await api(`/api/anime/${malId}`);
  const total = a.episodes;
  const epsLabel = total ? `全${total}話` : "話数不明";
  $("#modalContent").innerHTML = `
    <div class="detail-head">
      <img src="${a.image_url || PLACEHOLDER}" onerror="this.src='${PLACEHOLDER}'" alt="">
      <div class="detail-info">
        <h2>${escapeHtml(a.title)}</h2>
        <div class="card-meta" style="gap:14px">
          <span>${jpType(a.type)}</span><span>★ ${a.score ?? "?"}</span><span>${epsLabel}</span>
        </div>
        <div class="detail-genres">${a.genres.map((g) => `<span>${jpGenre(g)}</span>`).join("")}</div>
      </div>
    </div>
    <p class="detail-synopsis">${escapeHtml(a.synopsis) || "あらすじはありません。"}</p>

    <div class="finish-box">
      <label>📺 何話まで見ましたか？（見終わると好みのジャンルを記録します）</label>
      <div class="finish-row">
        <input id="watchedInput" type="number" min="0" value="${total || 1}" />
        <span class="card-meta">/ ${total ?? "?"}</span>
        <button class="btn-primary" id="finishBtn">見終わった！</button>
      </div>
    </div>

    <div class="similar-title">🎯 似ているアニメ</div>
    <div class="grid">${a.similar.map(cardHTML).join("")}</div>`;

  $("#finishBtn").onclick = () => finishAnime(a.mal_id);
  $("#modal").classList.remove("hidden");
}

async function finishAnime(malId) {
  const watched = Number($("#watchedInput").value);
  const res = await api("/api/finish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mal_id: malId, watched_episodes: watched }),
  });
  if (res.auth_required) {
    $("#modal").classList.add("hidden");
    openAuth("login");
    toast("記録するにはログインが必要です。");
    return;
  }
  toast(res.message || (res.finished ? "記録しました！" : "まだ完了していません。"));
  if (res.finished) {
    renderMemory(res.memory);
    loadRecommendations();
    $("#modal").classList.add("hidden");
  }
}

// ===== Bộ nhớ + gợi ý =====
function renderMemory(mem) {
  const top = mem.top_genres || [];
  const box = $("#topGenres");
  if (!top.length) {
    box.innerHTML = `<p class="hint">まだデータがありません。アニメを見終わると記録が始まります。</p>`;
    return;
  }
  const max = Math.max(...top.map((g) => g.score));
  box.innerHTML = top.map((g) => `
    <div class="genre-row">
      <span class="name">${jpGenre(g.name)}</span>
      <div class="bar"><span style="width:${(g.score / max) * 100}%"></span></div>
      <span class="val">${g.score}</span>
    </div>`).join("");
}

async function loadRecommendations() {
  const data = await api("/api/recommend");
  const box = $("#recoList");
  if (data.auth_required || !data.recommendations) return renderLoginPrompt();
  if (!data.recommendations.length) {
    box.innerHTML = `<p class="hint">アニメを数本見終わると、おすすめが表示されます。</p>`;
    return;
  }
  box.innerHTML = data.recommendations.slice(0, 10).map((a) => `
    <div class="reco-item" data-id="${a.mal_id}">
      <img src="${a.image_url || PLACEHOLDER}" onerror="this.src='${PLACEHOLDER}'" alt="">
      <div>
        <div class="r-title">${escapeHtml(a.title)}</div>
        <div class="r-meta">★ ${a.score ?? "?"} · ${a.genres.slice(0, 3).map(jpGenre).join("、")}</div>
      </div>
    </div>`).join("");
}

// ===== Init =====
async function init() {
  const genres = await api("/api/genres");
  $("#genreChips").innerHTML = genres
    .map((g) => `<div class="chip" data-genre="${g.name}" data-jp="${jpGenre(g.name)}">${jpGenre(g.name)}<span class="count">${g.count.toLocaleString()}</span></div>`)
    .join("");

  // năm: 2026 -> 1960
  const yearSel = $("#fYear");
  for (let y = 2026; y >= 1960; y--) {
    const o = document.createElement("option");
    o.value = y; o.textContent = `${y}年`;
    yearSel.appendChild(o);
  }

  // tìm kiếm lọc chip (khớp cả tên Nhật lẫn tên Anh)
  $("#genreSearch").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll(".chip").forEach((c) => {
      const hit = c.dataset.genre.toLowerCase().includes(q) || c.dataset.jp.includes(e.target.value);
      c.style.display = hit ? "" : "none";
    });
  });
  $("#genreSearch").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const first = [...document.querySelectorAll(".chip")].find((c) => c.style.display !== "none");
      if (first) showGenre(first.dataset.genre);
    }
  });

  // bộ lọc -> tải lại từ trang 1
  ["fSort", "fType", "fStatus", "fYear"].forEach((id) => {
    $("#" + id).addEventListener("change", () => {
      state.sort = $("#fSort").value;
      state.type = $("#fType").value;
      state.status = $("#fStatus").value;
      state.year = $("#fYear").value;
      state.page = 1;
      if (state.genre) fetchAnime();
    });
  });

  // delegation: chip / phân trang / card
  document.body.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (chip) return showGenre(chip.dataset.genre);
    const pg = e.target.closest(".pagination button");
    if (pg && !pg.disabled) {
      state.page = Number(pg.dataset.page);
      fetchAnime();
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const card = e.target.closest(".card, .reco-item");
    if (card && card.dataset.id) return openDetail(card.dataset.id);
  });

  $("#modalClose").onclick = () => $("#modal").classList.add("hidden");
  $("#modal").addEventListener("click", (e) => {
    if (e.target.id === "modal") $("#modal").classList.add("hidden");
  });
  $("#resetMemory").onclick = async () => {
    if (!CURRENT_USER) return openAuth("login");
    renderMemory(await api("/api/memory/reset", { method: "POST" }));
    loadRecommendations();
    toast("メモリをリセットしました。");
  };

  // ----- auth handlers -----
  $("#authBar").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-act]");
    if (!b) return;
    if (b.dataset.act === "logout") logout();
    else openAuth(b.dataset.act); // "login" hoặc "register"
  });
  $("#authClose").onclick = () => $("#authModal").classList.add("hidden");
  $("#authModal").addEventListener("click", (e) => {
    if (e.target.id === "authModal") $("#authModal").classList.add("hidden");
  });
  $("#authSwitch").addEventListener("click", (e) => {
    e.preventDefault();
    openAuth(authMode === "login" ? "register" : "login");
  });
  $("#authForm").addEventListener("submit", submitAuth);

  await loadMe();
  await refreshUserData();

  const m = location.hash.match(/genre=([^&]+)/);
  if (m) showGenre(decodeURIComponent(m[1]));
  const a = location.hash.match(/auth=(login|register)/);
  if (a && !CURRENT_USER) openAuth(a[1]);
}

init();
