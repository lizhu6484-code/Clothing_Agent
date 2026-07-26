/* ═══ 穿搭 Agent — Unified Frontend ═══ */
(function () {
"use strict";

const API = "http://127.0.0.1:8080/api";
const STATIC = "http://127.0.0.1:8080/static";
const BACKEND = "http://127.0.0.1:8080";

// ── State ──
let cameraStream = null;
let currentLat = null, currentLon = null;
let currentWeather = null;
let pendingRecognizeItemId = null;
let recMode = "wardrobe";
let imagesEnabled = false;
let allUsers = [];
let wardrobeItems = [];
let filterType = "", filterCategory = "";
let onlineScope = "full";

const CATEGORY_MAP = {
  "上衣": ["短袖", "衬衫", "卫衣", "毛衣", "外套"],
  "下装": ["长裤(休闲)", "长裤(正式)", "短裤"],
  "鞋子": ["运动鞋", "休闲鞋"],
};

// ── Init ──
document.addEventListener("DOMContentLoaded", async () => {
  initMainTabs();
  initSubTabs();
  await checkOnboarding();
  initUserChip();
  initWardrobe();
  initRecommend();
  initOnlinePurchase();
  initOfflineShopping();
  initLocationAndWeather();
});

// ═══ Onboarding Gate ═══
async function checkOnboarding() {
  try {
    const res = await fetch(`${API}/user`);
    const users = await res.json();
    if (users.length === 0) {
      document.getElementById("onboarding-overlay").classList.remove("hidden");
      initOnboardingForm();
    }
  } catch (e) {
    document.getElementById("onboarding-overlay").classList.remove("hidden");
    initOnboardingForm();
  }
}

function initOnboardingForm() {
  const form = document.getElementById("onboarding-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const gender = document.getElementById("ob-gender").value;
    const height = document.getElementById("ob-height").value;
    const weight = document.getElementById("ob-weight").value;
    if (!gender || !height || !weight) return;

    const body = {
      gender,
      height_cm: parseFloat(height),
      weight_kg: parseFloat(weight),
      name: document.getElementById("ob-name").value.trim(),
      age: document.getElementById("ob-age").value ? parseInt(document.getElementById("ob-age").value) : null,
      notes: document.getElementById("ob-notes").value.trim(),
    };

    try {
      await fetch(`${API}/user`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
      document.getElementById("onboarding-overlay").classList.add("hidden");
      loadUsers();
    } catch (e) { alert("创建失败，请重试"); }
  });
}

// ═══ Main Tabs (with hook animation) ═══
function initMainTabs() {
  const tabs = document.querySelectorAll(".main-tab");
  const hook = document.getElementById("tab-hook");

  function moveHook(btn) {
    const rect = btn.getBoundingClientRect();
    const parentRect = btn.parentElement.getBoundingClientRect();
    const x = rect.left - parentRect.left + rect.width / 2 - 12;
    hook.style.transform = `translateX(${x}px)`;
  }

  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
      moveHook(btn);
    });
  });

  // Initial hook position
  requestAnimationFrame(() => moveHook(document.querySelector(".main-tab.active")));
}

// ═══ Sub Tabs ═══
function initSubTabs() {
  document.querySelectorAll(".sub-nav").forEach(nav => {
    const btns = nav.querySelectorAll(".sub-tab");
    btns.forEach(btn => {
      btn.addEventListener("click", () => {
        btns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const section = nav.parentElement;
        section.querySelectorAll(".sub-panel").forEach(p => p.classList.remove("active"));
        section.querySelector(`#panel-${btn.dataset.panel}`).classList.add("active");
      });
    });
  });
}

// ═══ User Chip + Modal ═══
function initUserChip() {
  document.getElementById("user-chip").addEventListener("click", () => openUserModal());
  document.getElementById("btn-close-user-modal").addEventListener("click", () => closeModal("user-modal"));
  document.getElementById("btn-add-user").addEventListener("click", () => showUserForm(null));
  document.getElementById("btn-user-back").addEventListener("click", () => showUserListView());
  document.getElementById("user-form").addEventListener("submit", (e) => { e.preventDefault(); saveUser(); });
  loadUsers();
}

