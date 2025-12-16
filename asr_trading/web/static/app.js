const API = {
    status: '/api/system/status',
    activity: '/api/system/activity',
    logs: '/api/system/logs?limit=20',
    balance: '/api/account/balance',
    decision: '/api/decision/last',
    rejected: '/api/trade/last-rejected',
    control: {
        autoEnable: '/api/mode/auto/enable',
        autoDisable: '/api/mode/auto/disable',
        setMode: '/api/mode/set',
        monitorStart: '/api/monitor/start',
        monitorStop: '/api/monitor/stop',
        paperTrade: '/api/trade/paper',
        liveTrade: '/api/trade/live',
        refreshBal: '/api/account/refresh',
        setMockBal: '/api/settings/balance',
        kill: '/api/system/kill',
        watchlist: '/api/settings/watchlist', // New
        monitorCurrent: '/api/monitor/current' // New
    }
};

// Polling intervals
setInterval(refreshDashboard, 2000); // 2s polling
setInterval(loadConfig, 5000); // 5s for config

async function refreshDashboard() {
    try {
        await Promise.all([
            loadStatus(),
            loadActivity(),
            loadBalance(),
            loadDecision(),
            loadLogs(),
            loadPending()
        ]);
        updateConnectionState("CONNECTED");
    } catch (e) {
        updateConnectionState("DISCONNECTED");
        console.error("Polling error:", e);
    }
}

// ... (Modal Logic skipped) ...

async function loadStatus() {
    const data = await get(API.status);
    setText('market-state', data.marketState);
    setText('feed-status', data.dataFeed);
    setText('trading-mode', data.tradingMode);
    setText('exec-mode', data.executionMode);
    setText('bot-status', data.telegramBot);

    // Algo Status
    setText('algo-status', data.monitor);
    const algoEl = document.getElementById('algo-status');
    if (data.monitor === "RUNNING") algoEl.className = "status-ok";
    else algoEl.className = "status-warn";
}

async function loadConfig() {
    try {
        const data = await get(API.control.monitorCurrent);
        // data = { symbols: [], detail, running }
        const display = document.getElementById('cfg-display');
        display.innerText = "Current: " + (data.symbols || []).join(", ");

        // Also update Algo Status from here if needed, but loadStatus covers it.
    } catch (e) {/* ignore */ }
}

async function updateWatchlist() {
    const el = document.getElementById('cfg-watchlist');
    const val = el.value;
    if (!val) { alert("Enter symbols separated by comma"); return; }

    if (!await showConfirmModal("Update Watchlist? This resets the cycle.")) return;

    try {
        const res = await post(API.control.watchlist, { symbols: val });
        announce(res.message);
        el.value = ""; // Clear input on success
        loadConfig(); // Refresh display
    } catch (e) {
        announce("Failed: " + e.message);
    }
}

async function setMode(mode) {
    if (!await showConfirmModal(`Switch to ${mode} mode?`)) return;
    try {
        const res = await post(API.control.setMode, { mode: mode });
        announce(res.message);
        refreshDashboard();
    } catch (e) {
        announce("Mode Switch Failed: " + e.message);
    }
}

// --- ACCESSIBLE MODAL LOGIC ---
function showConfirmModal(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('custom-modal');
        const body = document.getElementById('modal-body');
        const yes = document.getElementById('btn-modal-yes');
        const no = document.getElementById('btn-modal-cancel');
        const announcer = document.getElementById('a11y-announcer');

        // 1. Capture Focus
        const lastActiveElement = document.activeElement;

        body.innerText = message;
        modal.style.display = 'flex';
        yes.focus(); // Move focus to confirmation button

        // Announce modal open
        announcer.innerText = "Confirmation needed: " + message;

        // 2. Focus Trap
        const handleTab = (e) => {
            if (e.key === 'Tab') {
                if (e.shiftKey) { // Shift + Tab
                    if (document.activeElement === yes) {
                        e.preventDefault();
                        no.focus();
                    }
                } else { // Tab
                    if (document.activeElement === no) {
                        e.preventDefault();
                        yes.focus();
                    }
                }
            } else if (e.key === 'Escape') {
                close(false);
            }
        };
        modal.addEventListener('keydown', handleTab);

        // Cleanup function
        function close(result) {
            modal.style.display = 'none';
            modal.removeEventListener('keydown', handleTab);
            yes.onclick = null;
            no.onclick = null;
            resolve(result);

            // 3. Restore Focus
            if (lastActiveElement) lastActiveElement.focus();
        }

        yes.onclick = () => close(true);
        no.onclick = () => close(false);
    });
}
// -----------------------------

// 0. Pending Approvals (Priority for Screen Readers)
let announcedIds = new Set();

