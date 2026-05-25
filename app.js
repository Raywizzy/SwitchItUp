const wardrobe = [
  { name:"White Oxford Shirt", category:"top", formality:4, colors:["#ffffff","#cbd5e1"] },
  { name:"Black Relaxed Tee", category:"top", formality:2, colors:["#111827","#334155"] },
  { name:"Stone Chinos", category:"bottom", formality:4, colors:["#cdbb9d","#a8906f"] },
  { name:"Dark Denim", category:"bottom", formality:2, colors:["#1e3a8a","#0f172a"] },
  { name:"White Trainers", category:"shoes", formality:3, colors:["#ffffff","#dbeafe"] },
  { name:"Navy Overshirt", category:"jacket", formality:3, colors:["#1e3a8a","#0f172a"] },
];
const stylists = [
  { name:"Tami Looks", specialty:"Smart casual · dates · brunch", rating:4.9, helped:214, paid:true },
  { name:"Kola Fits", specialty:"Streetwear · concerts · campus", rating:4.8, helped:187, paid:true },
  { name:"Ari Tailored", specialty:"Weddings · formal · business", rating:4.7, helped:143, paid:true },
  { name:"Maya FreeFit", specialty:"Budget wardrobe remix", rating:4.6, helped:91, paid:false },
];
const mall = [
  { item:"Structured navy blazer", store:"Metro Mall", price:78 },
  { item:"Minimal leather loafers", store:"StyleHub", price:64 },
  { item:"Silver chain accessory", store:"Urban Rack", price:22 },
];
let selected = ["White Oxford Shirt", "Stone Chinos", "White Trainers"];

function renderWardrobe(){
  document.getElementById("wardrobeGrid").innerHTML = wardrobe.map((item) => `
    <article class="cloth">
      <div class="cloth-art" style="--c1:${item.colors[0]};--c2:${item.colors[1]}"></div>
      <div><strong>${item.name}</strong><small>${item.category} · formality ${item.formality}/5</small></div>
      <button data-name="${item.name}" type="button">Wear</button>
    </article>
  `).join("");
  document.querySelectorAll(".cloth button").forEach(button => button.addEventListener("click", () => {
    const item = wardrobe.find(entry => entry.name === button.dataset.name);
    selected = selected.filter(name => wardrobe.find(w => w.name === name)?.category !== item.category);
    selected.push(item.name);
    renderFit();
  }));
}
function renderFit(){
  const list = document.getElementById("selectedFit");
  list.innerHTML = selected.map(item => `<li>${item}</li>`).join("");
  const top = wardrobe.find(item => item.name === selected.find(name => wardrobe.find(w => w.name === name)?.category === "top"));
  const bottom = wardrobe.find(item => item.name === selected.find(name => wardrobe.find(w => w.name === name)?.category === "bottom"));
  const shoes = wardrobe.find(item => item.name === selected.find(name => wardrobe.find(w => w.name === name)?.category === "shoes"));
  if(top) document.getElementById("avatarTop").style.background = `linear-gradient(135deg,${top.colors[0]},${top.colors[1]})`;
  if(bottom) document.getElementById("avatarBottom").style.background = `linear-gradient(135deg,${bottom.colors[0]},${bottom.colors[1]})`;
  if(shoes) document.getElementById("avatarShoes").style.background = `linear-gradient(135deg,${shoes.colors[0]},${shoes.colors[1]})`;
}
function renderStylists(){
  document.getElementById("stylistCards").innerHTML = stylists.map(stylist => `
    <article class="stylist-card"><strong>${stylist.name}</strong><span>${stylist.specialty}</span><br><b>${stylist.rating} rating · ${stylist.helped} helped · ${stylist.paid ? "Paid" : "Free"}</b></article>
  `).join("");
}
function renderMall(){
  document.getElementById("mallItems").innerHTML = mall.map(item => `
    <article class="mall-item"><strong>${item.item}</strong><span>${item.store} · £${item.price}</span></article>
  `).join("");
}
function sendRequest(){
  const occasion = document.getElementById("occasion").value;
  const budget = Number(document.getElementById("budget").value);
  const mode = document.getElementById("replaceMode").value;
  const stylist = mode === "none" ? "Maya FreeFit" : "Tami Looks";
  document.getElementById("requestOutput").textContent = `${stylist} received your ${occasion.toLowerCase()} request with £${budget} budget. Wishlist ready: ${mall[0].item}.`;
  document.getElementById("confidence").textContent = mode === "all" ? "94% remix" : "91% match";
}
document.querySelectorAll(".role-toggle button").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll(".role-toggle button").forEach(btn => btn.classList.remove("active"));
  button.classList.add("active");
  const role = button.dataset.role === "stylist" ? "Stylist / Influencer" : "Normal Person";
  document.getElementById("signedRole").textContent = role;
  document.getElementById("upgradeBtn").textContent = button.dataset.role === "stylist" ? "Subscription Active" : "Upgrade Stylist";
}));
document.getElementById("askStylist").addEventListener("click", sendRequest);
document.getElementById("styleMe").addEventListener("click", () => {
  selected = ["White Oxford Shirt", "Stone Chinos", "White Trainers"];
  renderFit();
  sendRequest();
});
document.getElementById("addItem").addEventListener("click", () => {
  wardrobe.push({ name:"Coral Statement Jacket", category:"jacket", formality:4, colors:["#ff5c70","#fb7185"] });
  renderWardrobe();
});
document.getElementById("sendWishlist").addEventListener("click", () => {
  document.getElementById("requestOutput").textContent = "Wishlist sent. If accepted, purchased items move into wardrobe with the stylist's outfit order.";
});
renderWardrobe();
renderFit();
renderStylists();
renderMall();