async function loadUsers() {
  try {
    const res = await fetch(`${API}/user`);
    allUsers = await res.json();
    updateUserChip();
    renderUserList();
  } catch (e) {}
}

function getActiveUser() { return allUsers.find(u => u.is_active); }

function updateUserChip() {
  const u = getActiveUser();
  document.getElementById("user-chip-name").textContent = u ? (u.name || u.gender || "用户") : "未设置";
  document.getElementById("user-avatar").textContent = u ? (u.name || u.gender || "?")[0] : "?";
}

function openUserModal() { document.getElementById("user-modal").classList.remove("hidden"); showUserListView(); }
function showUserListView() {
  document.getElementById("user-list-view").classList.remove("hidden");
  document.getElementById("user-form").classList.add("hidden");
  renderUserList();
}

function userSummary(u) {
  const parts = [];
  if (u.gender) parts.push(u.gender);
  if (u.height_cm) parts.push(`${u.height_cm}cm`);
  if (u.weight_kg) parts.push(`${u.weight_kg}kg`);
  if (u.age) parts.push(`${u.age}岁`);
  return parts.join(" · ") || "无信息";
}

function renderUserList() {
  const el = document.getElementById("user-list");
  if (!allUsers.length) { el.innerHTML = '<p class="empty-hint">暂无使用者</p>'; return; }
  el.innerHTML = allUsers.map(u => `
    <div class="user-row ${u.is_active ? 'active' : ''}" data-id="${u.id}">
      <span class="user-avatar">${(u.name || u.gender || '?')[0]}</span>
      <div class="user-info">
        <div class="uname">${esc(u.name || '未命名')}</div>
        <div class="usummary">${userSummary(u)}</div>
      </div>
      ${u.is_active ? '<span class="user-active-badge">当前</span>' : ''}
      <div class="row-actions">
        <button class="row-btn" data-action="edit" data-id="${u.id}">✎</button>
        <button class="row-btn" data-action="del" data-id="${u.id}">×</button>
      </div>
    </div>
  `).join("");

  el.querySelectorAll(".user-row").forEach(row => {
    row.addEventListener("click", (e) => {
      if (e.target.closest(".row-btn")) return;
      activateUser(parseInt(row.dataset.id));
    });
  });
  el.querySelectorAll('[data-action="edit"]').forEach(btn => btn.addEventListener("click", () => {
    const u = allUsers.find(x => x.id === parseInt(btn.dataset.id));
    if (u) showUserForm(u);
  }));
  el.querySelectorAll('[data-action="del"]').forEach(btn => btn.addEventListener("click", () => deleteUser(parseInt(btn.dataset.id))));
}

async function activateUser(id) {
  await fetch(`${API}/user/${id}/activate`, { method: "POST" });
  await loadUsers();
}

async function deleteUser(id) {
  if (!confirm("确定删除该使用者？")) return;
  await fetch(`${API}/user/${id}`, { method: "DELETE" });
  await loadUsers();
}

function showUserForm(u) {
  document.getElementById("user-list-view").classList.add("hidden");
  document.getElementById("user-form").classList.remove("hidden");
  document.getElementById("uf-id").value = u ? u.id : "";
  document.getElementById("uf-gender").value = u ? u.gender : "";
  document.getElementById("uf-height").value = u ? u.height_cm : "";
  document.getElementById("uf-weight").value = u ? u.weight_kg : "";
  document.getElementById("uf-name").value = u ? u.name : "";
  document.getElementById("uf-age").value = u ? (u.age || "") : "";
  document.getElementById("uf-notes").value = u ? u.notes : "";
}

