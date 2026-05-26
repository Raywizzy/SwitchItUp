const defaultState = {
  profile: {
    name: "Raymond",
    role: "normal",
    scan: { status: "ready", quality: 91 },
  },
  wardrobe: [
    { name: "White Oxford Shirt", category: "top", fit: "tailored", material: "brushed cotton", colorName: "white", formality: 4, warmth: 1, colors: ["#ffffff", "#cbd5e1"] },
    { name: "Black Relaxed Tee", category: "top", fit: "relaxed", material: "premium cotton", colorName: "black", formality: 2, warmth: 1, colors: ["#111827", "#334155"] },
    { name: "Stone Chinos", category: "bottom", fit: "straight", material: "cotton twill", colorName: "beige", formality: 4, warmth: 2, colors: ["#cdbb9d", "#a8906f"] },
    { name: "Dark Denim", category: "bottom", fit: "tapered", material: "raw denim", colorName: "indigo", formality: 2, warmth: 2, colors: ["#1e3a8a", "#0f172a"] },
    { name: "White Trainers", category: "shoes", fit: "low profile", material: "leather", colorName: "white", formality: 3, warmth: 1, colors: ["#ffffff", "#dbeafe"] },
    { name: "Navy Overshirt", category: "jacket", fit: "boxy", material: "linen blend", colorName: "navy", formality: 3, warmth: 3, colors: ["#1e3a8a", "#0f172a"] },
  ],
  selected: ["White Oxford Shirt", "Stone Chinos", "White Trainers"],
  stylists: [
    { name: "Tami Looks", specialty: "Smart casual · dates · brunch", rating: 4.9, helped: 214, paid: true, avatar: "linear-gradient(145deg,#7b4f38,#f3d2b2 58%,#1d2636 59%)" },
    { name: "Kola Fits", specialty: "Streetwear · concerts · campus", rating: 4.8, helped: 187, paid: true, avatar: "linear-gradient(145deg,#6e4635,#caa07b 55%,#233047 56%)" },
    { name: "Ari Tailored", specialty: "Weddings · formal · business", rating: 4.7, helped: 143, paid: true, avatar: "linear-gradient(145deg,#8a5f46,#e2b991 55%,#111827 56%)" },
    { name: "Maya FreeFit", specialty: "Budget wardrobe remix", rating: 4.6, helped: 91, paid: false, avatar: "linear-gradient(145deg,#8a583e,#d9a780 55%,#f7dce4 56%)" },
  ],
  mall: [
    { item: "Structured navy blazer", store: "Metro Mall", price: 78, match: "Sharpens dinner fit", bg: "linear-gradient(135deg,#081827,#0d2e55)" },
    { item: "Minimal leather loafers", store: "StyleHub", price: 64, match: "Upgrades footwear", bg: "linear-gradient(135deg,#7a3f1f,#c87a3a)" },
    { item: "Silver chain accessory", store: "Urban Rack", price: 22, match: "Adds quiet detail", bg: "linear-gradient(135deg,#e7edf5,#9ba9bb)" },
  ],
  styleRequests: [],
};

let profile = structuredClone(defaultState.profile);
let wardrobe = structuredClone(defaultState.wardrobe);
let selected = [...defaultState.selected];
let stylists = structuredClone(defaultState.stylists);
let mall = structuredClone(defaultState.mall);
let activeCategory = "all";
let backendOnline = false;

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
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
      <div class="cloth-art" style="--c1:${item.colors[0]};--c2:${item.colors[1]}"></div>
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
      <span class="stylist-avatar" style="--avatar:${stylist.avatar}" aria-hidden="true"></span>
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
      <span class="mall-thumb" style="--mall-bg:${item.bg}" aria-hidden="true"></span>
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

function nextCoralJacketName() {
  const base = "Coral Statement Jacket";
  if (!wardrobe.some((item) => item.name === base)) return base;
  return `${base} ${wardrobe.filter((item) => item.name.startsWith(base)).length + 1}`;
}

function newPhotoItem() {
  return {
    name: nextCoralJacketName(),
    category: "jacket",
    fit: "structured",
    material: "woven crepe",
    colorName: "coral",
    color: "coral",
    formality: 4,
    warmth: 2,
    colors: ["#ff5c70", "#fb7185"],
  };
}

function renderAll() {
  updateWardrobeCount();
  renderWardrobe();
  renderFit();
  renderStylists();
  renderMall();
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
  selected = ["White Oxford Shirt", "Stone Chinos", "White Trainers", "Navy Overshirt"].filter((name) =>
    wardrobe.some((item) => item.name === name)
  );
  renderFit();
  await sendRequest();
});
document.getElementById("addItem").addEventListener("click", async () => {
  const item = newPhotoItem();
  const result = await callBackend("/api/wardrobe", { item });
  if (result?.wardrobe) {
    wardrobe = result.wardrobe;
  } else {
    wardrobe.push(item);
  }
  updateWardrobeCount();
  renderWardrobe();
});
document.getElementById("sendWishlist").addEventListener("click", () => {
  markRequestSent("Wishlist sent. If accepted, purchased items move into the wardrobe in the stylist's exact outfit order.");
});

loadState();
