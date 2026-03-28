const authStatus = document.getElementById("auth-status");
const logoutBtn = document.getElementById("dashboard-logout");

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

function formatJson(data) {
  return JSON.stringify(data, null, 2);
}

function formatTime(unixSeconds) {
  if (!unixSeconds) {
    return "--";
  }

  return new Date(unixSeconds * 1000).toLocaleTimeString();
}

async function callApi(path, options = {}) {
  const token = getToken();
  const request = { ...options, headers: { ...(options.headers || {}) } };

  if (token) {
    request.headers.Authorization = `Bearer ${token}`;
  }

  if (request.body && typeof request.body === "object") {
    request.headers["Content-Type"] = "application/json";
    request.body = JSON.stringify(request.body);
  }

  const response = await fetch(path, request);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }

  return response.json().catch(() => ({}));
}

function updateAuthUI() {
  const token = getToken();
  const dashboardShell = document.getElementById("dashboard-shell");
  const heroPanel = document.querySelector(".hero-panel");
  const loginCard = document.getElementById("login-card");
  const kvCard = document.getElementById("kv-card");
  const infoCard = document.getElementById("info-card");
  const walCard = document.getElementById("wal-card");
  const lruCard = document.getElementById("lru-card");
  const replicationCard = document.getElementById("replication-card");
  const cliCard = document.getElementById("cli-card");
  const userDetails = document.getElementById("user-details");

  if (token) {
    authStatus.textContent = "Signed in";
    document.body.classList.remove("login-mode");
    document.body.classList.add("dashboard-mode");
    if (dashboardShell) dashboardShell.style.display = "grid";
    if (heroPanel) heroPanel.style.display = "grid";
    if (loginCard) loginCard.style.display = "none";
    if (loginCard) loginCard.classList.remove("unlocking");
    if (kvCard) kvCard.style.display = "block";
    if (infoCard) infoCard.style.display = "block";
    if (walCard) walCard.style.display = "block";
    if (lruCard) lruCard.style.display = "block";
    if (replicationCard) replicationCard.style.display = "block";
    if (cliCard) cliCard.style.display = "block";
    if (logoutBtn) logoutBtn.style.display = "block";

    fetchAndShowUser().catch(() => {
      authStatus.textContent = "Signed in";
    });
    loadLRU().catch(() => {});
    loadWalInfo().catch(() => {});
    checkReplica().catch(() => {});
    return;
  }

  authStatus.textContent = "Not signed in";
  document.body.classList.remove("auth-transition");
  document.body.classList.remove("dashboard-mode");
  document.body.classList.add("login-mode");
  if (dashboardShell) dashboardShell.style.display = "none";
  if (heroPanel) heroPanel.style.display = "none";
  if (loginCard) loginCard.style.display = "block";
  if (loginCard) loginCard.classList.remove("unlocking");
  if (kvCard) kvCard.style.display = "none";
  if (infoCard) infoCard.style.display = "none";
  if (walCard) walCard.style.display = "none";
  if (lruCard) lruCard.style.display = "none";
  if (replicationCard) replicationCard.style.display = "none";
  if (cliCard) cliCard.style.display = "none";
  if (logoutBtn) logoutBtn.style.display = "none";
  if (userDetails) userDetails.textContent = "Not signed in.";
}