async function saveUser() {
  const gender = document.getElementById("uf-gender").value;
  const height = document.getElementById("uf-height").value;
  const weight = document.getElementById("uf-weight").value;
  if (!gender || !height || !weight) { alert("性别、身高、体重为必填项"); return; }

  const body = {
    gender,
    height_cm: parseFloat(height),
    weight_kg: parseFloat(weight),
    name: document.getElementById("uf-name").value.trim(),
    age: document.getElementById("uf-age").value ? parseInt(document.getElementById("uf-age").value) : null,
    notes: document.getElementById("uf-notes").value.trim(),
  };

  const id = document.getElementById("uf-id").value;
  if (id) {
    await fetch(`${API}/user/${id}`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
  } else {
    await fetch(`${API}/user`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
  }
  await loadUsers();
  showUserListView();
}

// ═══ Location & Weather ═══
function initLocationAndWeather() {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(async (pos) => {
    currentLat = pos.coords.latitude;
    currentLon = pos.coords.longitude;
    try {
      const res = await fetch(`${API}/recommend/weather?lat=${currentLat}&lon=${currentLon}`);
      if (!res.ok) throw new Error();
      currentWeather = await res.json();
      renderWeatherHero(currentWeather);
    } catch (e) {
      document.getElementById("weather-hero-status").textContent = "天气获取失败";
    }
  }, () => {
    document.getElementById("weather-hero-status").textContent = "无法获取定位";
  });
}

function renderWeatherHero(w) {
  document.getElementById("weather-hero-status").classList.add("hidden");
  document.getElementById("weather-hero-content").classList.remove("hidden");
  document.getElementById("wh-location-text").textContent = w.location || "当前位置";
  document.getElementById("wh-temp").textContent = w.temp;
  document.getElementById("wh-text").textContent = w.text;
  document.getElementById("wh-humidity").textContent = `湿度 ${w.humidity}%`;
  document.getElementById("wh-wind").textContent = w.wind;
}

// ═══ Wardrobe ═══
function initWardrobe() {
  document.getElementById("btn-camera").addEventListener("click", openCamera);
  document.getElementById("file-input").addEventListener("change", (e) => { if (e.target.files[0]) uploadFile(e.target.files[0]); });
  document.getElementById("btn-capture").addEventListener("click", capturePhoto);
  document.getElementById("btn-close-camera").addEventListener("click", closeCamera);
  document.getElementById("btn-confirm-recognize").addEventListener("click", confirmRecognize);
  document.getElementById("btn-cancel-recognize").addEventListener("click", () => closeModal("recognize-modal"));
  document.getElementById("rec-type").addEventListener("change", (e) => updateCategoryOptions(e.target.value));
  initCategoryFilter();
  loadWardrobe();
}

function initCategoryFilter() {
  document.querySelectorAll("#category-main .cat-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#category-main .cat-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      filterType = btn.dataset.type;
      filterCategory = "";
      renderSubFilter();
      renderWardrobeList();
    });
  });
}

function renderSubFilter() {
  const subEl = document.getElementById("category-sub");
  if (!filterType || !CATEGORY_MAP[filterType]) { subEl.classList.add("hidden"); return; }
  subEl.classList.remove("hidden");
  subEl.innerHTML = CATEGORY_MAP[filterType].map(c => `<button class="cat-sub-btn" data-cat="${c}">${c}</button>`).join("");
  subEl.querySelectorAll(".cat-sub-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const wasActive = btn.classList.contains("active");
      subEl.querySelectorAll(".cat-sub-btn").forEach(b => b.classList.remove("active"));
      if (!wasActive) { btn.classList.add("active"); filterCategory = btn.dataset.cat; }
      else { filterCategory = ""; }
      renderWardrobeList();
    });
  });
}

async function loadWardrobe() {
  try {
    const res = await fetch(`${API}/wardrobe/items`);
    wardrobeItems = await res.json();
    renderWardrobeList();
  } catch (e) {}
}

