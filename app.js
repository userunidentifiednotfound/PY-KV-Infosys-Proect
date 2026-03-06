/* =========================
   ELEMENTS
========================= */

const authStatus = document.getElementById("auth-status");
const logoutBtn = document.getElementById("dashboard-logout");

/* =========================
   TOKEN STORAGE
========================= */

function saveToken(token) {
  localStorage.setItem("pkv_token", token);
  updateAuthUI();
}

function getToken() {
  return localStorage.getItem("pkv_token");
}

function clearToken() {
  localStorage.removeItem("pkv_token");
  updateAuthUI();
}

/* =========================
   UI UPDATE
========================= */

function updateAuthUI() {
  const token = getToken();

  const loginCard = document.getElementById("login-card");
  const kvCard = document.getElementById("kv-card");
  const infoCard = document.getElementById("info-card");
  const userCard = document.getElementById("user-card");

  if (token) {
    authStatus.textContent = "Signed in";

    if (loginCard) loginCard.style.display = "none";
    if (kvCard) kvCard.style.display = "block";
    if (infoCard) infoCard.style.display = "block";
    if (userCard) userCard.style.display = "block";
    if (logoutBtn) logoutBtn.style.display = "block";

    fetchAndShowUser().catch(() => {});
    loadLRU();   // 🔥 Load LRU after login
  } else {
    authStatus.textContent = "Not signed in";

    if (loginCard) loginCard.style.display = "block";
    if (kvCard) kvCard.style.display = "none";
    if (infoCard) infoCard.style.display = "none";
    if (userCard) userCard.style.display = "none";
    if (logoutBtn) logoutBtn.style.display = "none";

    const ud = document.getElementById("user-details");
    if (ud) ud.textContent = "Not signed in.";
  }
}

/* =========================
   AUTH
========================= */

async function login(event) {
  event.preventDefault();

  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  try {
    const body = new URLSearchParams();
    body.append("username", username);
    body.append("password", password);

    const response = await fetch("/auth/login", {
      method: "POST",
      body,
      headers: { Accept: "application/json" }
    });

    if (!response.ok) throw new Error(await response.text());

    const data = await response.json();
    saveToken(data.access_token);

    document.getElementById("output").textContent =
      "Signed in successfully.";
  } catch (error) {
    document.getElementById("output").textContent =
      "Login error: " + error.message;
  }
}

async function fetchAndShowUser() {
  try {
    const data = await callApi("/auth/me");

    const userDetails = document.getElementById("user-details");
    if (userDetails)
      userDetails.textContent = JSON.stringify(data, null, 2);

    authStatus.textContent =
      data.username || data.full_name || "Signed in";
  } catch {
    authStatus.textContent = "Signed in";
  }
}

/* =========================
   GENERIC API
========================= */

async function callApi(path, options = {}) {
  const token = getToken();

  options.headers = options.headers || {};

  if (token) {
    options.headers["Authorization"] = "Bearer " + token;
  }

  if (options.body && typeof options.body === "object") {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  const response = await fetch(path, options);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }

  return response.json().catch(() => ({}));
}

/* =========================
   KV FUNCTIONS
========================= */

async function setKey(event) {
  event.preventDefault();

  const key = document.getElementById("set-key").value;
  const value = document.getElementById("set-value").value;
  const ttl = document.getElementById("set-ttl").value;

  const body = { key, value };
  if (ttl) body.ttl = Number(ttl);

  try {
    const result = await callApi("/kv", { method: "POST", body });

    document.getElementById("output").textContent =
      JSON.stringify(result, null, 2);

    loadLRU();  // 🔥 Refresh LRU
  } catch (error) {
    document.getElementById("output").textContent =
      "Error: " + error.message;
  }
}

async function getKey(event) {
  event.preventDefault();

  const key = document.getElementById("get-key").value;

  try {
    const result = await callApi("/kv/" + encodeURIComponent(key));

    document.getElementById("output").textContent =
      JSON.stringify(result, null, 2);

    loadLRU();  // 🔥 Refresh LRU
  } catch (error) {
    document.getElementById("output").textContent =
      "Error: " + error.message;
  }
}

async function deleteKey(event) {
  event.preventDefault();

  const key = document.getElementById("delete-key").value;

  try {
    const result = await callApi(
      "/kv/" + encodeURIComponent(key),
      { method: "DELETE" }
    );

    document.getElementById("output").textContent =
      JSON.stringify(result, null, 2);

    loadLRU();  // 🔥 Refresh LRU
  } catch (error) {
    document.getElementById("output").textContent =
      "Error: " + error.message;
  }
}

/* =========================
   LRU FUNCTION
========================= */

async function loadLRU() {
  try {
    const data = await callApi("/admin/store");

    const container = document.getElementById("lru-container");
    const info = document.getElementById("lru-info");

    if (!container || !info) return;

    container.innerHTML = "";

    data.keys_in_order.forEach((key, index) => {
      const box = document.createElement("div");
      box.className = "lru-box";
      box.innerText = key;

      if (index === 0) box.classList.add("lru-oldest");
      if (index === data.keys_in_order.length - 1)
        box.classList.add("lru-newest");

      container.appendChild(box);
    });

    info.innerText =
      "Capacity: " + data.capacity +
      "\nCurrent Size: " + data.current_size +
      "\nOrder: " + data.keys_in_order.join(" → ");

  } catch (err) {
    console.error("LRU error:", err);
  }
}

/* =========================
   HEALTH
========================= */

async function health() {
  try {
    const response = await fetch("/health");
    const data = await response.json();

    document.getElementById("output").textContent =
      JSON.stringify(data, null, 2);
  } catch (error) {
    document.getElementById("output").textContent =
      "Error: " + error.message;
  }
}

/* =========================
   EVENTS
========================= */

document.getElementById("login-form").addEventListener("submit", login);
document.getElementById("set-form").addEventListener("submit", setKey);
document.getElementById("get-form").addEventListener("submit", getKey);
document.getElementById("delete-form").addEventListener("submit", deleteKey);
document.getElementById("health-btn").addEventListener("click", health);

if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    clearToken();
    document.getElementById("output").textContent = "Signed out.";
  });
}
/* =========================
   DASHBOARD CONTROL
========================= */

function showDashboard() {

  const dashboard = document.getElementById("dashboard");
  const loginCard = document.getElementById("login-card");
  const logoutBtn = document.getElementById("dashboard-logout");

  if (dashboard) dashboard.style.display = "block";
  if (loginCard) loginCard.style.display = "none";
  if (logoutBtn) logoutBtn.style.display = "block";

}

function hideDashboard() {

  const dashboard = document.getElementById("dashboard");
  const loginCard = document.getElementById("login-card");
  const logoutBtn = document.getElementById("dashboard-logout");

  if (dashboard) dashboard.style.display = "none";
  if (loginCard) loginCard.style.display = "block";
  if (logoutBtn) logoutBtn.style.display = "none";

}
/* =========================
   LRU VISIBILITY CONTROL
========================= */

const lruCard = document.getElementById("lru-card");
const loginForm = document.getElementById("login-form");

if (loginForm) {

loginForm.addEventListener("submit", function(){

    // hide login section
    document.getElementById("login-card").style.display = "none";

    // show LRU section
    if(lruCard){
        lruCard.style.display = "block";
    }

});

}
document.getElementById("dashboard-logout").addEventListener("click", function(){

document.getElementById("login-card").style.display = "block";

document.getElementById("lru-card").style.display = "none";

});
updateAuthUI();