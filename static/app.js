// ==========================================================================
// TRADING BOT AI DASHBOARD — CLIENT LOGIC (STITCH REVISION)
// Features: Auto-Polling, Theme Toggle, Equity Curve, PWA Offline, Filtering
// ==========================================================================

let activeTab = 'all';
let tradesCache = [];
let isFetching = false;
let equityHistory = [];

document.addEventListener('DOMContentLoaded', () => {
    initUI();

    // Register PWA Service Worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('PWA SW registered:', reg.scope))
            .catch(err => console.log('SW error:', err));
    }

    // Restore saved theme
    const savedTheme = localStorage.getItem('pwa_theme') || 'dark';
    applyTheme(savedTheme);

    // Restore equity history from cache
    const cachedEquity = localStorage.getItem('pwa_equity_history');
    if (cachedEquity) {
        try { equityHistory = JSON.parse(cachedEquity); } catch(e) {}
    }

    fetchDashboardData();
    setInterval(fetchDashboardData, 3000);

    // Init Lucide icons
    if (window.lucide) window.lucide.createIcons();
});

// ======== THEME TOGGLE ========
function applyTheme(theme) {
    document.body.classList.remove('theme-dark', 'theme-light');
    document.body.classList.add(`theme-${theme}`);
    localStorage.setItem('pwa_theme', theme);

    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.setAttribute('data-lucide', theme === 'dark' ? 'sun' : 'moon');
        if (window.lucide) window.lucide.createIcons();
    }
}

function toggleTheme() {
    const current = localStorage.getItem('pwa_theme') || 'dark';
    applyTheme(current === 'dark' ? 'light' : 'dark');
}

// ======== UI INITIALIZATION ========
function initUI() {
    // Theme toggle
    document.getElementById('btn-theme-toggle').addEventListener('click', toggleTheme);

    // QR Modal
    const btnShowQr = document.getElementById('btn-show-qr');
    const btnCloseQr = document.getElementById('btn-close-qr');
    const modalQr = document.getElementById('modal-qr');
    const btnCopyUrl = document.getElementById('btn-copy-url');

    btnShowQr.addEventListener('click', () => modalQr.classList.remove('hidden'));
    btnCloseQr.addEventListener('click', () => modalQr.classList.add('hidden'));
    modalQr.addEventListener('click', (e) => {
        if (e.target === modalQr) modalQr.classList.add('hidden');
    });

    btnCopyUrl.addEventListener('click', () => {
        const urlText = document.getElementById('qr-url-text').innerText;
        navigator.clipboard.writeText(urlText).then(() => {
            btnCopyUrl.innerText = "✓ Tersalin!";
            setTimeout(() => btnCopyUrl.innerText = "Salin URL", 2000);
        });
    });
}

// ======== TAB SWITCHING ========
function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`tab-${tab}`).classList.add('active');
    renderTrades(tradesCache);
}

// ======== DATA FETCHING ========
async function fetchDashboardData(isManual = false) {
    if (isFetching && !isManual) return;
    isFetching = true;

    try {
        const [summaryRes, statusRes, posRes, tradesRes] = await Promise.all([
            fetch('/api/summary'),
            fetch('/api/status'),
            fetch('/api/positions'),
            fetch('/api/trades')
        ]);

        if (!summaryRes.ok && !statusRes.ok) throw new Error("SERVER_UNREACHABLE");

        if (summaryRes.ok) {
            const data = await summaryRes.json();
            if (data.offline) throw new Error("PC_OFFLINE");
            updateSummary(data);
            localStorage.setItem('pwa_summary', JSON.stringify(data));
        }

        if (statusRes.ok) {
            const data = await statusRes.json();
            if (!data.offline) {
                updateStatus(data);
                localStorage.setItem('pwa_status', JSON.stringify(data));
            }
        }

        if (posRes.ok) {
            const data = await posRes.json();
            if (!Array.isArray(data) || !data.offline) {
                renderPositions(data);
                localStorage.setItem('pwa_positions', JSON.stringify(data));
            }
        }

        if (tradesRes.ok) {
            const data = await tradesRes.json();
            if (!Array.isArray(data) || !data.offline) {
                tradesCache = data;
                renderTrades(tradesCache);
                localStorage.setItem('pwa_trades', JSON.stringify(data));
            }
        }

        localStorage.setItem('pwa_last_sync', new Date().toLocaleTimeString('id-ID'));

        // Online UI
        const offlineBanner = document.getElementById('offline-banner');
        if (offlineBanner) offlineBanner.classList.add('hidden');
        document.getElementById('live-text').innerText = "LIVE";
        document.getElementById('engine-status').innerText = "ONLINE";

    } catch (err) {
        console.warn("Offline mode activated:", err);
        loadOfflineSnapshot();
    } finally {
        isFetching = false;
    }
}