function renderWardrobeList() {
  const el = document.getElementById("wardrobe-list");
  const emptyEl = document.getElementById("wardrobe-empty");
  let items = wardrobeItems;
  if (filterType) items = items.filter(i => i.type === filterType);
  if (filterCategory) items = items.filter(i => i.category === filterCategory);

  if (!items.length) { el.innerHTML = ""; emptyEl.classList.remove("hidden"); return; }
  emptyEl.classList.add("hidden");

  el.innerHTML = items.map(item => `
    <div class="wardrobe-card">
      <img src="${STATIC}/${item.image_path.replace('uploads/', '')}" alt="${esc(item.name)}" loading="lazy">
      <button class="btn-del" data-id="${item.id}">×</button>
      <div class="info">
        <div class="name">${esc(item.name)}</div>
        <span class="type-tag">${esc(item.category || item.type)}</span>
        <span class="meta-tag">${esc(item.color)}</span>
      </div>
    </div>
  `).join("");

  el.querySelectorAll(".btn-del").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("删除这件衣物？")) return;
      await fetch(`${API}/wardrobe/items/${btn.dataset.id}`, { method: "DELETE" });
      loadWardrobe();
    });
  });
}

// Camera
function openCamera() {
  const modal = document.getElementById("camera-modal");
  modal.classList.remove("hidden");
  navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
    .then(stream => { cameraStream = stream; document.getElementById("camera-preview").srcObject = stream; })
    .catch(() => { closeCamera(); document.getElementById("file-input").click(); });
}

function closeCamera() {
  if (cameraStream) { cameraStream.getTracks().forEach(t => t.stop()); cameraStream = null; }
  document.getElementById("camera-modal").classList.add("hidden");
}

function capturePhoto() {
  const video = document.getElementById("camera-preview");
  const canvas = document.getElementById("capture-canvas");
  const maxDim = 1280;
  let w = video.videoWidth, h = video.videoHeight;
  if (w > maxDim || h > maxDim) { const r = Math.min(maxDim / w, maxDim / h); w = Math.round(w * r); h = Math.round(h * r); }
  canvas.width = w; canvas.height = h;
  canvas.getContext("2d").drawImage(video, 0, 0, w, h);
  canvas.toBlob(blob => { closeCamera(); uploadBlob(blob, "capture.jpg"); }, "image/jpeg", 0.85);
}

function uploadFile(file) { uploadBlob(file, file.name); }

async function uploadBlob(blob, filename) {
  document.getElementById("upload-loading").classList.remove("hidden");
  const fd = new FormData();
  fd.append("file", blob, filename);
  try {
    const res = await fetch(`${API}/wardrobe/upload`, { method: "POST", body: fd });
    if (!res.ok) throw new Error((await res.json()).detail || "上传失败");
    const data = await res.json();
    await loadWardrobe();
    showRecognizeModal(data);
  } catch (e) { alert("上传失败: " + (e.message || e)); }
  document.getElementById("upload-loading").classList.add("hidden");
}

function showRecognizeModal(data) {
  pendingRecognizeItemId = data.id;
  const r = data.recognized;
  document.getElementById("recognize-img").src = `${STATIC}/${data.image_path.replace('uploads/', '')}`;
  document.getElementById("rec-name").value = r.name || "";
  document.getElementById("rec-type").value = r.type || "上衣";
  updateCategoryOptions(r.type || "上衣");
  document.getElementById("rec-category").value = r.category || "";
  document.getElementById("rec-color").value = r.color || "";
  document.getElementById("rec-material").value = r.material || "";
  document.getElementById("rec-season").value = (r.season || []).join(",");
  document.getElementById("rec-formality").value = r.formality || 3;
  document.getElementById("rec-style").value = (r.style || []).join(",");
  document.getElementById("rec-features").value = (r.features || []).join(",");
  document.getElementById("recognize-modal").classList.remove("hidden");
}

function updateCategoryOptions(type) {
  const sel = document.getElementById("rec-category");
  const cats = CATEGORY_MAP[type] || [];
  sel.innerHTML = cats.map(c => `<option value="${c}">${c}</option>`).join("");
}

