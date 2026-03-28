from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import time

replication_logs = []
last_sync_time = 0
app = FastAPI(title="Valut Sync Replica UI Server")

store = {}

# =============================
# HEALTH
# =============================
@app.get("/health")
async def health():
    return {"status": "replica alive", "keys": len(store)}

# =============================
# APPLY FROM PRIMARY
# =============================
@app.post("/replica/apply")
async def apply_replica(operation: dict):
    global last_sync_time

    now = time.time()
    operation_time = operation.get("timestamp", operation.get("time_stamp", now))
    lag = now - operation_time

    replication_logs.append({
        "operation": operation,
        "lag": round(lag, 4),
        "time": time.strftime("%H:%M:%S")
    })

    last_sync_time = now

    if operation["type"] == "SET":
        store[operation["key"]] = {
            "value": operation["value"],
            "expiry": operation["expiry"]
        }

    elif operation["type"] == "DELETE":
        store.pop(operation["key"], None)

    return {"status": "applied"}
@app.get("/metrics")
async def metrics():
    return {
        "keys": len(store),
        "keys_in_store": list(store.keys()),
        "applied_operations": len(replication_logs),
        "logs": replication_logs[-10:],  # last 10 logs
        "last_sync": last_sync_time
    }
# =============================
# LOCAL KV (for UI CLI)
# =============================
@app.get("/kv/{key}")
async def get_key(key: str):
    return {"key": key, "value": store.get(key)}

@app.post("/kv")
async def set_key(item: dict):
    store[item["key"]] = {
        "value": item["value"],
        "expiry": None
    }
    return {"message": "stored"}

@app.delete("/kv/{key}")
async def delete_key(key: str):
    store.pop(key, None)
    return {"message": "deleted"}

# =============================
# UI PAGE
# =============================
@app.get("/", response_class=HTMLResponse)
async def ui():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Valut Sync Replica Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
* {
    box-sizing: border-box;
}

:root {
    --bg: #06131f;
    --bg-soft: #0d1f31;
    --card: rgba(10, 25, 40, 0.88);
    --card-strong: rgba(15, 37, 57, 0.96);
    --line: rgba(145, 200, 228, 0.16);
    --text: #ecf7ff;
    --muted: #8eb0c3;
    --cyan: #63e6ff;
    --teal: #4adeb8;
    --amber: #f6c760;
    --pink: #ff7db8;
    --shadow: 0 24px 80px rgba(0, 0, 0, 0.38);
}

