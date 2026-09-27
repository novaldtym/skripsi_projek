/**
 * QuantLGB — AI Trading Bot Dashboard Logic (v4.3)
 * Pure Poppins Typography, Stepped Area Equity Curve with Custom Glass Tooltip,
 * Smooth Theme Switcher, Giant ON/OFF Slide Toggles, SVG Donut Gauges,
 * Web Audio API Sound Synthesizer (TP Ceria, SL Sad, Radar Open),
 * Slide-Down Notification Panel, and 16-Column Forward Testing Trade Recap.
 */

// ======== GLOBAL STATE ========
let currentTab = 'dashboard';
let chartInstance = null;
let chartActiveSeries = 'all'; // 'all', 'gain', 'drawdown'
let currentCurveDateFilter = '1 Sept – 30 Sept';
let currentCurveIntervalFilter = 'Daily';
let portfolioDataCache = null;
let summaryDataCache = null;
let diagnosticsDataCache = [];
let allTradesJournal = [];
let filteredJournal = [];
let m15DecisionLogs = [];
let m5DecisionLogs = [];
let m15FilterAction = 'ALL';
let recapFilters = {
    search: '',
    status: 'ALL',
    model: 'ALL',
    type: 'ALL'
};

let m15SessionStartTime = Date.now();
let m5SessionStartTime = Date.now();
let isM15Active = false;
let isM5Active = false;

// Audio & Notifications State
let audioCtx = null;
let isAudioMuted = false;
let knownNotificationIds = new Set();
let isInitialNotificationFetch = true;
let customTradeState = {
    m15: false,
    m5: false
};

// ======== INITIALIZATION ========
document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Theme from localStorage
    initTheme();

    // 2. Initial Data Load
    fetchLiveData();
    fetchPortfolioJourney();
    fetchDiagnosticsData();
    fetchNotifications();

    // 3. Setup Recurring Polling
    setInterval(fetchLiveData, 2500);
    setInterval(fetchPortfolioJourney, 10000);
    setInterval(updateClocksAndTimers, 1000);

    // 4. Global Click Listener to close open dropdowns & notification panel
    window.addEventListener('click', (e) => {
        if (!e.target.closest('.relative') && !e.target.closest('#notification-bell-btn') && !e.target.closest('#notification-dropdown-panel')) {
            closeAllDropdowns();
            closeNotificationPanel();
        }
    });

    // 5. Handle initial hash if any
    const hash = window.location.hash.replace('#', '');
    if (['dashboard', 'm15', 'm5', 'rekap', 'eval', 'about'].includes(hash)) {
        switchTab(hash);
    }
});

// ======== 1. THEME SWITCHING (LIGHT / DARK) ========
function initTheme() {
    const saved = localStorage.getItem('quantlgb_theme');
    if (saved === 'dark') {
        document.body.classList.remove('light-mode');
        document.body.classList.add('dark-mode');
        const sun = document.getElementById('theme-icon-sun');
        const moon = document.getElementById('theme-icon-moon');
        if (sun) sun.classList.add('hidden');
        if (moon) moon.classList.remove('hidden');
    } else {
        document.body.classList.remove('dark-mode');
        document.body.classList.add('light-mode');
        const sun = document.getElementById('theme-icon-sun');
        const moon = document.getElementById('theme-icon-moon');
        if (sun) sun.classList.remove('hidden');
        if (moon) moon.classList.add('hidden');
    }
}

function toggleTheme() {
    const isDark = document.body.classList.contains('dark-mode');
    const sun = document.getElementById('theme-icon-sun');
    const moon = document.getElementById('theme-icon-moon');
    if (isDark) {
        document.body.classList.remove('dark-mode');
        document.body.classList.add('light-mode');
        if (sun) sun.classList.remove('hidden');
        if (moon) moon.classList.add('hidden');
        localStorage.setItem('quantlgb_theme', 'light');
    } else {
        document.body.classList.remove('light-mode');
        document.body.classList.add('dark-mode');
        if (sun) sun.classList.add('hidden');
        if (moon) moon.classList.remove('hidden');
        localStorage.setItem('quantlgb_theme', 'dark');
    }

    // Re-render chart if currently on dashboard to update colors
    if (currentTab === 'dashboard') {
        renderEquityCurveChart();
    }
}