async function loadPending() {
    const data = await get('/api/trade/pending');
    const panel = document.getElementById('approval-panel');
    const list = document.getElementById('pending-list');

    if (data.length > 0) {
        panel.style.display = 'block';
        list.innerHTML = data.map(p => `
            <div class="approval-card" role="alert">
                <div class="approval-info">
                    <h3>APPROVAL REQUIRED ("${p.strategy}")</h3>
                    <p><strong>${p.action}</strong> ${p.quantity} shares of <strong>${p.symbol}</strong></p>
                    <div style="font-size: 0.9em; margin: 5px 0; color: #ccc;">
                        <span>Entry: ${p.entry || 'MKT'}</span> | 
                        <span style="color: #ff6b6b;">SL: ${p.sl.toFixed(2)}</span> | 
                        <span style="color: #51cf66;">TP: ${p.tp.toFixed(2)}</span>
                    </div>
                    <p style="font-size: 0.85em;">Confidence: ${(p.confidence * 100).toFixed(0)}%</p>
                </div>
                <div class="approval-actions">
                    <button onclick="approveTrade('${p.plan_id}')" class="btn success" aria-label="Execute Trade: ${p.action} ${p.quantity} ${p.symbol}">✅ EXECUTE</button>
                    <button onclick="rejectTrade('${p.plan_id}')" class="btn danger" aria-label="Reject Trade: ${p.action} ${p.quantity} ${p.symbol}">❌ REJECT</button>
                </div>
            </div>
        `).join('');

        // Announce new items
        data.forEach(p => {
            if (!announcedIds.has(p.plan_id)) {
                announce(`ALERT: New Pending Trade. ${p.action} ${p.quantity} ${p.symbol}.`);
                announcedIds.add(p.plan_id);
            }
        });
    } else {
        panel.style.display = 'none';
        list.innerHTML = '';
        announcedIds.clear();
    }
}

async function approveTrade(id) {
    if (!await showConfirmModal("CONFIRM EXECUTION? This is Real Money.")) return;
    try {
        const res = await post(`/api/trade/approve/${id}`);
        announce("Trade EXECUTED: " + res.status);
        refreshDashboard();
    } catch (e) {
        announce("Execution Error: " + e.message);
    }
}

async function rejectTrade(id) {
    await post(`/api/trade/reject/${id}`);
    announce("Trade Rejected");
    refreshDashboard();
}

// New Manual Trade Logic
let lastValidatedTrade = null;

async function checkTrade() {
    const sym = document.getElementById('man-symbol').value;
    const act = document.getElementById('man-action').value;
    const qtyInput = document.getElementById('man-qty');
    const qty = parseInt(qtyInput ? qtyInput.value : 1) || 1;
    const resDiv = document.getElementById('man-result');
    const execBtn = document.getElementById('btn-exec-man');

    if (!sym) { announce("Enter a symbol first."); return; }

    announce(`Analyzing ${act} ${qty} shares of ${sym}...`);
    resDiv.innerText = "Running Strategy Analysis...";
    resDiv.className = "status-text";
    execBtn.disabled = true;

    try {
        const res = await post('/api/trade/validate', { symbol: sym, action: act, quantity: qty });

        // Update UI
        const sugDiv = document.getElementById('man-suggestion');
        const riskDiv = document.getElementById('man-risk');
        if (sugDiv) sugDiv.innerText = res.suggestion ? `Suggestion: ${res.suggestion}` : '';
        if (riskDiv) riskDiv.innerText = res.risk_analysis ? `Risk: ${res.risk_analysis}` : '';

        // Handle Result Types (Unified API)
        if (res.result === "VALID") {
            // Valid
            lastValidatedTrade = { symbol: sym, action: act, quantity: qty, price: res.price, confidence: res.confidence };
            resDiv.innerText = `✅ Verified. ${res.message}`;
            resDiv.className = "status-text status-ok";
            announce(`Strategy Match! ${res.message}. Execute Enabled.`);

            // Enable Buttons
            const btnLive = document.getElementById('btn-exec-man');
            const btnPaper = document.getElementById('btn-exec-paper');
            if (btnLive) btnLive.disabled = false;
            if (btnPaper) btnPaper.disabled = false;

        } else if (res.result === "WARNING") {
            // Warning
            lastValidatedTrade = { symbol: sym, action: act, quantity: qty, price: res.price, confidence: res.confidence };
            resDiv.innerText = `⚠️ ${res.message}`;
            resDiv.className = "status-text status-warn";
            announce(`Warning. ${res.message}. You can still execute.`);

            // Enable Buttons (User Override)
            const btnLive = document.getElementById('btn-exec-man');
            const btnPaper = document.getElementById('btn-exec-paper');
            if (btnLive) btnLive.disabled = false;
            if (btnPaper) btnPaper.disabled = false;

        } else {
            // REJECTED (Hard or Strategy)
            // Explicit Reason Handling requested by User
            lastValidatedTrade = null;
            resDiv.innerText = `🛑 REJECTED: ${res.message}`; // Using message field
            resDiv.className = "status-text status-err";
            announce(`Trade Rejected. Reason: ${res.message}`);
        }

    } catch (e) {
        resDiv.innerText = "Error: " + e.message;
        announce(`Analysis Failed: ${e.message}`);
    }
}