body {
    margin: 0;
    min-height: 100vh;
    color: var(--text);
    font-family: "Space Grotesk", sans-serif;
    background:
        radial-gradient(circle at top left, rgba(99, 230, 255, 0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(255, 125, 184, 0.14), transparent 22%),
        linear-gradient(160deg, #04101a 0%, #071829 48%, #02070e 100%);
    padding: 32px 20px 48px;
}

.container {
    max-width: 1140px;
    margin: auto;
}

.hero {
    position: relative;
    overflow: hidden;
    background: linear-gradient(145deg, rgba(13, 31, 49, 0.95), rgba(6, 19, 31, 0.82));
    border: 1px solid var(--line);
    border-radius: 28px;
    padding: 28px;
    box-shadow: var(--shadow);
    margin-bottom: 22px;
}

.hero::after {
    content: "";
    position: absolute;
    inset: auto -40px -60px auto;
    width: 180px;
    height: 180px;
    background: radial-gradient(circle, rgba(99, 230, 255, 0.26), transparent 65%);
    pointer-events: none;
}

.eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(99, 230, 255, 0.1);
    border: 1px solid rgba(99, 230, 255, 0.18);
    color: var(--cyan);
    font-size: 12px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.hero-grid {
    display: grid;
    grid-template-columns: 1.5fr 1fr;
    gap: 18px;
    align-items: end;
    margin-top: 18px;
}

.hero h1 {
    margin: 14px 0 10px;
    font-size: clamp(32px, 5vw, 54px);
    line-height: 0.96;
    letter-spacing: -0.04em;
}

.hero p {
    margin: 0;
    max-width: 620px;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.7;
}

.hero-stats {
    display: grid;
    gap: 12px;
}

.pill {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 16px 18px;
}

.pill-label {
    color: var(--muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}

.pill-value {
    margin-top: 6px;
    font-size: 24px;
    font-weight: 700;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
    margin-bottom: 20px;
}

.shell-grid {
    display: grid;
    grid-template-columns: 1.1fr 0.9fr;
    gap: 18px;
    margin-bottom: 18px;
}

.bottom-grid {
    display: grid;
    grid-template-columns: 1.1fr 0.9fr;
    gap: 18px;
}

.card {
    background: linear-gradient(180deg, var(--card), var(--card-strong));
    border: 1px solid var(--line);
    border-radius: 24px;
    padding: 22px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
}

.card h3 {
    margin: 0 0 6px;
    font-size: 22px;
    letter-spacing: -0.03em;
}

.card-sub {
    margin: 0 0 18px;
    color: var(--muted);
    font-size: 14px;
}

.command-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}

input {
    flex: 1;
    min-width: 230px;
    border: 1px solid rgba(145, 200, 228, 0.2);
    background: rgba(255, 255, 255, 0.04);
    color: var(--text);
    padding: 14px 16px;
    border-radius: 14px;
    outline: none;
    font-family: "IBM Plex Mono", monospace;
    font-size: 14px;
}

input::placeholder {
    color: #7390a0;
}

input:focus {
    border-color: rgba(99, 230, 255, 0.4);
    box-shadow: 0 0 0 4px rgba(99, 230, 255, 0.08);
}

button {
    border: 0;
    border-radius: 14px;
    padding: 14px 18px;
    background: linear-gradient(135deg, var(--cyan), #8cf7ff);
    color: #032031;
    font-weight: 700;
    font-family: "Space Grotesk", sans-serif;
    cursor: pointer;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
    box-shadow: 0 12px 24px rgba(99, 230, 255, 0.18);
}

button:hover {
    transform: translateY(-1px);
    box-shadow: 0 16px 28px rgba(99, 230, 255, 0.24);
}

.metric {
    position: relative;
    overflow: hidden;
    min-height: 144px;
}

.metric::before {
    content: "";
    position: absolute;
    inset: auto auto -24px -24px;
    width: 110px;
    height: 110px;
    border-radius: 50%;
    opacity: 0.22;
    pointer-events: none;
}

.metric-cyan::before {
    background: radial-gradient(circle, var(--cyan), transparent 68%);
}

.metric-teal::before {
    background: radial-gradient(circle, var(--teal), transparent 68%);
}

.metric-amber::before {
    background: radial-gradient(circle, var(--amber), transparent 68%);
}

.metric-label {
    color: var(--muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}

.metric-value {
    margin-top: 12px;
    font-size: clamp(28px, 4vw, 42px);
    font-weight: 700;
    letter-spacing: -0.04em;
}

.metric-note {
    margin-top: 10px;
    color: var(--muted);
    font-size: 14px;
}

pre {
    margin: 16px 0 0;
    padding: 16px;
    border-radius: 16px;
    background: rgba(0, 0, 0, 0.26);
    border: 1px solid rgba(145, 200, 228, 0.12);
    color: #d8ebf7;
    font-family: "IBM Plex Mono", monospace;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
}

.log-box {
    max-height: 320px;
    overflow: auto;
    display: grid;
    gap: 10px;
    padding-right: 4px;
}

.log-item {
    padding: 14px 16px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(145, 200, 228, 0.1);
}

.log-head {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.log-main {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 58px;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}

.badge-set {
    background: rgba(74, 222, 184, 0.14);
    color: var(--teal);
}

.badge-del {
    background: rgba(255, 125, 184, 0.14);
    color: var(--pink);
}

.log-key {
    font-family: "IBM Plex Mono", monospace;
    font-size: 15px;
}

.empty-state {
    color: var(--muted);
    padding: 18px;
    border-radius: 16px;
    border: 1px dashed rgba(145, 200, 228, 0.18);
    text-align: center;
}

.chart-wrap {
    height: 320px;
}

.footer-note {
    margin-top: 18px;
    text-align: center;
    color: var(--muted);
    font-size: 13px;
}

@media (max-width: 920px) {
    .hero-grid,
    .shell-grid,
    .bottom-grid,
    .stats-grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 640px) {
    body {
        padding: 18px 14px 28px;
    }

    .hero,
    .card {
        border-radius: 20px;
        padding: 18px;
    }

    .command-row {
        flex-direction: column;
    }

    button,
    input {
        width: 100%;
    }
}
</style>
</head>

<body>

<div class="container">

<section class="hero">
    <span class="eyebrow">Replica node telemetry</span>
    <div class="hero-grid">
        <div>
            <h1>Valut Sync Replica Dashboard</h1>
            <p>
                Monitor replication flow, inspect recent operations, and test local KV commands
                from a cleaner control surface built for quick status checks.
            </p>
        </div>
        <div class="hero-stats">
            <div class="pill">
                <div class="pill-label">Node Status</div>
                <div class="pill-value" id="hero-status">Online</div>
            </div>
            <div class="pill">
                <div class="pill-label">Last Sync</div>
                <div class="pill-value" id="hero-sync">--</div>
            </div>
        </div>
    </div>
</section>

<section class="stats-grid">
    <div class="card metric metric-cyan">
        <div class="metric-label">Keys in Replica</div>
        <div class="metric-value" id="keys-count">0</div>
        <div class="metric-note">Current replicated key count.</div>
    </div>
    <div class="card metric metric-teal">
        <div class="metric-label">Applied Operations</div>
        <div class="metric-value" id="ops-count">0</div>
        <div class="metric-note">Total operations received from primary.</div>
    </div>
    <div class="card metric metric-amber">
        <div class="metric-label">Latest Lag</div>
        <div class="metric-value"><span id="lag">--</span>s</div>
        <div class="metric-note">Time between primary write and replica apply.</div>
    </div>
</section>

<section class="shell-grid">
<div class="card">
    <h3>Replica CLI</h3>
    <p class="card-sub">Try commands like <code>SET session abc123</code>, <code>GET session</code>, or <code>DEL session</code>.</p>
    <div class="command-row">
        <input id="cmd" placeholder="SET session_token abc123">
        <button onclick="run()">Run Command</button>
    </div>
    <pre id="output"></pre>
</div>

<div class="card">
    <h3>Replica Snapshot</h3>
    <p class="card-sub">A quick overview of the latest sync state and replica keys.</p>
    <pre id="snapshot">Waiting for metrics...</pre>
</div>
</section>

<section class="bottom-grid">
<div class="card">
    <h3>Replication Logs</h3>
    <p class="card-sub">Most recent apply events with operation type, key, and lag.</p>
    <div id="logs" class="log-box"></div>
</div>

<div class="card">
    <h3>Key Count Trend</h3>
    <p class="card-sub">Live key count history for the replica node.</p>
    <div class="chart-wrap">
    <canvas id="chart"></canvas>
    </div>
</div>
</section>

<div class="footer-note">Auto-refreshing every 2 seconds.</div>

</div>

<script>
let chart;
let keyHistory = [];

function formatClock(unixSeconds) {
    if (!unixSeconds) return "--";
    return new Date(unixSeconds * 1000).toLocaleTimeString();
}

// CLI
async function run(){
    const input = document.getElementById("cmd").value.trim().split(/\\s+/);
    const cmd = input[0].toUpperCase();

    let res;

    if(cmd==="SET" && input.length >= 3){
        res = await fetch("/kv", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({key:input[1], value:input[2]})
        });
    }
    else if(cmd==="GET" && input.length >= 2){
        res = await fetch("/kv/" + input[1]);
    }
    else if(cmd==="DEL" && input.length >= 2){
        res = await fetch("/kv/" + input[1], {method:"DELETE"});
    } else {
        document.getElementById("output").innerText =
            "Use SET <key> <value>, GET <key>, or DEL <key>.";
        return;
    }

    const data = await res.json();
    document.getElementById("output").innerText =
        JSON.stringify(data,null,2);

    loadMetrics();
}

// LIVE REFRESH
async function loadMetrics(){
    const res = await fetch("/metrics");
    const data = await res.json();

    // Logs
    const logsDiv = document.getElementById("logs");
    if (data.logs.length === 0) {
        logsDiv.innerHTML = '<div class="empty-state">No replication events yet. Once the primary sends writes, they will appear here.</div>';
    } else {
        logsDiv.innerHTML = data.logs.slice().reverse().map(l => `
            <div class="log-item">
                <div class="log-head">
                    <span>${l.time}</span>
                    <span>${l.lag}s lag</span>
                </div>
                <div class="log-main">
                    <span class="badge ${l.operation.type === "SET" ? "badge-set" : "badge-del"}">${l.operation.type}</span>
                    <span class="log-key">${l.operation.key}</span>
                </div>
            </div>
        `).join("");
    }

    // Lag
    if(data.logs.length > 0){
        document.getElementById("lag").innerText =
            data.logs[data.logs.length-1].lag;
    } else {
        document.getElementById("lag").innerText = "--";
    }

    document.getElementById("keys-count").innerText = data.keys;
    document.getElementById("ops-count").innerText = data.applied_operations;
    document.getElementById("hero-sync").innerText = formatClock(data.last_sync);
    document.getElementById("snapshot").innerText = JSON.stringify({
        keys_in_store: data.keys_in_store,
        applied_operations: data.applied_operations,
        last_sync: formatClock(data.last_sync)
    }, null, 2);

    // Chart
    keyHistory.push(data.keys);
    if(keyHistory.length > 20) keyHistory.shift();

    if(!chart){
        chart = new Chart(document.getElementById("chart"), {
            type: "line",
            data: {
                labels: keyHistory.map((_,i)=>i),
                datasets: [{
                    label: "Keys",
                    data: keyHistory,
                    borderColor: "#63e6ff",
                    backgroundColor: "rgba(99, 230, 255, 0.18)",
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: "#8cf7ff",
                    pointBorderColor: "#031723",
                    pointBorderWidth: 2,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: "#d9f4ff"
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: "#8eb0c3" },
                        grid: { color: "rgba(145, 200, 228, 0.08)" }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: "#8eb0c3", precision: 0 },
                        grid: { color: "rgba(145, 200, 228, 0.08)" }
                    }
                }
            }
        });
    } else {
        chart.data.labels = keyHistory.map((_,i)=>i);
        chart.data.datasets[0].data = keyHistory;
        chart.update();
    }
}

// Auto refresh every 2 seconds
loadMetrics();
setInterval(loadMetrics, 2000);
</script>

</body>
</html>
"""