// ======== 2. TAB NAVIGATION ========
function switchTab(tabId) {
    currentTab = tabId;
    window.location.hash = tabId;

    // Hide all views
    document.querySelectorAll('.tab-view').forEach(view => {
        view.classList.add('hidden');
        view.classList.remove('block');
    });

    // Show target view
    const target = document.getElementById(`view-${tabId}`);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('block');
    }

    // Update active nav-link-item in sidebar
    document.querySelectorAll('.nav-link-item').forEach(link => {
        if (link.getAttribute('data-tab') === tabId) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // Scroll main viewport to top
    const scrollArea = document.getElementById('main-scroll-area');
    if (scrollArea) scrollArea.scrollTop = 0;

    // Trigger chart render when dashboard opens
    if (tabId === 'dashboard') {
        setTimeout(renderEquityCurveChart, 50);
    }
}

// ======== 3. DROPDOWN UTILITIES & CURVE FILTERS ========
function toggleDropdown(id) {
    const target = document.getElementById(id);
    if (!target) return;
    const isShown = target.classList.contains('show');
    closeAllDropdowns();
    if (!isShown) {
        target.classList.add('show');
    }
}

function closeAllDropdowns() {
    document.querySelectorAll('.dropdown-menu-floating').forEach(d => {
        d.classList.remove('show');
    });
}

function applyDateFilter(label) {
    currentCurveDateFilter = label;
    const el = document.getElementById('label-date-filter');
    if (el) el.innerText = label;
    closeAllDropdowns();
    renderEquityCurveChart();
    showNotification(`Filter Tanggal Portofolio: ${label}`, 'info');
}

function applyIntervalFilter(label) {
    currentCurveIntervalFilter = label;
    const el = document.getElementById('label-interval-filter');
    if (el) el.innerText = label;
    closeAllDropdowns();
    renderEquityCurveChart();
    showNotification(`Granularitas Interval: ${label}`, 'info');
}

// ======== 4. LIVE TELEMETRY & STATUS POLLING ========
async function fetchLiveData() {
    try {
        const [sumRes, stRes] = await Promise.all([
            fetch('/api/summary'),
            fetch('/api/status')
        ]);

        if (sumRes.ok) {
            const summary = await sumRes.json();
            summaryDataCache = summary;
            updateDashboardMetrics(summary);
            updateBotTelemetry('m15', summary.telemetry_m15);
            updateBotTelemetry('m5', summary.telemetry_m5);

            // Injeksi Kesimpulan Makroekonomi Dinamis
            const elMacro = document.getElementById('m15-macro-text');
            if (elMacro && summary.macro_conclusion) {
                elMacro.innerText = summary.macro_conclusion;
            }
        }

        if (stRes.ok) {
            const status = await stRes.json();
            updateBotStatusUI(status);
        }

        // Auto sync notifikasi live
        fetchNotifications();
    } catch (err) {
        console.warn('[QuantLGB Sync]:', err);
    }
}

function updateDashboardMetrics(s) {
    if (!s) return;

    // 1. Balance & Growth
    const elBal = document.getElementById('dash-balance');
    const elGrowth = document.getElementById('dash-growth');
    const curBal = s.current_balance !== undefined ? s.current_balance : 500.00;
    const initialBal = s.starting_balance || 500.00;
    const growthPct = ((curBal - initialBal) / initialBal) * 100.0;

    if (elBal) elBal.innerText = `$${curBal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    if (elGrowth) {
        elGrowth.innerText = `${growthPct >= 0 ? '▲' : '▼'} ${Math.abs(growthPct).toFixed(1)}%`;
        elGrowth.className = `badge-pill ${growthPct >= 0 ? 'bg-white/25 text-white' : 'bg-red-900/60 text-white'} text-xs font-bold`;
    }

    // 2. Progress Trade
    const elProgText = document.getElementById('dash-progress-text');
    const elProgBar = document.getElementById('dash-progress-bar');
    const trades = s.total_trades || (s.skripsi_trades || 0);
    if (elProgText) elProgText.innerText = `${trades} of 100`;
    if (elProgBar) elProgBar.style.width = `${Math.min(100, trades)}%`;

    // 3. Total PnL & Profit Factor
    const elPnl = document.getElementById('dash-total-pnl');
    const pnl = s.net_profit !== undefined ? s.net_profit : (curBal - initialBal);
    if (elPnl) {
        elPnl.innerText = `${pnl >= 0 ? '+$' : '-$'}${Math.abs(pnl).toFixed(2)}`;
        elPnl.className = `text-4xl md:text-5xl font-bold tracking-tight ${pnl >= 0 ? 'text-[#007a4d]' : 'text-[#b91c1c]'}`;
    }

    // 4. Win Rate & Trades Count
    const elWr = document.getElementById('dash-win-rate');
    const elWinCount = document.getElementById('dash-win-count');
    const elLossCount = document.getElementById('dash-loss-count');
    const elTotalTrades = document.getElementById('dash-total-trades');
    const wr = s.win_rate !== undefined ? s.win_rate : 72.7;
    const wins = s.win_trades !== undefined ? s.win_trades : 16;
    const losses = s.loss_trades !== undefined ? s.loss_trades : 6;

    if (elWr) elWr.innerText = `${wr.toFixed(0)}%`;
    if (elWinCount) elWinCount.innerText = `${wins}W`;
    if (elLossCount) elLossCount.innerText = `${losses}L`;
    if (elTotalTrades) elTotalTrades.innerText = `${trades} Trades`;

    // 5. XAUUSD Live Ticker
    const elBid = document.getElementById('dash-bid');
    const elAsk = document.getElementById('dash-ask');
    const elSpread = document.getElementById('dash-spread');
    if (elBid && s.bid) elBid.innerText = `$${s.bid.toFixed(2)}`;
    if (elAsk && s.ask) elAsk.innerText = `$${s.ask.toFixed(2)}`;
    if (elSpread && s.spread !== undefined) elSpread.innerText = `${s.spread} pips`;

    // 6. MT5 Status Indicator in Sidebar & Header
    const mt5Ind = document.getElementById('mt5-status-indicator');
    const mt5Txt = document.getElementById('mt5-status-text');
    const isConnected = s.mt5_connected || (s.current_balance > 0) || (s.bid > 0);
    if (mt5Ind) {
        mt5Ind.className = `pulse-dot ${isConnected ? 'pulse-dot-green' : 'pulse-dot-red'}`;
    }
    if (mt5Txt) {
        mt5Txt.innerText = isConnected ? 'MT5 LIVE' : 'MT5 OFFLINE';
    }
}

function updateBotStatusUI(st) {
    if (!st) return;

    // M15 Bot Status
    const m15Running = (st.m15 && st.m15.running) || (st.bots && st.bots.m15_running);
    isM15Active = !!m15Running;
    const m15Toggle = document.getElementById('m15-bot-toggle');
    const m15PodStatus = document.getElementById('dash-m15-pod-status');
    const m15HeroDot = document.getElementById('m15-hero-dot');
    const m15HeroSub = document.getElementById('m15-hero-status-sub');

    if (m15Toggle) {
        if (m15Running) {
            m15Toggle.className = 'bot-toggle-wrapper on';
            m15Toggle.innerHTML = '<div class="toggle-knob">ON</div><span class="toggle-label-text toggle-label-off">Off</span>';
        } else {
            m15Toggle.className = 'bot-toggle-wrapper off';
            m15Toggle.innerHTML = '<div class="toggle-knob">Off</div><span class="toggle-label-text toggle-label-on">ON</span>';
        }
    }
    if (m15PodStatus) {
        m15PodStatus.innerText = m15Running ? 'ACTIVE' : 'NON - ACTIVE';
        m15PodStatus.className = `text-[11px] font-semibold ${m15Running ? 'text-[var(--accent-green)]' : 'text-[var(--text-muted)]'}`;
    }
    if (m15HeroDot) m15HeroDot.className = `pulse-dot ${m15Running ? 'pulse-dot-green' : 'pulse-dot-red'}`;
    if (m15HeroSub) m15HeroSub.innerText = m15Running ? '(Actived)' : '(Non-Actived)';

    // M5 Bot Status
    const m5Running = (st.m5 && st.m5.running) || (st.bots && st.bots.m5_running);
    isM5Active = !!m5Running;
    const m5Toggle = document.getElementById('m5-bot-toggle');
    const m5PodStatus = document.getElementById('dash-m5-pod-status');
    const m5PodCircle = document.getElementById('dash-m5-pod-circle');
    const m5HeroDot = document.getElementById('m5-hero-dot');
    const m5HeroSub = document.getElementById('m5-hero-status-sub');

    if (m5Toggle) {
        if (m5Running) {
            m5Toggle.className = 'bot-toggle-wrapper on';
            m5Toggle.innerHTML = '<div class="toggle-knob">ON</div><span class="toggle-label-text toggle-label-off">Off</span>';
        } else {
            m5Toggle.className = 'bot-toggle-wrapper off';
            m5Toggle.innerHTML = '<div class="toggle-knob">Off</div><span class="toggle-label-text toggle-label-on">ON</span>';
        }
    }
    if (m5PodStatus) {
        m5PodStatus.innerText = m5Running ? 'ACTIVE' : 'NON - ACTIVE';
        m5PodStatus.className = `text-[11px] font-semibold ${m5Running ? 'text-[var(--accent-green)]' : 'text-[var(--text-muted)]'}`;
    }
    if (m5PodCircle) {
        m5PodCircle.className = `w-10 h-10 rounded-full ${m5Running ? 'bg-[var(--accent-green)]' : 'bg-gray-400'} text-white flex items-center justify-center font-bold text-sm`;
    }
    if (m5HeroDot) m5HeroDot.className = `pulse-dot ${m5Running ? 'pulse-dot-green' : 'pulse-dot-red'}`;
    if (m5HeroSub) m5HeroSub.innerText = m5Running ? '(Actived)' : '(Non-Actived)';

    // Render Bot Decision History Tables
    if (st.m15 && st.m15.decision_history) {
        m15DecisionLogs = st.m15.decision_history;
        renderDecisionTable('m15', m15DecisionLogs);
    }
    if (st.m5 && st.m5.decision_history) {
        m5DecisionLogs = st.m5.decision_history;
        renderDecisionTable('m5', m5DecisionLogs);
    }
}

function updateBotTelemetry(botKey, t) {
    if (!t) return;
    const pb = Number(t.prob_buy || 50.0);
    const ps = Number(t.prob_sell || 50.0);
    const dominantPct = pb >= ps ? pb : ps;

    let biasLabel = "Netral";
    if (pb >= 70.0) biasLabel = "Sniper Buy";
    else if (ps >= 70.0) biasLabel = "Sniper Sell";
    else if (pb > ps) biasLabel = "Buy Bias";
    else if (ps > pb) biasLabel = "Sell Bias";

    // Update Percentage & Bias Labels
    const elGaugePct = document.getElementById(`${botKey}-gauge-pct`);
    const elGaugeBias = document.getElementById(`${botKey}-gauge-bias`);
    const elBuyPct = document.getElementById(`${botKey}-buy-pct`);
    const elSellPct = document.getElementById(`${botKey}-sell-pct`);
    const elBuyBar = document.getElementById(`${botKey}-buy-bar`);
    const elSellBar = document.getElementById(`${botKey}-sell-bar`);

    if (elGaugePct) elGaugePct.innerText = `${dominantPct.toFixed(0)}%`;
    if (elGaugeBias) {
        elGaugeBias.innerText = biasLabel;
        elGaugeBias.className = `text-sm font-semibold ${pb >= 70 || pb > ps ? 'text-[#007a4d]' : (ps >= 70 || ps > pb ? 'text-[#b91c1c]' : 'text-[var(--text-muted)]')}`;
    }

    if (elBuyPct) elBuyPct.innerText = `${pb.toFixed(0)}%`;
    if (elSellPct) elSellPct.innerText = `${ps.toFixed(0)}%`;
    if (elBuyBar) elBuyBar.style.width = `${pb}%`;
    if (elSellBar) elSellBar.style.width = `${ps}%`;

    // SVG Donut Circle Slide Animation (Circumference = 301.59)
    const elDonutBuy = document.getElementById(`${botKey}-donut-buy`);
    if (elDonutBuy) {
        const circumference = 301.59;
        const offset = circumference - (circumference * (pb / 100.0));
        elDonutBuy.style.strokeDashoffset = offset;
    }

    // Candle countdown if provided
    if (t.mins_left !== undefined && t.secs_left !== undefined) {
        const cd = `${String(t.mins_left).padStart(2, '0')}m ${String(t.secs_left).padStart(2, '0')}s`;
        const elCd = document.getElementById(`${botKey}-candle-countdown`);
        if (elCd) elCd.innerText = cd;
    }
}

// ======== 5. DECISION LOGS TABLE RENDERING ========
function renderDecisionTable(botKey, logs) {
    const tbody = document.getElementById(`${botKey}-decision-log-tbody`);
    if (!tbody || !logs) return;

    let filtered = logs;
    if (botKey === 'm15' && m15FilterAction !== 'ALL') {
        filtered = logs.filter(l => (l.action || '').toUpperCase() === m15FilterAction);
    }

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-[var(--text-muted)]">Tidak ada log keputusan yang cocok.</td></tr>`;
        return;
    }

    let html = '';
    filtered.slice(0, 15).forEach(l => {
        const act = (l.action || 'STANDBY').toUpperCase();
        let badgeClass = 'badge-standby';
        if (act === 'BUY') badgeClass = 'badge-win';
        else if (act === 'SELL') badgeClass = 'badge-loss';

        html += `
            <tr>
                <td class="font-medium">${l.time || '—'}</td>
                <td><span class="badge-pill ${badgeClass}">${act}</span></td>
                <td class="font-semibold text-[#007a4d]">${l.buy_pct !== undefined ? l.buy_pct.toFixed(0) + '%' : '50%'}</td>
                <td class="font-semibold text-[#b91c1c]">${l.sell_pct !== undefined ? l.sell_pct.toFixed(0) + '%' : '50%'}</td>
                <td class="text-xs text-[var(--text-secondary)] truncate max-w-xs">${l.detail || 'Evaluasi regular candle'}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;

    // Update Last Decision Text
    if (filtered.length > 0) {
        const last = filtered[0];
        const lastDecEl = document.getElementById(`${botKey}-last-decision-text`);
        if (lastDecEl && last.action) lastDecEl.innerText = last.action;
    }
}

function filterBotDecisionLogs(botKey, action) {
    if (botKey === 'm15') {
        m15FilterAction = action;
        const btnLabel = document.getElementById('m15-filter-btn-label');
        if (btnLabel) {
            btnLabel.innerText = action === 'ALL' ? 'Semua Aksi' : `${action} Saja`;
        }
        renderDecisionTable('m15', m15DecisionLogs);
    }
    closeAllDropdowns();
}

async function clearDecisionLogsUI(botKey) {
    const tbody = document.getElementById(`${botKey}-decision-log-tbody`);
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-[var(--text-muted)]">Riwayat keputusan telah dibersihkan.</td></tr>`;
    }
    if (botKey === 'm15') m15DecisionLogs = [];
    if (botKey === 'm5') m5DecisionLogs = [];
    try {
        await fetch(`/api/control/${botKey}/clean_logs`, { method: 'POST' });
    } catch(e) {}
    showNotification(`Log keputusan ${botKey.toUpperCase()} berhasil dibersihkan`, 'info');
}

// ======== 6. BOT EXECUTION CONTROLS (ON / OFF SLIDE) ========
async function toggleBotExecution(botKey) {
    const isRunning = botKey === 'm15' ? isM15Active : isM5Active;
    const targetAction = isRunning ? 'stop' : 'start';
    const actionLabel = targetAction === 'start' ? 'menyalakan' : 'mematikan';

    showNotification(`Sedang ${actionLabel} Bot ${botKey.toUpperCase()}...`, 'info');

    // Optimistic UI update
    const toggleEl = document.getElementById(`${botKey}-bot-toggle`);
    if (toggleEl) {
        if (targetAction === 'start') {
            toggleEl.className = 'bot-toggle-wrapper on';
            toggleEl.innerHTML = '<div class="toggle-knob">ON</div><span class="toggle-label-text toggle-label-off">Off</span>';
            if (botKey === 'm15') isM15Active = true;
            else isM5Active = true;
        } else {
            toggleEl.className = 'bot-toggle-wrapper off';
            toggleEl.innerHTML = '<div class="toggle-knob">Off</div><span class="toggle-label-text toggle-label-on">ON</span>';
            if (botKey === 'm15') isM15Active = false;
            else isM5Active = false;
        }
    }

    try {
        const res = await fetch(`/api/control/${botKey}/${targetAction}`, { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.status === 'ok') {
            showNotification(`Bot ${botKey.toUpperCase()} berhasil di-${targetAction}!`, 'success');
            setTimeout(fetchLiveData, 600);
        } else {
            showNotification(`Gagal: ${data.error || 'Aksi ditolak'}`, 'error');
            setTimeout(fetchLiveData, 1000);
        }
    } catch (err) {
        showNotification(`Koneksi server gagal: ${err.message}`, 'error');
    }
}

// ======== 7. STEPPED AREA EQUITY CURVE (CHART.JS) ========
async function fetchPortfolioJourney() {
    try {
        const res = await fetch('/api/portfolio/journey');
        if (!res.ok) return;
        const data = await res.json();
        portfolioDataCache = data;

        // Populate Journal for Recap Table
        if (data.journal && Array.isArray(data.journal)) {
            allTradesJournal = data.journal;
            filteredJournal = [...allTradesJournal];
            renderRecapTable();
        }

        // Render Periods Performance Table in Dashboard
        if (data.periods) {
            updatePeriodsTable(data.periods);
        }

        // Update Profit Factor Badge in Dashboard
        if (data.summary && data.summary.profit_factor !== undefined) {
            const elPf = document.getElementById('dash-profit-factor');
            if (elPf) elPf.innerText = data.summary.profit_factor.toFixed(1);
        }

        // Render Stepped Area Chart
        renderEquityCurveChart();
    } catch (err) {
        console.error('[Portfolio Journey Error]:', err);
    }
}

function updatePeriodsTable(p) {
    if (!p) return;
    const setRow = (period, prefix) => {
        const d = p[period] || {};
        const elGain = document.getElementById(`perf-${prefix}-gain`);
        const elTrade = document.getElementById(`perf-${prefix}-trade`);
        if (elGain) {
            const gain = d.gain || '+0.00%';
            elGain.innerText = gain;
            elGain.className = `py-1.5 text-center font-bold ${gain.startsWith('-') ? 'text-red-500' : 'text-[#007a4d]'}`;
        }
        if (elTrade) {
            elTrade.innerText = `${d.trades || 0} Trade`;
        }
    };
    setRow('today', 'day');
    setRow('this_week', 'week');
    setRow('this_month', 'month');
    setRow('all_time', 'all');
}

function toggleChartSeries(series) {
    if (chartActiveSeries === series) {
        chartActiveSeries = 'all';
    } else {
        chartActiveSeries = series;
    }

    const btnGain = document.getElementById('btn-toggle-gain');
    const btnDd = document.getElementById('btn-toggle-dd');

    if (btnGain) {
        btnGain.className = `badge-pill ${chartActiveSeries === 'gain' ? 'bg-[#005a38] ring-2 ring-white/50' : 'bg-[#007a4d]'} text-white px-3 py-1.5 cursor-pointer shadow-sm`;
    }
    if (btnDd) {
        btnDd.className = `badge-pill ${chartActiveSeries === 'drawdown' ? 'bg-[#5c1313] ring-2 ring-white/50' : 'bg-[#7f1d1d]'} text-white px-3 py-1.5 cursor-pointer shadow-sm`;
    }

    renderEquityCurveChart();
}

function filterCurveData(rawCurve) {
    if (!rawCurve || rawCurve.length === 0) return [];
    let filtered = [...rawCurve];

    if (currentCurveDateFilter === 'Hari Ini') {
        filtered = filtered.slice(-3);
    } else if (currentCurveDateFilter === 'Minggu Ini') {
        filtered = filtered.slice(-8);
    } else if (currentCurveDateFilter === 'Bulan Ini' || currentCurveDateFilter === '1 Sept – 30 Sept') {
        filtered = [...rawCurve];
    } else if (currentCurveDateFilter === 'Sepanjang Waktu') {
        filtered = [...rawCurve];
    }

    if (currentCurveIntervalFilter === 'Per Jam') {
        filtered = filtered.map((c, i) => ({
            ...c,
            displayLabel: i === 0 ? '08:00' : `${String(9 + (i % 12)).padStart(2, '0')}:00`
        }));
    } else if (currentCurveIntervalFilter === 'Mingguan') {
        const step = Math.max(1, Math.floor(filtered.length / 4));
        filtered = filtered.filter((_, i) => i === 0 || i % step === 0 || i === filtered.length - 1);
        filtered = filtered.map((c, i) => ({
            ...c,
            displayLabel: `Minggu ${i + 1}`
        }));
    } else if (currentCurveIntervalFilter === 'Bulanan') {
        filtered = [
            filtered[0],
            filtered[Math.floor(filtered.length / 2)],
            filtered[filtered.length - 1]
        ].filter(Boolean);
        filtered = filtered.map((c, i) => ({
            ...c,
            displayLabel: i === 0 ? 'Awal Sept' : (i === 1 ? 'Mid Sept' : 'Akhir Sept')
        }));
    } else {
        // Daily
        filtered = filtered.map(c => ({
            ...c,
            displayLabel: c.label || (c.index === 0 ? 'Mulai' : `T#${c.index}`)
        }));
    }

    return filtered;
}

function renderEquityCurveChart() {
    if (!portfolioDataCache) return;
    const canvas = document.getElementById('equityChartCanvas');
    if (!canvas) return;

    const rawCurve = portfolioDataCache.curve || [];
    if (rawCurve.length === 0) return;

    // Terapkan filter tanggal dan interval aktif
    const curve = filterCurveData(rawCurve);
    if (curve.length === 0) return;

    const isDark = document.body.classList.contains('dark-mode');

    // Labels & Datasets
    const labels = curve.map(c => c.displayLabel || (c.index === 0 ? 'Mulai' : `T#${c.index}`));
    const balanceData = curve.map(c => c.balance);
    const gainData = curve.map(c => c.growth_pct);
    const ddData = curve.map(c => -Math.abs(c.drawdown_pct));

    let activeData = balanceData;
    let borderColor = isDark ? '#10b981' : '#007a4d';
    let gradientStart = isDark ? 'rgba(16, 185, 129, 0.25)' : 'rgba(0, 122, 77, 0.18)';
    let gradientEnd = isDark ? 'rgba(16, 185, 129, 0.0)' : 'rgba(0, 122, 77, 0.0)';

    if (chartActiveSeries === 'gain') {
        activeData = gainData;
        borderColor = '#007a4d';
        gradientStart = 'rgba(0, 122, 77, 0.25)';
    } else if (chartActiveSeries === 'drawdown') {
        activeData = ddData;
        borderColor = '#dc2626';
        gradientStart = 'rgba(220, 38, 38, 0.25)';
        gradientEnd = 'rgba(220, 38, 38, 0.0)';
    }

    if (chartInstance) {
        chartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, gradientStart);
    gradient.addColorStop(1, gradientEnd);

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Equity Curve',
                data: activeData,
                stepped: true, // FIGMA SPEC: STEPPED AREA CURVE
                borderColor: borderColor,
                borderWidth: 2.5,
                fill: true,
                backgroundColor: gradient,
                pointBackgroundColor: curve.map((c, idx) => {
                    if (idx === 0) return '#3b82f6';
                    return c.pnl >= 0 ? '#007a4d' : '#dc2626';
                }),
                pointBorderColor: isDark ? '#1f2937' : '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 0, // FIGMA SPEC: Clean grid tanpa titik bulat berantakan
                pointHoverRadius: 6, // Munculkan titik saat kursor dihover
                pointHoverBackgroundColor: borderColor,
                pointHoverBorderColor: '#ffffff',
                pointHoverBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: false, // Gunakan Custom Frosted Glass Tooltip
                    external: (context) => customGlassTooltipHandler(context, curve)
                }
            },
            scales: {
                x: {
                    grid: {
                        color: isDark ? 'rgba(255, 255, 255, 0.07)' : 'rgba(0, 0, 0, 0.06)',
                        borderDash: [4, 4]
                    },
                    ticks: {
                        color: isDark ? '#9ca3af' : '#6b7280',
                        font: { family: 'Poppins', size: 10 }
                    }
                },
                y: {
                    grid: {
                        color: isDark ? 'rgba(255, 255, 255, 0.07)' : 'rgba(0, 0, 0, 0.06)',
                        borderDash: [4, 4]
                    },
                    ticks: {
                        color: isDark ? '#9ca3af' : '#6b7280',
                        font: { family: 'Poppins', size: 11 },
                        callback: function(val) {
                            if (chartActiveSeries === 'gain' || chartActiveSeries === 'drawdown') {
                                return val + '%';
                            }
                            return '$' + Number(val).toFixed(0);
                        }
                    }
                }
            }
        }
    });
}