function loadOfflineSnapshot() {
    const offlineBanner = document.getElementById('offline-banner');
    if (offlineBanner) offlineBanner.classList.remove('hidden');

    const lastSync = localStorage.getItem('pwa_last_sync') || '—';
    document.getElementById('live-text').innerText = `OFFLINE`;
    document.getElementById('engine-status').innerText = "OFFLINE";

    try { updateSummary(JSON.parse(localStorage.getItem('pwa_summary'))); } catch(e) {}
    try { updateStatus(JSON.parse(localStorage.getItem('pwa_status'))); } catch(e) {}
    try { renderPositions(JSON.parse(localStorage.getItem('pwa_positions'))); } catch(e) {}
    try {
        tradesCache = JSON.parse(localStorage.getItem('pwa_trades')) || [];
        renderTrades(tradesCache);
    } catch(e) {}
}

// ======== UPDATE SUMMARY ========
function updateSummary(data) {
    if (!data) return;
    document.getElementById('val-balance').innerText = `$${data.current_balance.toFixed(2)}`;
    document.getElementById('val-equity').innerText = `$${data.equity.toFixed(2)}`;

    const flEl = document.getElementById('val-floating');
    const flVal = data.floating_profit || 0;
    flEl.innerText = `${flVal >= 0 ? '+' : ''}$${flVal.toFixed(2)}`;
    flEl.className = 'stat-value ' + (flVal > 0 ? 'positive' : (flVal < 0 ? 'negative' : 'neutral'));

    const wr = data.win_rate || 0;
    document.getElementById('val-winrate').innerText = `${wr.toFixed(0)}%`;

    const netPl = data.net_profit || 0;
    const netEl = document.getElementById('val-netpl');
    netEl.innerText = `${netPl >= 0 ? '+' : ''}$${netPl.toFixed(2)}`;
    netEl.className = 'stat-value ' + (netPl > 0 ? 'positive' : (netPl < 0 ? 'negative' : 'neutral'));

    const roi = data.roi_pct || 0;
    const roiPill = document.getElementById('roi-pill');
    const roiText = document.getElementById('val-roi');
    roiText.innerText = `${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%`;
    roiPill.className = 'roi-badge ' + (roi >= 0 ? 'positive' : 'negative');

    // Progress bar
    const totalTrades = data.total_trades || 0;
    const pct = Math.min(100, (totalTrades / 100) * 100);
    document.getElementById('progress-count').innerText = `${totalTrades} / 100 Trade`;
    document.getElementById('progress-bar-fill').style.width = `${Math.max(2, pct)}%`;
    document.getElementById('progress-pct').innerText = `${pct.toFixed(1)}%`;

    // Equity Curve Update
    updateEquityCurve(data.current_balance);

    // Sync time
    document.getElementById('last-sync-time').innerText = data.last_updated || new Date().toLocaleTimeString('id-ID');
}

// ======== EQUITY CURVE ========
function updateEquityCurve(balance) {
    equityHistory.push(balance);
    if (equityHistory.length > 40) equityHistory.shift();
    localStorage.setItem('pwa_equity_history', JSON.stringify(equityHistory));

    const peak = Math.max(...equityHistory);
    document.getElementById('equity-peak').innerText = `Tertinggi: $${peak.toFixed(2)}`;

    if (equityHistory.length < 2) return;

    const minVal = Math.min(...equityHistory);
    const maxVal = Math.max(...equityHistory);
    const range = maxVal - minVal || 1;
    const w = 320;
    const h = 55;
    const stepX = w / (equityHistory.length - 1);

    let linePoints = [];
    equityHistory.forEach((val, i) => {
        const x = i * stepX;
        const y = h - ((val - minVal) / range) * (h - 5);
        linePoints.push(`${x.toFixed(1)} ${y.toFixed(1)}`);
    });

    const linePath = `M ${linePoints.join(' L ')}`;
    const fillPath = `${linePath} L ${w} 60 L 0 60 Z`;

    document.getElementById('eq-line').setAttribute('d', linePath);
    document.getElementById('eq-fill').setAttribute('d', fillPath);

    const lastX = (equityHistory.length - 1) * stepX;
    const lastY = h - ((equityHistory[equityHistory.length - 1] - minVal) / range) * (h - 5);
    document.getElementById('eq-dot').setAttribute('cx', lastX.toFixed(1));
    document.getElementById('eq-dot').setAttribute('cy', lastY.toFixed(1));
}