async function confirmRecognize() {
  const body = {
    name: document.getElementById("rec-name").value.trim(),
    type: document.getElementById("rec-type").value,
    category: document.getElementById("rec-category").value,
    color: document.getElementById("rec-color").value.trim(),
    material: document.getElementById("rec-material").value.trim(),
    season: document.getElementById("rec-season").value.split(/[,，]/).map(s => s.trim()).filter(Boolean),
    formality: parseInt(document.getElementById("rec-formality").value) || 3,
    style: document.getElementById("rec-style").value.split(/[,，]/).map(s => s.trim()).filter(Boolean),
    features: document.getElementById("rec-features").value.split(/[,，]/).map(s => s.trim()).filter(Boolean),
  };
  await fetch(`${API}/wardrobe/items/${pendingRecognizeItemId}`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
  closeModal("recognize-modal");
  loadWardrobe();
}

// ═══ Recommend ═══
function initRecommend() {
  document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      recMode = btn.dataset.mode;
      document.getElementById("mode-hint").textContent = recMode === "wardrobe" ? "从你的衣橱中搭配" : "不依赖衣橱，自由推荐";
    });
  });

  document.getElementById("images-toggle").addEventListener("change", (e) => { imagesEnabled = e.target.checked; });

  const occSel = document.getElementById("rec-occasion");
  occSel.addEventListener("change", () => {
    document.getElementById("rec-occasion-custom").classList.toggle("hidden", occSel.value !== "其他");
  });

  document.getElementById("recommend-form").addEventListener("submit", (e) => { e.preventDefault(); submitRecommend(); });
}

async function submitRecommend() {
  if (currentLat === null) { alert("等待定位完成后再试"); return; }
  const occSel = document.getElementById("rec-occasion");
  const occasion = occSel.value === "其他" ? document.getElementById("rec-occasion-custom").value.trim() || "其他" : occSel.value;

  const body = {
    lat: currentLat, lon: currentLon, occasion,
    purpose: document.getElementById("rec-purpose").value.trim(),
    preferences: document.getElementById("rec-preferences").value.trim(),
  };

  document.getElementById("recommend-loading").classList.remove("hidden");
  document.getElementById("recommend-result").innerHTML = "";

  try {
    const url = recMode === "wardrobe" ? `${API}/recommend` : `${API}/recommend/free`;
    const res = await fetch(url, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) {
      const err = data.detail?.error || data.detail || "推荐失败";
      if (err === "EMPTY_WARDROBE") { alert("衣橱是空的，先去拍几件衣服吧"); }
      else { alert("推荐失败: " + err); }
      return;
    }
    if (recMode === "wardrobe") renderWardrobeRecResult(data);
    else renderFreeRecResult(data);
  } catch (e) { alert("请求失败"); }
  document.getElementById("recommend-loading").classList.add("hidden");
}

function slotLine(label, slot) {
  if (!slot) return "";
  const name = typeof slot === "string" ? slot : slot.name;
  if (!name) return "";
  return `<div class="slot-line"><span class="slot-label">${label}</span><span>${esc(name)}</span></div>`;
}

function renderWardrobeRecResult(data) {
  const el = document.getElementById("recommend-result");
  let html = "";
  (data.outfits || []).forEach((o, i) => {
    html += `<div class="outfit-card">
      <div class="summary">${esc(o.summary)}</div>
      <div class="outfit-slots">${slotLine("上装", o.top)}${slotLine("下装", o.bottom)}${slotLine("鞋子", o.shoes)}</div>
      <div class="reason">${esc(o.reason)}</div>
      <div class="formality">${[1,2,3,4,5].map(n => `<span class="formality-dot ${n <= o.formality_match ? 'filled' : ''}"></span>`).join("")}</div>
      ${imagesEnabled ? `<div class="outfit-images" id="outfit-images-${i}"><span class="images-loading">图片搜索中...</span></div>` : ""}
    </div>`;
  });
  if (data.fallback_tips) html += `<div class="fallback-tips">${esc(data.fallback_tips)}</div>`;
  el.innerHTML = html;

  if (imagesEnabled) {
    (data.outfits || []).forEach((o, i) => {
      const keywords = [o.top?.name, o.bottom?.name, o.shoes?.name].filter(Boolean);
      if (keywords.length) loadOutfitImages(keywords, i);
    });
  }
}

