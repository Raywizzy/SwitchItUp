const defaultState = {
  profile: {
    name: "Raymond",
    role: "normal",
    scan: { status: "ready", quality: 91 },
  },
  wardrobe: [
    { name: "White Oxford Shirt", category: "top", fit: "tailored", material: "brushed cotton", colorName: "white", formality: 4, warmth: 1, colors: ["#ffffff", "#cbd5e1"], photo: "assets/photos/white-shirt.jpg" },
    { name: "Black Relaxed Tee", category: "top", fit: "relaxed", material: "premium cotton", colorName: "black", formality: 2, warmth: 1, colors: ["#111827", "#334155"], photo: "assets/photos/black-tee.jpg" },
    { name: "Stone Chinos", category: "bottom", fit: "straight", material: "cotton twill", colorName: "beige", formality: 4, warmth: 2, colors: ["#cdbb9d", "#a8906f"], photo: "assets/photos/stone-chinos.jpg" },
    { name: "Dark Denim", category: "bottom", fit: "tapered", material: "raw denim", colorName: "indigo", formality: 2, warmth: 2, colors: ["#1e3a8a", "#0f172a"], photo: "assets/photos/dark-denim.jpg" },
    { name: "White Trainers", category: "shoes", fit: "low profile", material: "leather", colorName: "white", formality: 3, warmth: 1, colors: ["#ffffff", "#dbeafe"], photo: "assets/photos/white-trainers.jpg" },
    { name: "Navy Overshirt", category: "jacket", fit: "boxy", material: "linen blend", colorName: "navy", formality: 3, warmth: 3, colors: ["#1e3a8a", "#0f172a"], photo: "assets/photos/navy-overshirt.jpg" },
  ],
  selected: ["White Oxford Shirt", "Stone Chinos", "White Trainers"],
  stylists: [
    { name: "Tami Looks", specialty: "Smart casual · dates · brunch", rating: 4.9, helped: 214, paid: true, avatar: "linear-gradient(145deg,#7b4f38,#f3d2b2 58%,#1d2636 59%)", photo: "assets/photos/blazer-portrait.jpg" },
    { name: "Kola Fits", specialty: "Streetwear · concerts · campus", rating: 4.8, helped: 187, paid: true, avatar: "linear-gradient(145deg,#6e4635,#caa07b 55%,#233047 56%)", photo: "assets/photos/style-feed.jpg" },
    { name: "Ari Tailored", specialty: "Weddings · formal · business", rating: 4.7, helped: 143, paid: true, avatar: "linear-gradient(145deg,#8a5f46,#e2b991 55%,#111827 56%)", photo: "assets/photos/avatar-model.jpg" },
    { name: "Maya FreeFit", specialty: "Budget wardrobe remix", rating: 4.6, helped: 91, paid: false, avatar: "linear-gradient(145deg,#8a583e,#d9a780 55%,#f7dce4 56%)", photo: "assets/photos/black-tee.jpg" },
  ],
  mall: [
    { item: "Structured navy blazer", store: "Metro Mall", price: 78, match: "Sharpens dinner fit", bg: "linear-gradient(135deg,#081827,#0d2e55)", photo: "assets/photos/mall-blazer.jpg" },
    { item: "Minimal leather loafers", store: "StyleHub", price: 64, match: "Upgrades footwear", bg: "linear-gradient(135deg,#7a3f1f,#c87a3a)", photo: "assets/photos/loafers.jpg" },
    { item: "Silver chain accessory", store: "Urban Rack", price: 22, match: "Adds quiet detail", bg: "linear-gradient(135deg,#e7edf5,#9ba9bb)", photo: "assets/photos/style-feed.jpg" },
  ],
  styleRequests: [],
  posts: [
    { id: "post_0001", author: "@tamilooks", subject: "@ray", caption: "Smart casual remix using wardrobe pieces plus one mall jacket. Saved as Friday dinner.", likes: 248, comments: 39, saves: 18, bookingRequests: 12, photo: "assets/photos/style-feed.jpg" },
  ],
  competitions: [
    { id: "competition_0001", name: "Weekend City Vibes", prize: 60, stylistsEntered: 8, winnersAllowed: 2, hoursLeft: 18 },
  ],
  switchAi: {
    version: "SwitchAI v1.0",
    preferences: { colors: {}, categories: {}, materials: {}, formalityBias: 0 },
    recommendations: [],
    feedback: [],
  },
};