function customGlassTooltipHandler(context, curveData) {
    const tooltipEl = document.getElementById('custom-glass-tooltip');
    if (!tooltipEl) return;

    const { chart, tooltip } = context;
    if (tooltip.opacity === 0) {
        tooltipEl.style.opacity = '0';
        tooltipEl.style.pointerEvents = 'none';
        return;
    }

    if (tooltip.body) {
        const idx = tooltip.dataPoints[0].dataIndex;
        const pt = curveData[idx];
        if (!pt) return;

        const tradeEl = document.getElementById('tooltip-trade');
        const balEl = document.getElementById('tooltip-balance');
        const pnlEl = document.getElementById('tooltip-pnl');
        const pctEl = document.getElementById('tooltip-pct');

        if (tradeEl) tradeEl.innerText = pt.index === 0 ? 'Start Deposit' : `Trade #${pt.index}`;
        if (balEl) balEl.innerText = `Balance: $${pt.balance.toFixed(2)}`;
        if (pnlEl) {
            const isPos = pt.pnl >= 0;
            pnlEl.innerText = `PnL: ${isPos ? '+' : ''}$${pt.pnl.toFixed(2)}`;
            pnlEl.className = `font-semibold ${isPos ? 'text-[#007a4d]' : 'text-red-500'}`;
        }
        if (pctEl) {
            const growth = pt.growth_pct;
            const isUp = growth >= 0;
            pctEl.innerText = `${isUp ? '▲' : '▼'} ${Math.abs(growth).toFixed(1)}%`;
            pctEl.className = `badge-pill ${isUp ? 'badge-win' : 'badge-loss'} text-[11px]`;
        }
    }

    const { offsetLeft: positionX, offsetTop: positionY } = chart.canvas;
    tooltipEl.style.opacity = '1';
    tooltipEl.style.left = (positionX + tooltip.caretX) + 'px';
    tooltipEl.style.top = (positionY + tooltip.caretY - 55) + 'px';
    tooltipEl.style.transform = 'translate(-50%, 0)';
}