function renderFreeRecResult(data) {
  const el = document.getElementById("recommend-result");
  let html = "";
  (data.outfits || []).forEach((o, i) => {
    html += `<div class="outfit-card">
      <div class="summary">${esc(o.summary)}</div>
      <div class="outfit-slots">${slotLine("上装", o.top)}${slotLine("下装", o.bottom)}${slotLine("鞋子", o.shoes)}</div>
      <div class="reason">${esc(o.reason)}</div>
      ${imagesEnabled ? `<div class="outfit-images" id="outfit-images-${i}"><span class="images-loading">图片搜索中...</span></div>` : ""}
    </div>`;
  });
  if (data.tips) html += `<div class="fallback-tips">${esc(data.tips)}</div>`;
  el.innerHTML = html;

  if (imagesEnabled) {
    (data.outfits || []).forEach((o, i) => {
      const keywords = [o.top, o.bottom, o.shoes].filter(Boolean).map(s => s.split("，")[0].split(",")[0]);
      if (keywords.length) loadOutfitImages(keywords, i);
    });
  }
}

async function loadOutfitImages(keywords, index) {
  const container = document.getElementById(`outfit-images-${index}`);
  if (!container) return;
  try {
    const res = await fetch(`${API}/recommend/images`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ keywords }) });
    const data = await res.json();
    const imgs = (data.images || []).filter(x => x.url);
    if (!imgs.length) { container.innerHTML = '<span class="images-empty">暂无匹配图片</span>'; return; }
    container.innerHTML = `<div class="images-row">${imgs.map(x => `<figure class="outfit-img-item"><img src="${BACKEND}${x.url}" alt="${esc(x.keyword)}" loading="lazy"><figcaption>${esc(x.keyword)}</figcaption></figure>`).join("")}</div>`;
  } catch (e) { container.innerHTML = '<span class="images-empty">图片加载失败</span>'; }
}

// ═══ Online Purchase ═══
function initOnlinePurchase() {
  document.querySelectorAll(".scope-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".scope-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      onlineScope = btn.dataset.scope;
    });
  });
  document.getElementById("online-form").addEventListener("submit", (e) => { e.preventDefault(); submitOnline(); });
}

async function submitOnline() {
  const body = {
    purchase_scope: onlineScope,
    scene: document.getElementById("ol-scene").value.trim(),
    style: document.getElementById("ol-style").value.trim(),
    budget: document.getElementById("ol-budget").value ? parseFloat(document.getElementById("ol-budget").value) : null,
    other: document.getElementById("ol-other").value.trim(),
  };

  // Validate at least one field
  if (!body.scene && !body.style && !body.budget && !body.other) { alert("请至少填写一项需求"); return; }

  document.getElementById("online-loading").classList.remove("hidden");
  document.getElementById("online-result").innerHTML = "";

  try {
    const res = await fetch(`${API}/purchase/recommend`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) { alert("推荐失败: " + (data.detail?.message || data.detail?.error || "未知错误")); return; }
    renderOnlineResult(data);
  } catch (e) { alert("请求失败"); }
  document.getElementById("online-loading").classList.add("hidden");
}