// ======== UPDATE STATUS ========
function updateStatus(data) {
    if (!data) return;

    // Bot status badges
    if (data.bots) {
        updateBotBadge('status-m15', data.bots.m15_running);
        updateBotBadge('status-m5', data.bots.m5_running);
    }

    // Macro alert
    if (data.radar) {
        const macroCard = document.getElementById('macro-alert-card');
        const title = document.getElementById('macro-title');
        const desc = document.getElementById('macro-desc');
        const impact = document.getElementById('macro-impact');
        const alert = data.radar.macro_alert || '';

        title.innerText = alert.replace(/[🟢⚠️]/g, '').trim();
        desc.innerText = data.radar.macro_details || '';

        if (alert.includes('STABIL') || alert.includes('NORMAL')) {
            macroCard.className = 'card card-macro stable';
            impact.innerText = 'Rendah';
        } else {
            macroCard.className = 'card card-macro';
            impact.innerText = 'Dampak Tinggi';
        }
    }

    if (data.public_url) {
        const qrText = document.getElementById('qr-url-text');
        if (qrText && qrText.innerText !== data.public_url) {
            qrText.innerText = data.public_url;
            const qrImg = document.getElementById('qr-image');
            if (qrImg) qrImg.src = '/api/qr?t=' + Date.now();
        }
    }

    if (data.server_time) {
        document.getElementById('last-sync-time').innerText = data.server_time;
    }
}


function updateBotBadge(elementId, isRunning) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (isRunning) {
        el.className = 'status-badge active';
        el.innerHTML = '<span class="status-dot"></span>Aktif scanning';
    } else {
        el.className = 'status-badge inactive';
        el.innerHTML = '<span class="status-dot"></span>Tidak aktif';
    }
}

// ======== RENDER POSITIONS ========
function renderPositions(positions) {
    const container = document.getElementById('positions-list');
    const countEl = document.getElementById('pos-count');
    if (!positions || !Array.isArray(positions)) positions = [];

    countEl.innerText = positions.length;

    if (positions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon-wrap"><i data-lucide="coffee"></i></div>
                <h5>Tidak Ada Posisi Terbuka</h5>
                <p>Bot sedang menunggu setup terbaik sesuai probabilitas model machine learning.</p>
            </div>`;
        if (window.lucide) window.lucide.createIcons();
        return;
    }

    let html = '';
    positions.forEach(p => {
        const isBuy = p.type === 'BUY';
        const profitClass = p.profit >= 0 ? 'positive' : 'negative';
        html += `
        <div class="pos-card">
            <div class="pos-top">
                <div>
                    <span class="pos-type ${isBuy ? 'buy' : 'sell'}">${p.type}</span>
                    <span style="font-size:10px;color:var(--text-muted);margin-left:6px;">${p.bot_tag}</span>
                </div>
                <span class="pos-profit ${profitClass}">${p.profit >= 0 ? '+' : ''}$${p.profit.toFixed(2)}</span>
            </div>
            <div class="pos-details">
                <div><span class="label-muted">Entry</span><span class="pos-detail-val">$${p.price_open.toFixed(2)}</span></div>
                <div><span class="label-muted">Current</span><span class="pos-detail-val">$${p.price_current.toFixed(2)}</span></div>
                <div><span class="label-muted">Pips</span><span class="pos-detail-val">${p.pips > 0 ? '+' : ''}${p.pips}</span></div>
            </div>
        </div>`;
    });

    container.innerHTML = html;
}

// ======== RENDER TRADES ========
function renderTrades(trades) {
    const container = document.getElementById('section-trades');
    const countEl = document.getElementById('trades-count');
    if (!trades || !Array.isArray(trades)) trades = [];

    // Filter by tab
    let filtered = trades;
    if (activeTab === 'm15') filtered = trades.filter(t => t.model && t.model.toLowerCase().includes('m15'));
    if (activeTab === 'm5') filtered = trades.filter(t => t.model && t.model.toLowerCase().includes('m5'));

    countEl.innerText = filtered.length;

    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>Belum ada trade tercatat.</p></div>';
        return;
    }

    let html = '';
    filtered.forEach(t => {
        const isWin = t.profit > 0;
        const isBep = t.profit === 0;
        const dotClass = isWin ? 'win' : (isBep ? 'bep' : 'loss');
        const pnlClass = isWin ? 'positive' : (isBep ? '' : 'negative');
        const timeStr = t.time_out ? t.time_out.replace('2026-', '').substring(0, 11) : '—';
        const modelShort = (t.model || '').replace('LightGBM ', '').substring(0, 12);

        html += `
        <div class="trade-card">
            <div class="trade-left">
                <span class="trade-type-dot ${dotClass}"></span>
                <div>
                    <div class="trade-info-primary">${t.type || '—'} ${t.status || ''}</div>
                    <div class="trade-info-secondary">${modelShort}</div>
                </div>
            </div>
            <div class="trade-right">
                <div class="trade-pnl ${pnlClass}">${t.profit >= 0 ? '+' : ''}$${t.profit.toFixed(2)}</div>
                <div class="trade-time">${timeStr}</div>
            </div>
        </div>`;
    });

    container.innerHTML = html;
}