// ======== 8. 16-COLUMN RECAP TRANSAKSI TABLE ========
function renderRecapTable() {
    const tbody = document.getElementById('rekap-trades-tbody');
    if (!tbody) return;

    if (!filteredJournal || filteredJournal.length === 0) {
        tbody.innerHTML = `<tr><td colspan="16" class="text-center py-6 text-[var(--text-muted)] font-medium">Tidak ada transaksi yang cocok dengan kriteria pencarian / filter.</td></tr>`;
        return;
    }

    let html = '';
    filteredJournal.forEach(j => {
        const isWin = j.result === 'WIN';
        const isLoss = j.result === 'LOSS';
        const pnl = j.profit || 0.0;
        const pnlClass = isWin ? 'text-[#007a4d] font-bold' : (isLoss ? 'text-[#b91c1c] font-bold' : 'text-[var(--text-secondary)] font-bold');
        const resultBadge = isWin ? 'badge-win' : (isLoss ? 'badge-loss' : 'badge-standby');
        const typeBadge = j.type === 'BUY' ? 'badge-win' : 'badge-loss';

        html += `
            <tr class="hover:bg-[var(--table-row-hover)] transition-colors">
                <td class="font-semibold text-center">#${j.index}</td>
                <td class="font-medium text-[var(--text-primary)]">#${j.ticket}</td>
                <td class="whitespace-nowrap text-[var(--text-secondary)]">${j.time_open || '—'}</td>
                <td class="whitespace-nowrap text-[var(--text-secondary)]">${j.time_close || '—'}</td>
                <td class="text-[var(--text-secondary)]">${j.duration || '—'}</td>
                <td><span class="badge-pill ${typeBadge}">${j.type}</span></td>
                <td class="text-center font-medium">${Number(j.lot || 0.01).toFixed(2)}</td>
                <td class="text-[var(--text-primary)] font-medium">$${Number(j.open_price || 0).toFixed(2)}</td>
                <td class="text-[var(--text-secondary)]">$${Number(j.sl || 0).toFixed(2)}</td>
                <td class="text-[var(--text-secondary)]">$${Number(j.tp || 0).toFixed(2)}</td>
                <td class="text-[var(--text-primary)] font-medium">$${Number(j.close_price || 0).toFixed(2)}</td>
                <td class="font-semibold ${j.pips >= 0 ? 'text-[#007a4d]' : 'text-[#b91c1c]'}">${j.pips >= 0 ? '+' : ''}${Number(j.pips || 0).toFixed(1)}</td>
                <td class="${pnlClass}">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</td>
                <td class="font-bold text-[var(--text-primary)]">$${Number(j.balance || 500).toFixed(2)}</td>
                <td><span class="badge-pill ${resultBadge}">${j.result}</span></td>
                <td class="text-xs text-[var(--text-secondary)] truncate max-w-xs" title="${j.alasan || j.scenario || '—'}">${j.alasan || j.scenario || '—'}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function filterRecapTable() {
    const input = document.getElementById('rekap-search-input');
    recapFilters.search = input ? input.value.trim().toLowerCase() : '';

    filteredJournal = allTradesJournal.filter(j => {
        // Status filter
        if (recapFilters.status !== 'ALL' && j.result !== recapFilters.status) {
            return false;
        }

        // Model filter
        if (recapFilters.model === 'M15' && !(j.model || '').includes('M15')) {
            return false;
        }
        if (recapFilters.model === 'M5' && !(j.model || '').includes('M5')) {
            return false;
        }

        // Type filter (BUY / SELL)
        if (recapFilters.type !== 'ALL' && j.type !== recapFilters.type) {
            return false;
        }

        // Search text filter
        if (recapFilters.search) {
            const query = recapFilters.search;
            const fullStr = `${j.index} ${j.ticket} ${j.type} ${j.result} ${j.time_open} ${j.time_close} ${j.scenario} ${j.alasan}`.toLowerCase();
            if (!fullStr.includes(query)) return false;
        }

        return true;
    });

    renderRecapTable();
}

function applyRecapFilter(filterType, value) {
    if (filterType === 'status') {
        recapFilters.status = value;
        const el = document.getElementById('label-filter-status');
        if (el) el.innerText = value === 'ALL' ? 'Semua Status' : `${value} Saja`;
    } else if (filterType === 'model') {
        recapFilters.model = value;
        const el = document.getElementById('label-filter-model');
        if (el) el.innerText = value === 'ALL' ? 'Semua Bot' : (value === 'M15' ? 'M15 Bot (Skripsi)' : 'M5 Bot (Scalper)');
    } else if (filterType === 'type') {
        recapFilters.type = value;
        const el = document.getElementById('label-filter-type');
        if (el) el.innerText = value === 'ALL' ? 'Semua Arah' : `${value} Saja`;
    }

    closeAllDropdowns();
    filterRecapTable();
}

function exportData(format) {
    closeAllDropdowns();
    if (format === 'csv') {
        window.location.href = '/api/export/csv';
    }
}

// ======== 9. EVALUASI W/L & TRADE AUTOPSY ========
async function fetchDiagnosticsData() {
    try {
        const res = await fetch('/api/diagnostics');
        if (!res.ok) return;
        const data = await res.json();
        const trades = Array.isArray(data) ? data : (data.trades || []);
        diagnosticsDataCache = trades;
        renderDiagnosticsTable(trades);
    } catch (err) {
        console.error('[Diagnostics Error]:', err);
    }
}

function renderDiagnosticsTable(trades) {
    const tbody = document.getElementById('eval-diagnostics-tbody');
    if (!tbody) return;

    if (!trades || trades.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-[var(--text-muted)]">Belum ada data diagnosa transaksi.</td></tr>`;
        return;
    }

    let html = '';
    trades.forEach(t => {
        const isWin = t.result === 'WIN';
        const isLoss = t.result === 'LOSS';
        const pnl = t.profit !== undefined ? t.profit : 0;
        const pnlClass = isWin ? 'text-[#007a4d] font-bold' : (isLoss ? 'text-[#b91c1c] font-bold' : 'text-[var(--text-secondary)]');
        const resBadge = isWin ? 'badge-win' : (isLoss ? 'badge-loss' : 'badge-standby');
        const typeBadge = t.type === 'BUY' ? 'badge-win' : 'badge-loss';

        html += `
            <tr class="hover:bg-[var(--table-row-hover)] transition-colors">
                <td class="font-medium text-[var(--text-primary)]">#${t.ticket}</td>
                <td class="whitespace-nowrap text-[var(--text-secondary)]">${t.time_close || t.time_open || '—'}</td>
                <td><span class="badge-pill ${typeBadge}">${t.type}</span></td>
                <td class="text-xs font-semibold text-[var(--text-primary)]">${t.scenario || 'General Setup'}</td>
                <td class="text-xs text-[var(--text-secondary)]">$${t.entry_price ? t.entry_price.toFixed(2) : '—'}</td>
                <td class="${pnlClass}">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</td>
                <td><span class="badge-pill ${resBadge}">${t.result}</span></td>
                <td class="text-xs text-[var(--text-secondary)] max-w-sm leading-relaxed">${t.diagnostic_text || t.lesson_learned || 'Evaluasi regular model.'}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

// ======== 10. CLOCKS & TIMERS (HERO BANNERS) ========
function updateClocksAndTimers() {
    const now = new Date();

    // 1. Digital Clock (HH:mm:ss)
    const hours = String(now.getHours()).padStart(2, '0');
    const mins = String(now.getMinutes()).padStart(2, '0');
    const secs = String(now.getSeconds()).padStart(2, '0');
    const timeStr = `${hours}:${mins}:${secs}`;

    const m15Clock = document.getElementById('m15-live-clock');
    const m5Clock = document.getElementById('m5-live-clock');
    if (m15Clock) m15Clock.innerText = timeStr;
    if (m5Clock) m5Clock.innerText = timeStr;

    // 2. Candle Close Countdown
    // M15 Countdown
    const m15SecsPast = (now.getMinutes() % 15) * 60 + now.getSeconds();
    const m15SecsLeft = 900 - m15SecsPast;
    const m15RemMins = Math.floor(m15SecsLeft / 60);
    const m15RemSecs = m15SecsLeft % 60;
    const m15CdEl = document.getElementById('m15-candle-countdown');
    if (m15CdEl) {
        m15CdEl.innerText = `${String(m15RemMins).padStart(2, '0')}m ${String(m15RemSecs).padStart(2, '0')}s`;
    }

    // M5 Countdown
    const m5SecsPast = (now.getMinutes() % 5) * 60 + now.getSeconds();
    const m5SecsLeft = 300 - m5SecsPast;
    const m5RemMins = Math.floor(m5SecsLeft / 60);
    const m5RemSecs = m5SecsLeft % 60;
    const m5CdEl = document.getElementById('m5-candle-countdown');
    if (m5CdEl) {
        m5CdEl.innerText = `${String(m5RemMins).padStart(2, '0')}m ${String(m5RemSecs).padStart(2, '0')}s`;
    }

    // 3. Durasi Sesi Bot Stopwatch
    if (isM15Active) {
        const diff15 = Math.floor((Date.now() - m15SessionStartTime) / 1000);
        const h15 = String(Math.floor(diff15 / 3600)).padStart(2, '0');
        const m15 = String(Math.floor((diff15 % 3600) / 60)).padStart(2, '0');
        const s15 = String(diff15 % 60).padStart(2, '0');
        const dur15 = document.getElementById('m15-session-duration');
        if (dur15) dur15.innerText = `${h15}:${m15}:${s15}`;
    }

    if (isM5Active) {
        const diff5 = Math.floor((Date.now() - m5SessionStartTime) / 1000);
        const h5 = String(Math.floor(diff5 / 3600)).padStart(2, '0');
        const m5 = String(Math.floor((diff5 % 3600) / 60)).padStart(2, '0');
        const s5 = String(diff5 % 60).padStart(2, '0');
        const dur5 = document.getElementById('m5-session-duration');
        if (dur5) dur5.innerText = `${h5}:${m5}:${s5}`;
    }
}

// ======== 11. TOAST NOTIFICATION ========
function showNotification(msg, type = 'info') {
    const existing = document.querySelectorAll('.quantlgb-toast');
    existing.forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = 'quantlgb-toast';
    const borderColor = type === 'success' ? '#007a4d' : (type === 'error' ? '#b91c1c' : '#2563eb');
    toast.style.cssText = `
        position: fixed;
        bottom: 28px;
        right: 28px;
        background: var(--card-bg);
        color: var(--text-primary);
        border: 1px solid var(--card-border);
        border-left: 5px solid ${borderColor};
        padding: 12px 20px;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        z-index: 9999;
        font-family: 'Poppins', sans-serif;
        font-size: 13px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 12px;
        animation: fadeIn 0.25s ease-out;
    `;
    toast.innerText = msg;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}

// ======== 12. WEB AUDIO API SYNTHESIZER (CERIA TP, SAD SL, RADAR OPEN) ========
function getAudioContext() {
    if (!audioCtx) {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (AudioContextClass) {
            audioCtx = new AudioContextClass();
        }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    return audioCtx;
}

// 1. CHEERFUL TP SOUND (Major Arpeggio Chime: C5 -> E5 -> G5 -> C6 -> E6 Shimmer)
function playCheerfulTpSound() {
    if (isAudioMuted) return;
    try {
        const ctx = getAudioContext();
        if (!ctx) return;
        const now = ctx.currentTime;
        
        // C5 (523.25), E5 (659.25), G5 (783.99), C6 (1046.50), E6 (1318.51)
        const notes = [523.25, 659.25, 783.99, 1046.50, 1318.51];
        notes.forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            
            osc.type = idx === notes.length - 1 ? 'sine' : 'triangle';
            osc.frequency.setValueAtTime(freq, now + idx * 0.08);
            
            gain.gain.setValueAtTime(0.0001, now + idx * 0.08);
            gain.gain.linearRampToValueAtTime(0.25, now + idx * 0.08 + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.08 + 0.55);
            
            osc.connect(gain);
            gain.connect(ctx.destination);
            
            osc.start(now + idx * 0.08);
            osc.stop(now + idx * 0.08 + 0.6);
        });
    } catch (e) {
        console.warn('Audio play error:', e);
    }
}

// 2. SAD SL SOUND (Melancholy Descending Minor: F4 -> Eb4 -> Db4 -> C4)
function playSadSlSound() {
    if (isAudioMuted) return;
    try {
        const ctx = getAudioContext();
        if (!ctx) return;
        const now = ctx.currentTime;
        
        // F4 (349.23), Eb4 (311.13), Db4 (277.18), C4 (261.63)
        const notes = [349.23, 311.13, 277.18, 246.94];
        notes.forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            
            osc.type = 'sine';
            const noteStart = now + idx * 0.16;
            osc.frequency.setValueAtTime(freq, noteStart);
            // Melancholy pitch drop
            osc.frequency.exponentialRampToValueAtTime(freq * 0.94, noteStart + 0.35);
            
            gain.gain.setValueAtTime(0.0001, noteStart);
            gain.gain.linearRampToValueAtTime(0.22, noteStart + 0.04);
            gain.gain.exponentialRampToValueAtTime(0.0001, noteStart + 0.45);
            
            osc.connect(gain);
            gain.connect(ctx.destination);
            
            osc.start(noteStart);
            osc.stop(noteStart + 0.5);
        });
    } catch (e) {
        console.warn('Audio play error:', e);
    }
}

// 3. RADAR OPEN POSISI SOUND (Modern Crisp Two-Tone Tech Blip)
function playOpenPosisiSound() {
    if (isAudioMuted) return;
    try {
        const ctx = getAudioContext();
        if (!ctx) return;
        const now = ctx.currentTime;
        
        const osc1 = ctx.createOscillator();
        const osc2 = ctx.createOscillator();
        const gain = ctx.createGain();
        
        osc1.type = 'sine';
        osc2.type = 'sine';
        osc1.frequency.setValueAtTime(587.33, now); // D5
        osc2.frequency.setValueAtTime(880.00, now + 0.08); // A5
        
        gain.gain.setValueAtTime(0.0001, now);
        gain.gain.linearRampToValueAtTime(0.22, now + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.35);
        
        osc1.connect(gain);
        osc2.connect(gain);
        gain.connect(ctx.destination);
        
        osc1.start(now);
        osc1.stop(now + 0.12);
        osc2.start(now + 0.08);
        osc2.stop(now + 0.36);
    } catch (e) {
        console.warn('Audio play error:', e);
    }
}

// ======== 13. NOTIFICATION SLIDE-DOWN PANEL & LIVE FEED ========
function toggleNotificationPanel() {
    const panel = document.getElementById('notification-dropdown-panel');
    if (!panel) return;
    
    // Unlock AudioContext on interaction
    getAudioContext();
    
    const isShown = panel.classList.contains('show');
    if (isShown) {
        panel.classList.remove('show');
    } else {
        closeAllDropdowns();
        panel.classList.add('show');
        const badge = document.getElementById('notif-badge-dot');
        if (badge) badge.classList.remove('animate-pulse');
        fetchNotifications();
    }
}

function closeNotificationPanel() {
    const panel = document.getElementById('notification-dropdown-panel');
    if (panel) panel.classList.remove('show');
}

async function fetchNotifications() {
    try {
        const res = await fetch('/api/notifications');
        if (!res.ok) return;
        const items = await res.json();
        renderNotificationItems(items);
        
        // Deteksi notifikasi baru yang masuk untuk memainkan audio live
        if (!isInitialNotificationFetch && Array.isArray(items)) {
            for (const item of items) {
                if (!knownNotificationIds.has(item.id)) {
                    knownNotificationIds.add(item.id);
                    if (item.sound === 'tp') {
                        playCheerfulTpSound();
                        showNotification(item.title, 'success');
                    } else if (item.sound === 'sl') {
                        playSadSlSound();
                        showNotification(item.title, 'error');
                    } else if (item.sound === 'open') {
                        playOpenPosisiSound();
                        showNotification(item.title, 'info');
                    }
                }
            }
        } else if (Array.isArray(items)) {
            items.forEach(it => knownNotificationIds.add(it.id));
            isInitialNotificationFetch = false;
        }
    } catch (e) {
        console.warn('Error fetching notifications:', e);
    }
}

function renderNotificationItems(items) {
    const container = document.getElementById('notification-items-container');
    if (!container) return;
    
    if (!items || items.length === 0) {
        container.innerHTML = `
            <div class="py-6 text-center text-[var(--text-muted)]">
                <span class="text-2xl block mb-1">🔔</span>
                <span class="font-medium text-xs">Belum ada riwayat aktivitas bot.</span>
            </div>
        `;
        return;
    }
    
    let html = '';
    items.forEach(item => {
        let typeClass = 'notif-item-open';
        let badgeBg = 'bg-blue-500/15 text-blue-600';
        if (item.type === 'TP') {
            typeClass = 'notif-item-tp';
            badgeBg = 'bg-emerald-500/15 text-emerald-600';
        } else if (item.type === 'SL') {
            typeClass = 'notif-item-sl';
            badgeBg = 'bg-red-500/15 text-red-600';
        } else if (item.type === 'BEP') {
            typeClass = 'notif-item-open';
            badgeBg = 'bg-cyan-500/15 text-cyan-600';
        }
        
        html += `
            <div class="notif-item ${typeClass} cursor-pointer" onclick="onNotificationClick('${item.type}')">
                <div class="flex items-center justify-between">
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${badgeBg}">${item.type}</span>
                    <span class="text-[10px] font-medium text-[var(--text-muted)]">${item.time || 'Live'}</span>
                </div>
                <div class="font-bold text-[12px] text-[var(--text-primary)] mt-0.5">${item.title}</div>
                <div class="text-[11px] leading-relaxed text-[var(--text-secondary)]">${item.message}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function onNotificationClick(type) {
    if (type === 'TP') playCheerfulTpSound();
    else if (type === 'SL') playSadSlSound();
    else playOpenPosisiSound();
}

async function clearNotifications() {
    try {
        await fetch('/api/notifications/clear', { method: 'POST' });
        const container = document.getElementById('notification-items-container');
        if (container) {
            container.innerHTML = `
                <div class="py-6 text-center text-[var(--text-muted)]">
                    <span class="text-2xl block mb-1">🔔</span>
                    <span class="font-medium text-xs">Semua notifikasi telah dibersihkan.</span>
                </div>
            `;
        }
        showNotification('Notifikasi telah dibersihkan', 'info');
    } catch (e) {
        console.warn('Error clearing notifications:', e);
    }
}

// ======== 14. CUSTOM TRADE TOGGLE (ON / OFF) ========
function toggleCustomTrade(botKey) {
    customTradeState[botKey] = !customTradeState[botKey];
    const isActive = customTradeState[botKey];
    
    const btn = document.getElementById(`${botKey}-custom-trade-toggle`);
    const inputsContainer = document.getElementById(`${botKey}-custom-trade-inputs`);
    
    if (btn) {
        if (isActive) btn.classList.add('active');
        else btn.classList.remove('active');
    }
    
    if (inputsContainer) {
        if (isActive) {
            inputsContainer.classList.remove('disabled-inputs');
        } else {
            inputsContainer.classList.add('disabled-inputs');
        }
        
        const inputs = inputsContainer.querySelectorAll('input');
        inputs.forEach(input => {
            input.disabled = !isActive;
        });
    }
    
    if (isActive) {
        showNotification(`Custom Trade ${botKey.toUpperCase()} DIAKTIFKAN. Parameter Lot, TP, & SL dapat diedit manual.`, 'success');
    } else {
        showNotification(`Custom Trade ${botKey.toUpperCase()} DINONAKTIFKAN. Bot berjalan 100% full otomatis AI LightGBM.`, 'info');
    }
}