function renderOnlineResult(data) {
  const el = document.getElementById("online-result");
  const CAT_LABELS = { top: "上衣", bottom: "下装", shoes: "鞋子" };
  let html = `<div class="purchase-summary">${esc(data.summary)}</div>`;

  // Outfit plan cards
  (data.outfit_plan?.items || []).forEach(item => {
    html += `<div class="plan-card">
      <div class="plan-cat">${CAT_LABELS[item.category] || item.category}</div>
      <div class="plan-name">${esc(item.name)}</div>
      <div class="plan-desc">${esc(item.description)}</div>
      <div class="plan-role">${esc(item.role)}</div>
    </div>`;
  });

  // Product cards by category
  const products = data.products_by_category || {};
  for (const [cat, items] of Object.entries(products)) {
    if (!items || !items.length) continue;
    html += `<div class="category-section-title">${CAT_LABELS[cat] || cat} · 商品推荐</div>`;
    items.slice(0, 5).forEach(p => {
      const finalPrice = ((p.min_group_price - (p.coupon_discount || 0)) / 100).toFixed(1);
      const origPrice = (p.min_normal_price / 100).toFixed(1);
      html += `<div class="product-card">
        <img src="${p.goods_image_url}" alt="" loading="lazy" onerror="this.style.display='none'">
        <div class="product-info">
          <div class="product-name">${esc(p.goods_name)}</div>
          <div class="product-price">¥${finalPrice}<span class="original">¥${origPrice}</span></div>
          <div class="product-meta">${p.coupon_discount ? `券 ¥${(p.coupon_discount/100).toFixed(0)} · ` : ""}${esc(p.sales_tip || "")}</div>
          ${(p.unified_tags || []).length ? `<div class="product-tags">${p.unified_tags.slice(0,3).map(t => `<span>${esc(t)}</span>`).join("")}</div>` : ""}
        </div>
      </div>`;
    });
  }

  el.innerHTML = html;
}

// ═══ Offline Shopping ═══
function initOfflineShopping() {
  const occSel = document.getElementById("off-occasion");
  occSel.addEventListener("change", () => {
    document.getElementById("off-occasion-custom").classList.toggle("hidden", occSel.value !== "其他");
  });
  document.getElementById("offline-form").addEventListener("submit", (e) => { e.preventDefault(); submitOffline(); });
}

async function submitOffline() {
  if (currentLat === null) { alert("等待定位完成后再试"); return; }
  const occSel = document.getElementById("off-occasion");
  const occasion = occSel.value === "其他" ? document.getElementById("off-occasion-custom").value.trim() || "其他" : occSel.value;

  const body = {
    lat: currentLat, lon: currentLon,
    need: document.getElementById("off-need").value.trim(),
    occasion,
    budget: document.getElementById("off-budget").value.trim(),
    preferences: document.getElementById("off-preferences").value.trim(),
  };

  document.getElementById("offline-loading").classList.remove("hidden");
  document.getElementById("offline-result").innerHTML = "";

  try {
    const res = await fetch(`${API}/shopping/offline`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) { alert("请求失败: " + (data.detail?.error || "未知错误")); return; }
    renderOfflineResult(data);
  } catch (e) { alert("请求失败"); }
  document.getElementById("offline-loading").classList.add("hidden");
}

function renderOfflineResult(data) {
  const el = document.getElementById("offline-result");
  let html = "";

  // AI advice bubble
  if (data.advice) {
    html += `<div class="chat-bubble"><span class="chat-avatar">AI</span><div class="chat-text">${esc(data.advice)}</div></div>`;
  }

  // Shopping list
  if (data.shopping_list?.length) {
    html += `<div class="shopping-section-title">购物清单</div>`;
    data.shopping_list.forEach(item => {
      html += `<div class="shopping-item-card">
        <div class="shopping-item-name">${esc(item.item)}</div>
        <div class="shopping-item-reason">${esc(item.reason)}</div>
        ${item.tips ? `<div class="shopping-item-tips">${esc(item.tips)}</div>` : ""}
      </div>`;
    });
  }

  // Stores
  if (data.stores?.length) {
    html += `<div class="shopping-section-title">附近店铺</div>`;
    data.stores.forEach(s => {
      html += `<div class="store-card">
        <div class="store-name">${esc(s.name)}</div>
        <div class="store-address">${esc(s.address)}</div>
        <div class="store-meta">
          ${s.phone ? `📞 ${esc(s.phone)} · ` : ""}
          ${s.rating ? `<span class="store-rating">★ ${s.rating}</span> · ` : ""}
          ${s.tags ? esc(s.tags) : ""}
        </div>
      </div>`;
    });
  } else {
    html += `<div class="store-empty">暂未找到附近店铺（需配置百度地图AK）</div>`;
  }

  el.innerHTML = html;
}

// ═══ Utilities ═══
function closeModal(id) { document.getElementById(id).classList.add("hidden"); }
function esc(s) { if (!s) return ""; const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

})();