async function executeManual(isPaper = false) {
    if (!lastValidatedTrade) return;
    const mode = isPaper ? "PAPER" : "LIVE";

    if (!await showConfirmModal(`Confirm ${mode} Execution: ${lastValidatedTrade.action} ${lastValidatedTrade.quantity} ${lastValidatedTrade.symbol}?`)) {
        announce("Execution Cancelled.");
        return;
    }

    announce("Executing Order...");
    try {
        const endpoint = isPaper ? API.control.paperTrade : API.control.liveTrade;
        const res = await post(endpoint, { confirm: true, ...lastValidatedTrade });
        announce(`Order Executed! ID: ${res.tradeId}. Status: ${res.status}`);

        if (res.status === "PENDING_APPROVAL") {
            alert("Order HELD for Approval (Semi-Auto). Check Pending List."); // Safe to keep basic alert or use announce
        }

        // Reset
        lastValidatedTrade = null;
        refreshDashboard();

    } catch (e) {
        announce("Execution Failed: " + e.message);
    }
}

// 1. System Status


// 2. Activity (Critical)
async function loadActivity() {
    const data = await get(API.activity);
    setText('act-state', data.state);
    setText('act-instrument', data.instrument);
    setText('act-strategy', data.strategy);
    setText('act-detail', data.message);

    // Visual cue
    const box = document.getElementById('activity-panel');
    if (data.state === "EXECUTING") box.className = "panel highlight-panel pulsing";
    else box.className = "panel highlight-panel";
}

// 3. Balance
async function loadBalance() {
    const data = await get(API.balance);
    setMoney('bal-avail', data.availableBalance);
    setMoney('bal-used', data.usedMargin);
    setMoney('bal-risk', data.dailyRiskUsed);
}

// 4. Decision
async function loadDecision() {
    const data = await get(API.decision);
    setText('dec-strategy', data.strategy);
    setText('dec-result', data.decision);
    setText('dec-reason', data.message);
    setText('dec-conf', (data.confidence * 100).toFixed(1) + '%');
}

// 5. Logs
async function loadLogs() {
    const data = await get(API.logs);
    const list = document.getElementById('log-list');
    const html = data.logs.slice().reverse().map(l => `<li>${l}</li>`).join('');
    if (list.innerHTML !== html) {
        list.innerHTML = html;
    }
}

// Actions
async function toggleAuto(enable) {
    if (!await showConfirmModal(`Confirm: ${enable ? 'ENABLE' : 'DISABLE'} Auto Mode?`)) return;
    const url = enable ? API.control.autoEnable : API.control.autoDisable;
    const res = await post(url);
    announce(res.message);
    refreshDashboard();
}

async function toggleMonitor(start) {
    const url = start ? API.control.monitorStart : API.control.monitorStop;
    const res = await post(url);
    announce(res.message);
    refreshDashboard();
}

refreshDashboard();
// This brace was removed: }



async function refreshBalanceAction() {
    announce("Refreshing Balance...");
    const res = await post(API.control.refreshBal);
    announce(res.message);
}

async function setMockBalance() {
    const input = document.getElementById('mock-bal-input');
    const val = parseFloat(input.value);
    if (!val || val <= 0) {
        alert("Enter a positive number");
        return;
    }

    try {
        const res = await post(API.control.setMockBal, { amount: val });
        announce(`Mock Capital Set to ₹${val}`);
        input.value = "";
        refreshDashboard();
    } catch (e) {
        alert("Failed: " + e.message);
    }
}

async function triggerKill() {
    if (!await showConfirmModal("EMERGENCY KILL SWITCH? This will stop all systems.")) return;
    announce("SENDING KILL SIGNAL");
    await post(API.control.kill);
    alert("SYSTEM HALTED");
}

// Utils
async function get(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
}

async function post(url, body = {}) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el && el.innerText !== String(val)) el.innerText = val || '--';
}

function setMoney(id, val) {
    const el = document.getElementById(id);
    if (el) el.innerText = '₹' + (val || 0).toLocaleString();
}

function updateConnectionState(state) {
    const el = document.getElementById('conn-status');
    el.innerText = state;
    el.className = state === "CONNECTED" ? "status-ok" : "status-err";
}

function announce(msg) {
    const el = document.getElementById('a11y-announcer');
    el.innerText = msg;
    // Clear after read to allow repeating same message if needed
    // setTimeout(() => { el.innerText = ''; }, 3000); // Optional cleanup
}