let profile = structuredClone(defaultState.profile);
let wardrobe = structuredClone(defaultState.wardrobe);
let selected = [...defaultState.selected];
let stylists = structuredClone(defaultState.stylists);
let mall = structuredClone(defaultState.mall);
let posts = structuredClone(defaultState.posts);
let competitions = structuredClone(defaultState.competitions);
let switchAi = structuredClone(defaultState.switchAi);
let activeCategory = "all";
let backendOnline = false;
let uploadedPhotoData = "";
let uploadedPhotoName = "";
const maxUploadBytes = 6 * 1024 * 1024;
const acceptedUploadTypes = new Set(["image/png", "image/jpeg", "image/webp"]);
const githubPagesApiBase = "https://switchitup.vercel.app";
const apiBase = (
  window.SWITCHITUP_API_BASE ||
  document.querySelector("meta[name='switchitup-api-base']")?.content ||
  (window.location.hostname.endsWith("github.io") ? githubPagesApiBase : "") ||
  ""
).replace(/\/+$/, "");
const sessionStorageKey = "switchitup.sessionId";
const sessionHeader = "X-SwitchItUp-Session";
const sessionIdPattern = /^session_[a-z0-9]{16,64}$/;

function randomSessionSuffix() {
  if (window.crypto?.getRandomValues) {
    const bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(36).padStart(2, "0")).join("").slice(0, 32);
  }
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`.padEnd(24, "0").slice(0, 32);
}

function getSessionId() {
  try {
    const existing = window.localStorage?.getItem(sessionStorageKey);
    if (sessionIdPattern.test(existing || "")) return existing;
  } catch (error) {
    console.info("Switch It Up could not read local session storage.", error);
  }
  const created = `session_${randomSessionSuffix()}`;
  try {
    window.localStorage?.setItem(sessionStorageKey, created);
  } catch (error) {
    console.info("Switch It Up could not persist local session storage.", error);
  }
  return created;
}

const switchItUpSessionId = getSessionId();

function apiUrl(path) {
  if (/^https?:\/\//i.test(path)) return path;
  return `${apiBase}${path}`;
}

async function api(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json", [sessionHeader]: switchItUpSessionId, ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
  }
  return response.json();
}

async function callBackend(path, body) {
  if (!backendOnline) return null;
  try {
    return await api(path, { method: "POST", body: JSON.stringify(body || {}) });
  } catch (error) {
    backendOnline = false;
    updateApiStatus("Offline fallback");
    console.warn("Switch It Up API unavailable; using local demo state.", error);
    return null;
  }
}

function applyState(state) {
  profile = structuredClone(state.profile || defaultState.profile);
  wardrobe = structuredClone(state.wardrobe || defaultState.wardrobe);
  selected = [...(state.selected || defaultState.selected)];
  stylists = structuredClone(state.stylists || defaultState.stylists);
  mall = structuredClone(state.mall || defaultState.mall);
  posts = structuredClone(state.posts || defaultState.posts);
  competitions = structuredClone(state.competitions || defaultState.competitions);
  switchAi = structuredClone(state.switchAi || defaultState.switchAi);
  syncProfileUi();
}

async function loadState() {
  try {
    const state = await api("/api/state");
    backendOnline = true;
    applyState(state);
    updateApiStatus("Live backend");
  } catch (error) {
    backendOnline = false;
    applyState(defaultState);
    updateApiStatus("Static demo");
    console.info("Switch It Up backend not detected; running the GitHub Pages/static demo.", error);
  }
  renderAll();
}

function updateApiStatus(label) {
  const node = document.getElementById("apiStatus");
  if (!node) return;
  node.textContent = label || (backendOnline ? "Live backend" : "Static demo");
  node.classList.toggle("live", backendOnline);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;",
  })[character]);
}

function syncProfileUi() {
  const stylistMode = profile.role === "stylist";
  document.getElementById("signedRole").textContent = stylistMode ? "Stylist / Influencer" : "Normal Person";
  document.getElementById("upgradeBtn").textContent = stylistMode ? "Subscription active" : "Upgrade";
  document.querySelectorAll(".role-toggle button").forEach((button) => {
    button.classList.toggle("active", button.dataset.role === (stylistMode ? "stylist" : "normal"));
  });

  const scan = profile.scan || { status: "ready", quality: 91 };
  if (scan.status === "captured") {
    markScanCaptured(scan.quality || 96);
  } else {
    document.getElementById("scanStatus").textContent = "Ready to capture";
    document.getElementById("scanStep").classList.add("active");
    document.getElementById("scanStep").classList.remove("done");
    document.getElementById("scanQuality").textContent = `${scan.quality || 91}% match`;
  }
}

function findSelected(category) {
  const selectedName = selected.find((name) => wardrobe.find((entry) => entry.name === name)?.category === category);
  return wardrobe.find((item) => item.name === selectedName);
}

function updateWardrobeCount() {
  document.getElementById("wardrobeCount").textContent = wardrobe.length;
  document.querySelector(".progress-panel .step:nth-child(4) small").textContent = `${wardrobe.length} items`;
}

function setActiveCategory(category) {
  activeCategory = category;
  document.querySelectorAll(".filter-row button").forEach((button) => {
    button.classList.toggle("active", button.dataset.category === category);
  });
  renderWardrobe();
}

function renderWardrobe() {
  const visible = activeCategory === "all" ? wardrobe : wardrobe.filter((item) => item.category === activeCategory);
  document.getElementById("wardrobeGrid").innerHTML = visible.map((item) => `
    <article class="cloth">
      <span class="wardrobe-select-dot" aria-hidden="true"></span>
      <div class="cloth-art" style="--c1:${item.colors[0]};--c2:${item.colors[1]}">
        ${item.photo ? `<img src="${item.photo}" alt="${item.name}" loading="lazy">` : ""}
      </div>
      <div>
        <strong>${item.name}</strong>
        <small>${item.material} · ${item.colorName}</small>
        <div class="cloth-tags">
          <span>${item.category}</span>
          <span>${item.fit}</span>
        </div>
      </div>
      <button data-name="${item.name}" type="button">Wear</button>
    </article>
  `).join("");

  document.querySelectorAll(".cloth button").forEach((button) => {
    button.addEventListener("click", async () => {
      const result = await callBackend("/api/outfit/select", { name: button.dataset.name });
      if (result?.selected) {
        selected = result.selected;
      } else {
        const item = wardrobe.find((entry) => entry.name === button.dataset.name);
        selected = selected.filter((name) => wardrobe.find((entry) => entry.name === name)?.category !== item.category);
        selected.push(item.name);
      }
      renderFit();
    });
  });
}

function paintPart(id, item, fallback) {
  const node = document.getElementById(id);
  node.style.background = item ? `linear-gradient(135deg,${item.colors[0]},${item.colors[1]})` : fallback;
}

function renderFit() {
  document.getElementById("selectedFit").innerHTML = selected.map((item) => `<li>${item}</li>`).join("");
  const top = findSelected("top");
  const bottom = findSelected("bottom");
  const shoes = findSelected("shoes");
  const jacket = findSelected("jacket");

  paintPart("avatarTop", top, "#f8fafc");
  paintPart("avatarJacket", jacket, "transparent");
  document.getElementById("avatarJacket").style.opacity = jacket ? ".34" : "0";

  if (bottom) {
    paintPart("avatarLeftLeg", bottom, "#c8b28f");
    paintPart("avatarRightLeg", bottom, "#c8b28f");
  }
  if (shoes) {
    paintPart("avatarLeftShoe", shoes, "#ffffff");
    paintPart("avatarRightShoe", shoes, "#ffffff");
  }
}

function renderStylists() {
  document.getElementById("stylistCards").innerHTML = stylists.map((stylist) => `
    <article class="stylist-card">
      <span class="stylist-avatar" style="--avatar:${stylist.avatar}">
        ${stylist.photo ? `<img src="${stylist.photo}" alt="${stylist.name}" loading="lazy">` : ""}
      </span>
      <div>
        <strong>${stylist.name}</strong>
        <span>${stylist.specialty}</span>
        <b>${stylist.rating} rating · ${stylist.helped} helped · ${stylist.paid ? "Paid" : "Free"}</b>
      </div>
    </article>
  `).join("");
}

function renderMall() {
  document.getElementById("mallItems").innerHTML = mall.map((item) => `
    <article class="mall-item">
      <span class="mall-thumb" style="--mall-bg:${item.bg}">
        ${item.photo ? `<img src="${item.photo}" alt="${item.item}" loading="lazy">` : ""}
      </span>
      <strong>${item.item}</strong>
      <span>${item.store} · GBP ${item.price} · ${item.match}</span>
      <div class="mall-actions">
        <button data-action="accept" data-item="${item.item}" type="button">Accept</button>
        <button data-action="discard" data-item="${item.item}" type="button">Discard</button>
      </div>
    </article>
  `).join("");

  document.querySelectorAll(".mall-actions button").forEach((button) => {
    button.addEventListener("click", async () => {
      const result = await callBackend("/api/wishlist", {
        item: button.dataset.item,
        action: button.dataset.action,
      });
      if (result?.wardrobe) {
        wardrobe = result.wardrobe;
        updateWardrobeCount();
        renderWardrobe();
      }
      const fallbackVerb = button.dataset.action === "accept" ? "accepted" : "discarded";
      markRequestSent(result?.message || `${button.dataset.item} ${fallbackVerb}. Your stylist board was updated.`);
    });
  });
}

function renderSocial() {
  document.getElementById("feedList").innerHTML = posts.map((post) => `
    <article class="feed-card">
      <div class="fit-photo">
        <img src="${escapeHtml(post.photo || "assets/photos/style-feed.jpg")}" alt="Styled outfit post" loading="lazy" />
      </div>
      <div>
        <strong>${escapeHtml(post.author || "@ray")} styled ${escapeHtml(post.subject || "@ray")}</strong>
        <p>${escapeHtml(post.caption)}</p>
        <span>${Number(post.likes || 0)} likes · ${Number(post.comments || 0)} comments · ${Number(post.saves || 0)} saves · ${Number(post.bookingRequests || 0)} booking requests</span>
      </div>
    </article>
  `).join("");
}

function renderCompetitions() {
  const active = competitions[0] || defaultState.competitions[0];
  document.getElementById("competitionPrize").textContent = `Prize pot GBP ${Number(active.prize || 0)}`;
  document.getElementById("competitionRows").innerHTML = `
    <div class="competition-row">
      <div><strong>${Number(active.stylistsEntered || 0)}</strong><span>stylists entered</span></div>
      <div><strong>${Number(active.winnersAllowed || 1)}</strong><span>winners allowed</span></div>
      <div><strong>${Number(active.hoursLeft || 0)}h</strong><span>left to submit</span></div>
      <button id="openCompetition" type="button">Open competition</button>
    </div>
  `;
  document.getElementById("openCompetition").addEventListener("click", openCompetition);
}

function latestAiRecommendation() {
  return switchAi?.recommendations?.[0] || null;
}

function renderSwitchAI() {
  const latest = latestAiRecommendation();
  const output = document.getElementById("aiRecommendation");
  if (!output) return;
  const feedbackCount = Number(switchAi?.feedback?.length || 0);
  document.getElementById("aiLearning").textContent = `${feedbackCount} feedback signal${feedbackCount === 1 ? "" : "s"}`;
  document.getElementById("aiModelName").textContent = switchAi?.version || latest?.model || "SwitchAI v1.0";

  if (!latest) {
    document.getElementById("aiConfidence").textContent = "Ready";
    output.innerHTML = `
      <strong>Generate a look</strong>
      <p>SwitchAI will score your wardrobe, style your avatar, suggest a stylist, and learn from your feedback.</p>
    `;
    return;
  }

  const wishlist = latest.mallWishlist || [];
  const scores = latest.fitScores || [];
  const reasons = latest.reasons || [];
  const learning = latest.learningSummary || {};
  document.getElementById("aiConfidence").textContent = `${Number(latest.confidence || 0)}%`;
  output.innerHTML = `
    <div class="ai-fit">
      <strong>${escapeHtml(latest.occasion || "Styled outfit")}</strong>
      <p>${escapeHtml((latest.outfitItems || []).join(" + "))}</p>
    </div>
    <div class="ai-mini-grid">
      ${scores.map((item) => `
        <article>
          <span>${escapeHtml(item.category)}</span>
          <strong>${escapeHtml(item.name)}</strong>
          <small>${Number(item.score || 0)} · ${escapeHtml(item.reason)}</small>
        </article>
      `).join("")}
    </div>
    <ul class="ai-reasons">
      ${reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
    </ul>
    <div class="ai-bottom-row">
      <span>Stylist: ${escapeHtml(latest.stylistMatch?.name || "SwitchAI")}</span>
      <span>Wishlist: ${wishlist.length ? wishlist.map((item) => escapeHtml(item.item)).join(", ") : "No replacement needed"}</span>
      <span>Learning: ${(learning.favoriteColors || []).map(escapeHtml).join(", ") || "fresh profile"}</span>
    </div>
  `;
}

function markRequestSent(text) {
  document.getElementById("requestOutput").textContent = text;
  document.getElementById("requestStatus").textContent = "Sent to stylist";
  document.getElementById("requestStatus").parentElement.classList.add("done");
}

function markScanCaptured(quality = 96) {
  document.getElementById("scanStatus").textContent = "360 scan captured";
  document.getElementById("scanStep").classList.remove("active");
  document.getElementById("scanStep").classList.add("done");
  document.getElementById("confidence").textContent = `${quality}% scan confidence`;
  document.getElementById("scanQuality").textContent = `${quality}% match`;
}

async function sendRequest() {
  const occasion = document.getElementById("occasion").value;
  const budget = Number(document.getElementById("budget").value);
  const mode = document.getElementById("replaceMode").value;
  const delivery = document.getElementById("delivery").value;
  const paidAllowed = document.getElementById("paidToggle").checked;
  const result = await callBackend("/api/style-requests", {
    occasion,
    budget,
    replaceMode: mode,
    delivery,
    paidAllowed,
  });
  if (result) {
    if (result.selected) selected = result.selected;
    renderFit();
    markRequestSent(result.message);
    document.getElementById("confidence").textContent = `${Math.round(result.confidence)}% backend confidence`;
    return;
  }

  const stylist = mode === "none" || !paidAllowed ? "Maya FreeFit" : "Tami Looks";
  const action = mode === "all" ? "full outfit rebuild" : mode === "none" ? "wardrobe-only remix" : "partial replacement";
  markRequestSent(`${stylist} received your ${occasion.toLowerCase()} ${action} request with GBP ${budget} budget. Delivery: ${delivery.toLowerCase()}. Wishlist ready: ${mall[0].item}.`);
  document.getElementById("confidence").textContent = mode === "all" ? "94% remix confidence" : "91% fit confidence";
}

function nextUploadedItemName() {
  const base = "Uploaded Wardrobe Photo";
  if (!wardrobe.some((item) => item.name === base)) return base;
  return `${base} ${wardrobe.filter((item) => item.name.startsWith(base)).length + 1}`;
}

function newPhotoItem() {
  const category = document.getElementById("uploadCategory").value;
  const name = document.getElementById("uploadName").value.trim() || nextUploadedItemName();
  return {
    name,
    category,
    fit: category === "shoes" ? "low profile" : category === "jacket" ? "structured" : "regular",
    material: "uploaded photo",
    colorName: "custom",
    color: "custom",
    formality: category === "accessory" ? 2 : 3,
    warmth: category === "jacket" ? 3 : 1,
    colors: ["#f8fafc", "#94a3b8"],
    photo: uploadedPhotoData || "assets/photos/style-feed.jpg",
    photoData: uploadedPhotoData,
    photoName: uploadedPhotoName || `${name}.jpg`,
  };
}

function openUploadPanel() {
  document.getElementById("uploadPanel").hidden = false;
  document.getElementById("uploadName").focus();
}

function setUploadPrompt(message) {
  const preview = document.getElementById("uploadPreview");
  const prompt = document.createElement("span");
  prompt.textContent = message;
  preview.replaceChildren(prompt);
}

function setUploadPreview(src) {
  const image = document.createElement("img");
  image.src = src;
  image.alt = "Selected wardrobe upload preview";
  document.getElementById("uploadPreview").replaceChildren(image);
}

function closeUploadPanel() {
  uploadedPhotoData = "";
  uploadedPhotoName = "";
  document.getElementById("uploadPanel").hidden = true;
  document.getElementById("uploadPanel").reset();
  setUploadPrompt("Choose a clothing photo");
}

function readSelectedPhoto(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(reader.result));
    reader.addEventListener("error", () => reject(reader.error));
    reader.readAsDataURL(file);
  });
}

function renderAll() {
  updateWardrobeCount();
  renderWardrobe();
  renderFit();
  renderStylists();
  renderMall();
  renderSocial();
  renderCompetitions();
  renderSwitchAI();
}

async function upgradeStylistAccount() {
  const result = await callBackend("/api/stylist/upgrade", {
    specialty: "Smart casual · wardrobe remix · occasion styling",
    plan: "pro_monthly",
  });
  if (result?.profile) {
    profile = result.profile;
    stylists = result.stylists || stylists;
  } else {
    profile.role = "stylist";
  }
  syncProfileUi();
  renderStylists();
  markRequestSent("Stylist account upgraded. Your portfolio can now receive paid styling requests.");
}

async function postCurrentFit() {
  const caption = `Posted a fit using ${selected.join(", ")}.`;
  const result = await callBackend("/api/social/posts", {
    caption,
    author: "@ray",
    subject: "@ray",
    photo: "assets/photos/style-feed.jpg",
  });
  if (result?.posts) {
    posts = result.posts;
  } else {
    posts = [{ id: `post_${posts.length + 1}`, author: "@ray", subject: "@ray", caption, likes: 0, comments: 0, saves: 0, bookingRequests: 0, photo: "assets/photos/style-feed.jpg" }, ...posts];
  }
  renderSocial();
  markRequestSent("Fit posted to your style feed for stylist proof and social feedback.");
}

async function openCompetition() {
  const result = await callBackend("/api/competitions", {
    name: "Fresh wardrobe remix",
    prize: 60,
    winnersAllowed: 2,
    hoursLeft: 24,
  });
  if (result?.competitions) {
    competitions = result.competitions;
  } else {
    competitions = [{ id: `competition_${competitions.length + 1}`, name: "Fresh wardrobe remix", prize: 60, stylistsEntered: 0, winnersAllowed: 2, hoursLeft: 24 }, ...competitions];
  }
  renderCompetitions();
  markRequestSent("Competition opened. Stylists can submit outfits for your prize pool.");
}

function currentStylePayload() {
  return {
    occasion: document.getElementById("occasion").value,
    budget: Number(document.getElementById("budget").value),
    replaceMode: document.getElementById("replaceMode").value,
    delivery: document.getElementById("delivery").value,
    paidAllowed: document.getElementById("paidToggle").checked,
    apply: true,
  };
}

async function runSwitchAI() {
  const result = await callBackend("/api/ai/style", currentStylePayload());
  if (!result) {
    markRequestSent("SwitchAI needs the live backend. The static fallback can still style manually.");
    return;
  }
  switchAi = result.switchAi || switchAi;
  selected = result.selected || result.recommendation?.outfitItems || selected;
  renderFit();
  renderSwitchAI();
  document.getElementById("confidence").textContent = `${Math.round(result.recommendation?.confidence || 0)}% SwitchAI confidence`;
  markRequestSent(result.message);
}

async function sendSwitchAIFeedback(action) {
  const latest = latestAiRecommendation();
  if (!latest?.id) {
    markRequestSent("Run SwitchAI first, then rate the recommendation.");
    return;
  }
  const result = await callBackend("/api/ai/feedback", { recommendationId: latest.id, action });
  if (!result) return;
  switchAi = result.switchAi || switchAi;
  renderSwitchAI();
  markRequestSent(result.message);
}

document.querySelectorAll(".filter-row button").forEach((button) => {
  button.dataset.category = button.textContent.trim().toLowerCase().replace("tops", "top").replace("bottoms", "bottom").replace("shoes", "shoes");
  if (button.textContent.trim() === "All") button.dataset.category = "all";
  button.addEventListener("click", () => setActiveCategory(button.dataset.category));
});

document.querySelectorAll(".role-toggle button").forEach((button) => {
  button.addEventListener("click", async () => {
    const role = button.dataset.role;
    const result = await callBackend("/api/profile/role", { role });
    profile.role = result?.profile?.role || role;
    syncProfileUi();
  });
});

document.getElementById("upgradeBtn").addEventListener("click", upgradeStylistAccount);
document.getElementById("sidebarUpgrade").addEventListener("click", upgradeStylistAccount);

document.querySelectorAll(".stylist-tier button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".stylist-tier button").forEach((candidate) => candidate.classList.remove("active"));
    button.classList.add("active");
    document.getElementById("paidToggle").checked = button.textContent.includes("Pro");
  });
});

document.getElementById("captureScan").addEventListener("click", async () => {
  const result = await callBackend("/api/scan", { quality: 96 });
  profile.scan = result?.scan || { status: "captured", quality: 96 };
  markScanCaptured(profile.scan.quality);
});

document.getElementById("askStylist").addEventListener("click", sendRequest);
document.getElementById("styleMe").addEventListener("click", async () => {
  await runSwitchAI();
});
document.getElementById("runSwitchAi").addEventListener("click", runSwitchAI);
document.querySelectorAll("[data-ai-feedback]").forEach((button) => {
  button.addEventListener("click", () => sendSwitchAIFeedback(button.dataset.aiFeedback));
});
document.getElementById("addItem").addEventListener("click", openUploadPanel);
document.getElementById("cancelUpload").addEventListener("click", closeUploadPanel);
document.getElementById("photoUpload").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  uploadedPhotoData = "";
  uploadedPhotoName = "";
  if (!acceptedUploadTypes.has(file.type)) {
    event.target.value = "";
    setUploadPrompt("Use a PNG, JPEG, or WebP photo");
    return;
  }
  if (file.size > maxUploadBytes) {
    event.target.value = "";
    setUploadPrompt("Use a photo under 6MB");
    return;
  }
  try {
    uploadedPhotoData = await readSelectedPhoto(file);
    uploadedPhotoName = file.name;
    setUploadPreview(uploadedPhotoData);
  } catch (error) {
    event.target.value = "";
    setUploadPrompt("Could not read this photo");
    console.warn("Switch It Up could not read the selected wardrobe photo.", error);
    return;
  }
  if (!document.getElementById("uploadName").value.trim()) {
    document.getElementById("uploadName").value = file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ");
  }
});
document.getElementById("uploadPanel").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!uploadedPhotoData) {
    setUploadPrompt("Please choose a clothing photo first");
    return;
  }
  const item = newPhotoItem();
  const result = await callBackend("/api/wardrobe", { item });
  if (result?.wardrobe) {
    wardrobe = result.wardrobe;
  } else {
    delete item.photoData;
    delete item.photoName;
    wardrobe.push(item);
  }
  updateWardrobeCount();
  renderWardrobe();
  closeUploadPanel();
});
document.getElementById("sendWishlist").addEventListener("click", () => {
  markRequestSent("Wishlist sent. If accepted, purchased items move into the wardrobe in the stylist's exact outfit order.");
});
document.getElementById("postFit").addEventListener("click", postCurrentFit);

loadState();