async function login(event) {
  event.preventDefault();

  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;
  const loginCard = document.getElementById("login-card");

  try {
    const body = new URLSearchParams();
    body.append("username", username);
    body.append("password", password);

    const response = await fetch("/auth/login", {
      method: "POST",
      body,
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    const data = await response.json();
    if (loginCard) loginCard.classList.add("unlocking");
    document.body.classList.add("auth-transition");
    await new Promise((resolve) => setTimeout(resolve, 1050));
    saveToken(data.access_token);
    document.getElementById("output").textContent = "Signed in successfully.";
  } catch (error) {
    if (loginCard) loginCard.classList.remove("unlocking");
    document.body.classList.remove("auth-transition");
    document.getElementById("output").textContent = `Login error: ${error.message}`;
  }
}

async function fetchAndShowUser() {
  const data = await callApi("/auth/me");
  const userDetails = document.getElementById("user-details");

  if (userDetails) {
    userDetails.textContent = formatJson(data);
  }

  authStatus.textContent = data.username || data.full_name || "Signed in";
}

async function setKey(event) {
  event.preventDefault();

  const key = document.getElementById("set-key").value;
  const value = document.getElementById("set-value").value;
  const ttl = document.getElementById("set-ttl").value;
  const body = { key, value };

  if (ttl) {
    body.ttl = Number(ttl);
  }

  try {
    const result = await callApi("/kv", { method: "POST", body });
    document.getElementById("output").textContent = formatJson(result);
    await Promise.all([loadLRU(), loadWalInfo(), checkReplica()]);
  } catch (error) {
    document.getElementById("output").textContent = `Error: ${error.message}`;
  }
}

async function getKey(event) {
  event.preventDefault();

  const key = document.getElementById("get-key").value;

  try {
    const result = await callApi(`/kv/${encodeURIComponent(key)}`);
    document.getElementById("output").textContent = formatJson(result);
    await loadLRU();
  } catch (error) {
    document.getElementById("output").textContent = `Error: ${error.message}`;
  }
}

async function deleteKey(event) {
  event.preventDefault();

  const key = document.getElementById("delete-key").value;

  try {
    const result = await callApi(`/kv/${encodeURIComponent(key)}`, { method: "DELETE" });
    document.getElementById("output").textContent = formatJson(result);
    await Promise.all([loadLRU(), loadWalInfo(), checkReplica()]);
  } catch (error) {
    document.getElementById("output").textContent = `Error: ${error.message}`;
  }
}

async function loadLRU() {
  try {
    const data = await callApi("/admin/store");
    const container = document.getElementById("lru-container");
    const info = document.getElementById("lru-info");

    if (!container || !info) {
      return;
    }

    container.innerHTML = "";

    data.keys_in_order.forEach((key, index) => {
      const box = document.createElement("div");
      box.className = "lru-box";
      box.innerText = key;

      if (index === 0) box.classList.add("lru-oldest");
      if (index === data.keys_in_order.length - 1) box.classList.add("lru-newest");

      container.appendChild(box);
    });

    info.innerText =
      `Capacity: ${data.capacity}\n` +
      `Current Size: ${data.current_size}\n` +
      `Order: ${data.keys_in_order.join(" -> ")}`;
  } catch (error) {
    document.getElementById("lru-info").textContent = `Error: ${error.message}`;
  }
}

async function health() {
  try {
    const data = await callApi("/health");
    document.getElementById("output").textContent = formatJson(data);
  } catch (error) {
    document.getElementById("output").textContent = `Error: ${error.message}`;
  }
}

async function loadWalInfo() {
  try {
    const data = await callApi("/admin/wal-status");
    document.getElementById("wal-size").textContent = `${data.log_size_bytes} bytes`;
    document.getElementById("wal-entries").textContent = data.entries;
    document.getElementById("wal-info").textContent = formatJson(data);
  } catch (error) {
    document.getElementById("wal-info").textContent = `Error: ${error.message}`;
  }
}

async function runCompaction() {
  try {
    const result = await callApi("/admin/compact", { method: "POST" });
    document.getElementById("wal-compaction").textContent = new Date().toLocaleTimeString();
    document.getElementById("wal-info").textContent = formatJson(result);
    await loadWalInfo();
  } catch (error) {
    document.getElementById("wal-info").textContent = `Error: ${error.message}`;
  }
}

async function checkReplica() {
  try {
    const data = await callApi("/admin/replica-status");
    const statusText = data.in_sync ? `${data.status} (in sync)` : data.status;

    document.getElementById("replica-status").textContent = statusText;
    document.getElementById("replica-sync").textContent = formatTime(data.last_sync);
    document.getElementById("replica-info").textContent = formatJson(data);
  } catch (error) {
    document.getElementById("replica-status").textContent = "offline";
    document.getElementById("replica-info").textContent = `Error: ${error.message}`;
  }
}

async function syncReplica() {
  try {
    const data = await callApi("/admin/sync", { method: "POST" });
    document.getElementById("replica-info").textContent = formatJson(data);
    await checkReplica();
  } catch (error) {
    document.getElementById("replica-info").textContent = `Error: ${error.message}`;
  }
}

async function runCli() {
  const raw = document.getElementById("cli-input").value.trim();
  const input = raw.split(/\s+/);
  const cmd = (input[0] || "").toUpperCase();

  try {
    let result;

    if (cmd === "SET") {
      result = await callApi("/kv", {
        method: "POST",
        body: { key: input[1], value: input[2] },
      });
    } else if (cmd === "GET") {
      result = await callApi(`/kv/${encodeURIComponent(input[1])}`);
    } else if (cmd === "DEL") {
      result = await callApi(`/kv/${encodeURIComponent(input[1])}`, { method: "DELETE" });
    } else {
      throw new Error("Use SET <key> <value>, GET <key>, or DEL <key>.");
    }

    document.getElementById("cli-output").textContent = formatJson(result);
    await Promise.all([loadLRU(), loadWalInfo(), checkReplica()]);
  } catch (error) {
    document.getElementById("cli-output").textContent = `Error: ${error.message}`;
  }
}

document.getElementById("login-form").addEventListener("submit", login);
document.getElementById("set-form").addEventListener("submit", setKey);
document.getElementById("get-form").addEventListener("submit", getKey);
document.getElementById("delete-form").addEventListener("submit", deleteKey);
document.getElementById("health-btn").addEventListener("click", health);
document.getElementById("refresh-lru").addEventListener("click", loadLRU);
document.getElementById("clear-log").addEventListener("click", () => {
  clearToken();
  document.getElementById("output").textContent = "Saved token cleared.";
});
document.getElementById("refresh-wal").addEventListener("click", loadWalInfo);
document.getElementById("compact-wal").addEventListener("click", runCompaction);
document.getElementById("check-replica").addEventListener("click", checkReplica);
document.getElementById("sync-replica").addEventListener("click", syncReplica);
document.getElementById("run-cli").addEventListener("click", runCli);

if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    clearToken();
    document.getElementById("output").textContent = "Signed out.";
  });
}

updateAuthUI();
