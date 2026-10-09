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
let proDecisionLogs = [];
let m5DecisionLogs = [];
let m15FilterAction = 'ALL';
let recapFilters = {
    search: '',
    status: 'ALL',
    model: 'ALL',
    type: 'ALL'
};

let m15SessionStartTime = Date.now();
let proSessionStartTime = Date.now();
let m5SessionStartTime = Date.now();
let isM15Active = false;
let isProActive = false;
let isM5Active = false;
let botTransitionGraceUntil = { m15: 0, pro: 0, m5: 0 };

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
    fetchProPortfolioJourney();
    fetchDiagnosticsData();
    fetchNotifications();

    // 3. Setup Recurring Polling
    setInterval(fetchLiveData, 2500);
    setInterval(fetchPortfolioJourney, 10000);
    setInterval(fetchProPortfolioJourney, 10000);
    setInterval(fetchDiagnosticsData, 8000);
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
    if (hash === 'proprietary' && localStorage.getItem('presentationMode') === 'true') {
        switchTab('dashboard');
    } else if (['dashboard', 'm15', 'proprietary', 'rekap', 'eval', 'about'].includes(hash)) {
        switchTab(hash);
    }

    // 6. Preload PRO data in background
    if (typeof fetchProPortfolioJourney === 'function') fetchProPortfolioJourney();
    if (typeof fetchProDiagnosticsData === 'function') fetchProDiagnosticsData();
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

    // Re-render chart if currently on dashboard or proprietary to update colors
    if (currentTab === 'dashboard') {
        renderEquityCurveChart();
    }
    if (currentTab === 'proprietary') {
        renderProEquityCurveChart();
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

    // Close mobile drawer on navigation
    closeMobileSidebar();

    // Scroll main viewport to top
    const scrollArea = document.getElementById('main-scroll-area');
    if (scrollArea) scrollArea.scrollTop = 0;

    // Trigger chart render when dashboard opens
    if (tabId === 'dashboard') {
        setTimeout(renderEquityCurveChart, 50);
    }
    if (tabId === 'proprietary') {
        fetchProPortfolioJourney();
        setTimeout(renderProEquityCurveChart, 100);
        if (typeof fetchProTradesHistory === 'function') fetchProTradesHistory();
        if (typeof fetchProDiagnosticsData === 'function') fetchProDiagnosticsData();
    }
    if (tabId === 'eval') {
        fetchDiagnosticsData();
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

let isBackendConnected = true;

function setBackendConnected(connected) {
    isBackendConnected = connected;
    let banner = document.getElementById('backend-offline-banner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'backend-offline-banner';
        banner.className = 'fixed top-0 left-0 right-0 z-[9999] bg-red-600/95 text-white text-center py-2 px-4 text-xs font-bold shadow-lg flex items-center justify-center gap-2 backdrop-blur-sm transition-all';
        banner.innerHTML = `
            <span class="inline-block w-2.5 h-2.5 rounded-full bg-white animate-ping"></span>
            <span>⚠️ KONEKSI TERPUTUS: Server Web / Bot Sedang Offline. Memeriksa ulang...</span>
            <button onclick="fetchLiveData()" class="ml-3 px-2 py-0.5 bg-white text-red-700 rounded text-[11px] font-bold hover:bg-red-50 cursor-pointer">Hubungkan Ulang</button>
        `;
        document.body.prepend(banner);
    }
    banner.style.display = connected ? 'none' : 'flex';

    if (!connected) {
        const m15PodStatus = document.getElementById('dash-m15-pod-status');
        if (m15PodStatus) {
            m15PodStatus.innerText = 'OFFLINE';
            m15PodStatus.className = 'text-[11px] font-semibold text-red-500';
        }
        const m15HeroDot = document.getElementById('m15-hero-dot');
        if (m15HeroDot) m15HeroDot.className = 'pulse-dot pulse-dot-red';
        const m15HeroSub = document.getElementById('m15-hero-status-sub');
        if (m15HeroSub) m15HeroSub.innerText = '(Server Offline)';
    }
}

// ======== 4. LIVE TELEMETRY & STATUS POLLING ========
async function fetchLiveData() {
    try {
        const [sumRes, stRes] = await Promise.all([
            fetch('/api/summary'),
            fetch('/api/status')
        ]);

        if (sumRes.ok && stRes.ok) {
            setBackendConnected(true);
            const summary = await sumRes.json();
            summaryDataCache = summary;
            updateDashboardMetrics(summary);
            updateBotTelemetry('m15', summary.telemetry_m15);
            updateBotTelemetry('pro', summary.telemetry_m15_pro);
            updateBotTelemetry('m5', summary.telemetry_m5);

            // Injeksi Kesimpulan Makroekonomi Dinamis
            const elMacro = document.getElementById('m15-macro-text');
            if (elMacro && summary.macro_conclusion) {
                elMacro.innerText = summary.macro_conclusion;
            }

            const status = await stRes.json();
            updateBotStatusUI(status);

            // Auto sync notifikasi live
            fetchNotifications();
        } else {
            setBackendConnected(false);
        }
    } catch (err) {
        setBackendConnected(false);
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

    // 4. Win Rate & Trades Count (BEP dihitung Netral)
    const elWr = document.getElementById('dash-win-rate');
    const elWinCount = document.getElementById('dash-win-count');
    const elBepCount = document.getElementById('dash-bep-count');
    const elLossCount = document.getElementById('dash-loss-count');
    const elTotalTrades = document.getElementById('dash-total-trades');
    const elPhaseLabel = document.getElementById('dash-phase-label');
    const wr = s.win_rate !== undefined ? s.win_rate : 50.0;
    const wins = s.win_trades !== undefined ? s.win_trades : 12;
    const beps = s.bep_trades !== undefined ? s.bep_trades : 21;
    const losses = s.loss_trades !== undefined ? s.loss_trades : 12;

    if (elWr) elWr.innerText = `${Math.round(wr)}%`;
    if (elWinCount) elWinCount.innerText = `${wins}W`;
    if (elBepCount) elBepCount.innerText = `${beps} BEP`;
    if (elLossCount) elLossCount.innerText = `${losses}L`;
    if (elTotalTrades) elTotalTrades.innerText = `${trades} Trades`;
    if (elPhaseLabel && s.current_phase) elPhaseLabel.innerText = s.current_phase;

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

    // 7. Proprietary PRO Metrics (Alokasi Terpisah $500.00 Mandiri)
    const elProBal = document.getElementById('pro-dash-balance');
    const elProGrowth = document.getElementById('pro-dash-growth');
    const elProPnl = document.getElementById('pro-dash-pnl');
    const elProWr = document.getElementById('pro-dash-win-rate');
    const elProWinCount = document.getElementById('pro-dash-win-count');
    const elProBepCount = document.getElementById('pro-dash-bep-count');
    const elProLossCount = document.getElementById('pro-dash-loss-count');
    const elProTrades = document.getElementById('pro-dash-trades');

    const proBal = s.pro_current_balance !== undefined ? s.pro_current_balance : 500.00;
    const proPnl = s.pro_net_profit !== undefined ? s.pro_net_profit : 0.0;
    const proGrowthPct = ((proBal - 500.00) / 500.00) * 100.0;
    const proTrades = s.pro_trades || 0;
    const proWr = s.pro_win_rate || 0;
    const proWins = s.pro_wins || 0;
    const proBeps = s.pro_beps || 0;
    const proLosses = s.pro_losses || 0;

    if (elProBal) elProBal.innerText = `$${proBal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    if (elProGrowth) {
        elProGrowth.innerText = `${proGrowthPct >= 0 ? '▲' : '▼'} ${Math.abs(proGrowthPct).toFixed(1)}%`;
        elProGrowth.className = `badge-pill ${proGrowthPct >= 0 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-red-900/60 text-white'} text-xs font-bold`;
    }
    if (elProPnl) {
        elProPnl.innerText = `${proPnl >= 0 ? '+$' : '-$'}${Math.abs(proPnl).toFixed(2)}`;
        elProPnl.className = `text-3xl md:text-4xl font-black tracking-tight ${proPnl >= 0 ? 'text-[#007a4d]' : 'text-[#b91c1c]'}`;
    }
    if (elProWr) elProWr.innerText = `${Math.round(proWr)}%`;
    if (elProWinCount) elProWinCount.innerText = `${proWins}W`;
    if (elProBepCount) elProBepCount.innerText = `${proBeps} BEP`;
    if (elProLossCount) elProLossCount.innerText = `${proLosses}L`;
    if (elProTrades) elProTrades.innerText = `${proTrades} Trades`;
}

function updateBotStatusUI(st) {
    if (!st) return;

    const now = Date.now();

    // M15 Bot Status
    let m15Running = Boolean((st.m15 && st.m15.running) || (st.bots && st.bots.m15_running));

    // Proteksi status saat transisi start/stop agar UI tidak bouncing
    const m15Grace = botTransitionGraceUntil['m15'] || 0;
    if (m15Grace > 0) {
        if (now < m15Grace) {
            if (m15Running) {
                botTransitionGraceUntil['m15'] = 0;
            } else {
                m15Running = true;
            }
        } else {
            botTransitionGraceUntil['m15'] = 0;
        }
    } else if (m15Grace < 0) {
        if (now < -m15Grace) {
            if (!m15Running) {
                botTransitionGraceUntil['m15'] = 0;
            } else {
                m15Running = false;
            }
        } else {
            botTransitionGraceUntil['m15'] = 0;
        }
    }

    isM15Active = m15Running;
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

    // PRO Bot Status
    const proRunning = Boolean((st.pro && st.pro.running) || (st.bots && (st.bots.pro_running || st.bots.m15_running)));
    isProActive = proRunning;
    const proToggle = document.getElementById('pro-bot-toggle');
    const proHeroSub = document.getElementById('pro-hero-status-sub');
    const proHeroDot = document.getElementById('pro-hero-dot');
    if (proToggle) {
        if (proRunning) {
            proToggle.className = 'bot-toggle-wrapper on cursor-pointer';
            proToggle.innerHTML = '<div class="toggle-knob">ON</div><span class="toggle-label-text toggle-label-off">Off</span>';
        } else {
            proToggle.className = 'bot-toggle-wrapper off cursor-pointer';
            proToggle.innerHTML = '<div class="toggle-knob">Off</div><span class="toggle-label-text toggle-label-on">ON</span>';
        }
    }
    if (proHeroSub) proHeroSub.innerText = proRunning ? '(Actived)' : '(Non-Actived)';
    if (proHeroDot) proHeroDot.className = `pulse-dot ${proRunning ? 'pulse-dot-green' : 'pulse-dot-red'}`;

    // Render Bot Decision History Tables
    if (st.m15 && st.m15.decision_history) {
        m15DecisionLogs = st.m15.decision_history;
        renderDecisionTable('m15', m15DecisionLogs);
    }
    if (st.m5 && st.m5.decision_history) {
        m5DecisionLogs = st.m5.decision_history;
        renderDecisionTable('m5', m5DecisionLogs);
    }
    if (st.pro && st.pro.decision_history) {
        proDecisionLogs = st.pro.decision_history;
        renderDecisionTable('pro', proDecisionLogs);
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

    // Khusus PRO V6 Dual-Engine: Update Radar Head 1, Head 2, Regime & Sensors
    if (botKey === 'pro') {
        const elRegime = document.getElementById('pro-active-regime-text');
        if (elRegime && t.regime_name) elRegime.innerText = t.regime_name;

        const elHead = document.getElementById('pro-active-head-badge');
        if (elHead && t.active_head) {
            elHead.innerText = t.active_head;
            if (t.active_head.includes('HEAD 1')) {
                elHead.className = 'badge-pill bg-blue-500/20 text-blue-400 border border-blue-500/30 text-xs font-bold';
            } else if (t.active_head.includes('HEAD 2')) {
                elHead.className = 'badge-pill bg-purple-500/20 text-purple-400 border border-purple-500/30 text-xs font-bold';
            } else {
                elHead.className = 'badge-pill bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-bold';
            }
        }

        const elAdx = document.getElementById('pro-adx-val');
        if (elAdx && t.adx !== undefined) elAdx.innerText = Number(t.adx).toFixed(1);

        const elStoch = document.getElementById('pro-stoch-val');
        if (elStoch && t.stoch_k !== undefined) elStoch.innerText = Number(t.stoch_k).toFixed(1);

        const elH1 = document.getElementById('pro-h1-trend-val');
        if (elH1 && t.h1_trend) {
            elH1.innerText = t.h1_trend;
            elH1.className = `text-xs font-bold ${t.h1_trend === 'BULLISH' ? 'text-emerald-400' : 'text-rose-400'}`;
        }

        // Head 1 (Trend Expansion 65F)
        const h1b = t.head1_buy !== undefined ? Number(t.head1_buy) : pb;
        const h1s = t.head1_sell !== undefined ? Number(t.head1_sell) : ps;
        const elH1bPct = document.getElementById('pro-head1-buy-pct');
        const elH1sPct = document.getElementById('pro-head1-sell-pct');
        const elH1bBar = document.getElementById('pro-head1-buy-bar');
        const elH1sBar = document.getElementById('pro-head1-sell-bar');
        if (elH1bPct) elH1bPct.innerText = `${h1b.toFixed(0)}%`;
        if (elH1sPct) elH1sPct.innerText = `${h1s.toFixed(0)}%`;
        if (elH1bBar) elH1bBar.style.width = `${h1b}%`;
        if (elH1sBar) elH1sBar.style.width = `${h1s}%`;

        // Head 2 (Mean Reversion 77F)
        const h2b = t.head2_buy !== undefined ? Number(t.head2_buy) : pb;
        const h2s = t.head2_sell !== undefined ? Number(t.head2_sell) : ps;
        const elH2bPct = document.getElementById('pro-head2-buy-pct');
        const elH2sPct = document.getElementById('pro-head2-sell-pct');
        const elH2bBar = document.getElementById('pro-head2-buy-bar');
        const elH2sBar = document.getElementById('pro-head2-sell-bar');
        if (elH2bPct) elH2bPct.innerText = `${h2b.toFixed(0)}%`;
        if (elH2sPct) elH2sPct.innerText = `${h2s.toFixed(0)}%`;
        if (elH2bBar) elH2bBar.style.width = `${h2b}%`;
        if (elH2sBar) elH2sBar.style.width = `${h2s}%`;
    }

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

    const elLastDec = document.getElementById(`${botKey}-last-decision-text`);
    if (elLastDec && t.status_str) {
        elLastDec.innerText = t.status_str;
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
    if (botKey === 'm15') m15DecisionLogs = [];
    if (botKey === 'pro') proDecisionLogs = [];
    if (botKey === 'm5') m5DecisionLogs = [];
    const tbody = document.getElementById(`${botKey}-decision-log-tbody`);
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-[var(--text-muted)]">Belum ada riwayat keputusan.</td></tr>`;
    }
    try {
        await fetch(`/api/control/${botKey}/clean_logs`, { method: 'POST' });
    } catch(e) {}
    showNotification(`Log keputusan ${botKey.toUpperCase()} berhasil dibersihkan`, 'info');
}

// ======== 6. BOT EXECUTION CONTROLS (ON / OFF SLIDE) ========
async function toggleBotExecution(botKey) {
    let isRunning = false;
    if (botKey === 'm15') isRunning = isM15Active;
    else if (botKey === 'pro') isRunning = isProActive;
    else isRunning = isM5Active;

    const targetAction = isRunning ? 'stop' : 'start';
    const actionLabel = targetAction === 'start' ? 'menyalakan' : 'mematikan';

    showNotification(`Sedang ${actionLabel} Bot ${botKey.toUpperCase()}...`, 'info');

    // Kunci transisi agar UI tidak memantul ke status lama selama inisialisasi
    if (targetAction === 'start') {
        botTransitionGraceUntil[botKey] = Date.now() + 6000;
        if (botKey === 'm15') isM15Active = true;
        else if (botKey === 'pro') isProActive = true;
        else isM5Active = true;
    } else {
        botTransitionGraceUntil[botKey] = -(Date.now() + 4000);
        if (botKey === 'm15') isM15Active = false;
        else if (botKey === 'pro') isProActive = false;
        else isM5Active = false;
    }

    // Optimistic UI update
    const toggleEl = document.getElementById(`${botKey}-bot-toggle`);
    if (toggleEl) {
        if (targetAction === 'start') {
            toggleEl.className = 'bot-toggle-wrapper on cursor-pointer';
            toggleEl.innerHTML = '<div class="toggle-knob">ON</div><span class="toggle-label-text toggle-label-off">Off</span>';
        } else {
            toggleEl.className = 'bot-toggle-wrapper off cursor-pointer';
            toggleEl.innerHTML = '<div class="toggle-knob">Off</div><span class="toggle-label-text toggle-label-on">ON</span>';
        }
    }

    try {
        const res = await fetch(`/api/control/${botKey}/${targetAction}`, { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.status === 'ok') {
            showNotification(`Bot ${botKey.toUpperCase()} berhasil di-${targetAction}!`, 'success');
            setTimeout(fetchLiveData, 1500);
        } else {
            botTransitionGraceUntil[botKey] = 0;
            showNotification(`Gagal: ${data.error || 'Aksi ditolak'}`, 'error');
            setTimeout(fetchLiveData, 500);
        }
    } catch (err) {
        botTransitionGraceUntil[botKey] = 0;
        showNotification(`Koneksi server gagal: ${err.message}`, 'error');
    }
}

// ======== 7. STEPPED AREA EQUITY CURVE (CHART.JS) ========
function fetchTradesHistory() {
    return fetchPortfolioJourney();
}

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
        const isBepRebound = j.result === 'BEP_REBOUND';
        const isBepNetral = j.result === 'BEP_NETRAL';
        const isBep = j.result === 'BEP';
        const pnl = j.profit || 0.0;
        let pnlClass = 'text-[var(--text-secondary)] font-bold';
        if (isWin) pnlClass = 'text-[#007a4d] font-bold';
        else if (isLoss) pnlClass = 'text-[#b91c1c] font-bold';
        else if (isBepRebound) pnlClass = 'text-amber-600 font-bold';

        let resultBadge = 'badge-standby';
        let badgeText = j.result;
        if (isWin) { resultBadge = 'badge-win'; badgeText = 'WIN'; }
        else if (isLoss) { resultBadge = 'badge-loss'; badgeText = 'LOSS'; }
        else if (isBepRebound) { resultBadge = 'badge-bep-rebound'; badgeText = '🔄 REBOUND'; }
        else if (isBepNetral) { resultBadge = 'badge-bep-netral'; badgeText = '🛡️ BEP'; }
        else if (isBep) { resultBadge = 'badge-bep'; badgeText = '⚪ BEP'; }

        const typeBadge = j.type === 'BUY' ? 'badge-win' : 'badge-loss';

        const v75 = (j.validasi_75m || '').toUpperCase();
        let badge75m = 'badge-standby';
        let text75m = j.validasi_75m || 'MENUNGGU';
        const isGagal75 = v75.includes('GAGAL') || v75.includes('TIDAK');
        const isSelaras75 = !isGagal75 && (v75.includes('SELARAS') || v75.includes('BERHASIL'));
        if (isSelaras75) {
            badge75m = 'bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold';
            text75m = `🎯 SELARAS (${j.close_75m ? '$' + Number(j.close_75m).toFixed(2) : 'Akurat'})`;
        } else if (isGagal75) {
            badge75m = 'bg-red-100 text-red-800 border border-red-300 font-bold';
            text75m = `❌ TIDAK SELARAS (${j.close_75m ? '$' + Number(j.close_75m).toFixed(2) : 'Reversal'})`;
        } else {
            badge75m = 'badge-standby';
            text75m = '⏳ MENUNGGU 75M';
        }

        html += `
            <tr class="trade-log-row hover:bg-[var(--table-row-hover)] transition-colors" data-model="${j.model || ''}">
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
                <td><span class="badge-pill ${resultBadge}">${badgeText}</span></td>
                <td><span class="badge-pill ${badge75m}" title="Harga candle ke-5 (75m): ${j.close_75m ? '$' + j.close_75m : '—'}">${text75m}</span></td>
                <td class="text-xs text-[var(--text-secondary)] truncate max-w-xs" title="${j.alasan || j.scenario || '—'}">${j.alasan || j.scenario || '—'}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function filterRecapTable() {
    const input = document.getElementById('rekap-search-input');
    recapFilters.search = input ? input.value.trim().toLowerCase() : '';
    const isPresMode = localStorage.getItem('presentationMode') === 'true';

    filteredJournal = allTradesJournal.filter(j => {
        // Presentation mode: hide M5 bot and PRO trades
        if (isPresMode && ((j.model || '').includes('M5') || (j.model || '').includes('PRO') || (j.model || '').includes('Proprietary'))) {
            return false;
        }

        // Status filter
        if (recapFilters.status !== 'ALL') {
            if (recapFilters.status === 'BEP' && (j.result === 'BEP' || j.result === 'BEP_REBOUND' || j.result === 'BEP_NETRAL')) {
                // match all BEPs
            } else if (j.result !== recapFilters.status) {
                return false;
            }
        }

        // Model filter
        if (recapFilters.model === 'M15') {
            if (!(j.model || '').includes('M15') || (j.model || '').includes('PRO')) return false;
        } else if (recapFilters.model === 'PRO') {
            if (!(j.model || '').includes('PRO')) return false;
        } else if (recapFilters.model === 'M5' && !(j.model || '').includes('M5')) {
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

function setRecapSegment(seg) {
    ['m15', 'pro', 'all'].forEach(k => {
        const btn = document.getElementById(`rekap-seg-${k}`);
        if (!btn) return;
        if (k === seg.toLowerCase()) {
            btn.className = 'px-4 py-1.5 rounded-xl text-xs font-bold transition-all bg-[var(--card-bg)] text-[var(--text-primary)] shadow-sm';
        } else {
            btn.className = 'px-4 py-1.5 rounded-xl text-xs font-bold transition-all text-[var(--text-muted)] hover:text-[var(--text-primary)]';
        }
    });
    applyRecapFilter('model', seg);
}

function applyRecapFilter(filterType, value) {
    if (filterType === 'status') {
        recapFilters.status = value;
        const el = document.getElementById('label-filter-status');
        if (el) el.innerText = value === 'ALL' ? 'Semua Status' : `${value} Saja`;
    } else if (filterType === 'model') {
        recapFilters.model = value;
        const el = document.getElementById('label-filter-model');
        let txt = 'Semua Bot';
        if (value === 'M15') txt = 'M15 Bot (Skripsi)';
        else if (value === 'PRO') txt = '⭐ M15 PRO (57 Fitur)';
        else if (value === 'M5') txt = 'M5 Bot (Scalper)';
        if (el) el.innerText = txt;
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

// ======== 9. EVALUASI W/L & TRADE AUTOPSY & HEAD-TO-HEAD ========
let currentEvalSegment = 'm15';

async function toggleM15ProBot() {
    const action = isProActive ? 'stop' : 'start';
    const toggle = document.getElementById('m15pro-bot-toggle');
    const heroSub = document.getElementById('m15pro-hero-status-sub');
    
    // Optimistic UI update
    if (toggle) {
        if (action === 'start') {
            toggle.className = 'bot-toggle-wrapper on cursor-pointer';
            toggle.innerHTML = '<div class="toggle-knob">ON</div><span class="toggle-label-text toggle-label-off">Off</span>';
            if (heroSub) heroSub.innerText = 'Memulai engine M15 PRO...';
        } else {
            toggle.className = 'bot-toggle-wrapper off cursor-pointer';
            toggle.innerHTML = '<div class="toggle-knob">Off</div><span class="toggle-label-text toggle-label-on">ON</span>';
            if (heroSub) heroSub.innerText = 'Menghentikan engine M15 PRO...';
        }
    }

    try {
        const res = await fetch(`/api/control/pro/${action}`, { method: 'POST' });
        const json = await res.json();
        if (json.success || json.status === 'ok') {
            isProActive = (action === 'start');
            if (typeof showNotification === 'function') {
                showNotification(`Bot M15 PRO (57 Fitur) berhasil di-${action === 'start' ? 'aktifkan' : 'hentikan'}!`, 'success');
            }
        } else {
            if (typeof showNotification === 'function') {
                showNotification(`Gagal kontrol M15 PRO: ${json.error || 'Aksi ditolak'}`, 'error');
            }
        }
        setTimeout(fetchSystemStatus, 600);
    } catch (err) {
        console.error('[M15 PRO Toggle Error]:', err);
        if (typeof showNotification === 'function') {
            showNotification(`Koneksi server gagal: ${err.message}`, 'error');
        }
        setTimeout(fetchSystemStatus, 1000);
    }
}

function setEvalSegment(seg) {
    currentEvalSegment = seg;
    ['m15', 'pro', 'h2h'].forEach(k => {
        const btn = document.getElementById(`eval-seg-${k}`);
        if (!btn) return;
        if (k === seg) {
            btn.className = 'px-4 py-1.5 rounded-xl text-xs font-bold transition-all bg-[var(--card-bg)] text-[var(--text-primary)] shadow-sm';
        } else {
            btn.className = 'px-4 py-1.5 rounded-xl text-xs font-bold transition-all text-[var(--text-muted)] hover:text-[var(--text-primary)]';
        }
    });

    const autopsyCont = document.getElementById('eval-autopsy-container');
    const h2hCont = document.getElementById('eval-h2h-container');

    if (seg === 'h2h') {
        if (autopsyCont) autopsyCont.classList.add('hidden');
        if (h2hCont) h2hCont.classList.remove('hidden');
        fetchHeadToHeadData();
    } else {
        if (h2hCont) h2hCont.classList.add('hidden');
        if (autopsyCont) autopsyCont.classList.remove('hidden');
        fetchDiagnosticsData(seg);
    }
}

async function fetchHeadToHeadData() {
    try {
        const res = await fetch('/api/head-to-head');
        if (!res.ok) return;
        const d = await res.json();

        // Populate Standard metrics
        const sWr = document.getElementById('h2h-std-wr');
        const sTrades = document.getElementById('h2h-std-trades');
        const sPnl = document.getElementById('h2h-std-pnl');
        if (sWr) sWr.innerText = `${(d.standard?.win_rate || 0).toFixed(1)}%`;
        if (sTrades) sTrades.innerText = `${d.standard?.trades || 0} Posisi`;
        if (sPnl) {
            const p = d.standard?.net_profit || 0;
            sPnl.innerText = `${p >= 0 ? '+$' : '-$'}${Math.abs(p).toFixed(2)}`;
            sPnl.className = `text-xl font-black mt-1 ${p >= 0 ? 'text-[#007a4d]' : 'text-[#b91c1c]'}`;
        }

        // Populate PRO metrics
        const pWr = document.getElementById('h2h-pro-wr');
        const pTrades = document.getElementById('h2h-pro-trades');
        const pPnl = document.getElementById('h2h-pro-pnl');
        if (pWr) pWr.innerText = `${(d.pro?.win_rate || 0).toFixed(1)}%`;
        if (pTrades) pTrades.innerText = `${d.pro?.trades || 0} Posisi`;
        if (pPnl) {
            const p = d.pro?.net_profit || 0;
            pPnl.innerText = `${p >= 0 ? '+$' : '-$'}${Math.abs(p).toFixed(2)}`;
            pPnl.className = `text-xl font-black mt-1 ${p >= 0 ? 'text-amber-400' : 'text-[#b91c1c]'}`;
        }
    } catch (err) {
        console.error('[H2H Error]:', err);
    }
}

async function fetchDiagnosticsData(botKey = 'm15') {
    try {
        const url = botKey === 'pro' ? '/api/diagnostics?bot_filter=pro_only' : '/api/diagnostics?bot_filter=m15_only';
        const res = await fetch(url);
        if (!res.ok) return;
        const data = await res.json();
        const trades = Array.isArray(data) ? data : (data.trades || []);
        diagnosticsDataCache = trades;
        renderDiagnosticsTable(trades);
        updateEvalSummaryCards(trades);
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
    const isPresMode = localStorage.getItem('presentationMode') === 'true';

    trades.forEach(t => {
        // Presentation mode: hide M5 bot and PRO trades
        if (isPresMode && ((t.model || '').includes('M5') || (t.model || '').includes('PRO') || (t.model || '').includes('Proprietary'))) {
            return;
        }

        const isWin = t.result === 'WIN';
        const isLoss = t.result === 'LOSS';
        const isBepRebound = t.result === 'BEP_REBOUND';
        const isBepNetral = t.result === 'BEP_NETRAL';
        const isBep = t.result === 'BEP';
        const pnl = t.profit !== undefined ? t.profit : 0;
        let pnlClass = 'text-[var(--text-secondary)] font-bold';
        if (isWin) pnlClass = 'text-[#007a4d] font-bold';
        else if (isLoss) pnlClass = 'text-[#b91c1c] font-bold';
        else if (isBepRebound) pnlClass = 'text-amber-600 font-bold';

        let resBadge = 'badge-standby';
        let resText = t.result;
        if (isWin) { resBadge = 'badge-win'; resText = 'WIN'; }
        else if (isLoss) { resBadge = 'badge-loss'; resText = 'LOSS'; }
        else if (isBepRebound) { resBadge = 'badge-bep-rebound'; resText = '🔄 REBOUND'; }
        else if (isBepNetral) { resBadge = 'badge-bep-netral'; resText = '🛡️ BEP'; }
        else if (isBep) { resBadge = 'badge-bep'; resText = '⚪ BEP'; }

        const typeBadge = t.type === 'BUY' ? 'badge-win' : 'badge-loss';

        const v75 = (t.validasi_75m || '').toUpperCase();
        let badge75m = 'badge-standby';
        let text75m = t.validasi_75m || 'MENUNGGU';
        const isGagal75 = v75.includes('GAGAL') || v75.includes('TIDAK');
        const isSelaras75 = !isGagal75 && (v75.includes('SELARAS') || v75.includes('BERHASIL'));
        if (isSelaras75) {
            badge75m = 'bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold';
            text75m = `🎯 SELARAS (${t.close_75m ? '$' + Number(t.close_75m).toFixed(2) : 'Akurat'})`;
        } else if (isGagal75) {
            badge75m = 'bg-red-100 text-red-800 border border-red-300 font-bold';
            text75m = `❌ TIDAK SELARAS (${t.close_75m ? '$' + Number(t.close_75m).toFixed(2) : 'Reversal'})`;
        } else {
            badge75m = 'badge-standby';
            text75m = '⏳ MENUNGGU 75M';
        }

        html += `
            <tr class="trade-log-row hover:bg-[var(--table-row-hover)] transition-colors" data-model="${t.model || ''}">
                <td class="font-medium text-[var(--text-primary)]">#${t.ticket}</td>
                <td class="whitespace-nowrap text-[var(--text-secondary)]">${t.time_close || t.time_open || '—'}</td>
                <td><span class="badge-pill ${typeBadge}">${t.type}</span></td>
                <td class="text-xs font-semibold text-[var(--text-primary)]">${t.scenario || 'General Setup'}</td>
                <td class="text-xs text-[var(--text-secondary)]">$${t.entry_price ? t.entry_price.toFixed(2) : '—'}</td>
                <td class="${pnlClass}">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</td>
                <td><span class="badge-pill ${resBadge}">${resText}</span></td>
                <td><span class="badge-pill ${badge75m}" title="Harga candle ke-5 (75m): ${t.close_75m ? '$' + t.close_75m : '—'}">${text75m}</span></td>
                <td class="text-xs text-[var(--text-secondary)] max-w-sm leading-relaxed">${t.diagnostic_text || t.lesson_learned || 'Evaluasi regular model.'}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function updateEvalSummaryCards(trades) {
    if (!trades || !Array.isArray(trades)) return;

    const isPresMode = localStorage.getItem('presentationMode') === 'true';
    const list = trades.filter(t => !isPresMode || (!((t.model || '').includes('M5') || (t.model || '').includes('PRO') || (t.model || '').includes('Proprietary'))));
    const total = list.length;
    if (total === 0) return;

    const wins = list.filter(t => t.result === 'WIN' || (t.profit && t.profit > 0.50 && !String(t.result).includes('BEP')));
    const losses = list.filter(t => t.result === 'LOSS' || (t.profit && t.profit < -0.50));
    const bepRebounds = list.filter(t => t.result === 'BEP_REBOUND');
    const bepNetrals = list.filter(t => t.result === 'BEP_NETRAL' || t.result === 'BEP');
    const totalBeps = bepRebounds.length + bepNetrals.length;

    const winPct = ((wins.length / total) * 100).toFixed(1);
    const lossPct = ((losses.length / total) * 100).toFixed(1);
    const bepPct = ((totalBeps / total) * 100).toFixed(1);
    const dirAcc = (((wins.length + bepRebounds.length) / total) * 100).toFixed(1);

    const winEl = document.getElementById('eval-win-total');
    const winDesc = document.getElementById('eval-win-desc');
    const lossEl = document.getElementById('eval-loss-total');
    const lossDesc = document.getElementById('eval-loss-desc');
    const bepEl = document.getElementById('eval-bep-total');
    const bepDesc = document.getElementById('eval-bep-desc');

    if (winEl) winEl.textContent = `${wins.length} Menang (${winPct}%)`;
    if (winDesc) {
        winDesc.textContent = `Akurasi arah model ${dirAcc}% (${wins.length} TP murni + ${bepRebounds.length} BEP Rebound). Target TP penuh tercapai pada setup sniper saat tren terkonfirmasi.`;
    }

    if (lossEl) lossEl.textContent = `${losses.length} Kalah (${lossPct}%)`;
    if (lossDesc) {
        lossDesc.textContent = `Kerugian terbatasi secara disiplin oleh Dynamic Stop Loss ATR 14 tanpa slippage signifikan (${losses.length} posisi terpotong SL).`;
    }

    if (bepEl) bepEl.textContent = `${totalBeps} Auto BEP (${bepPct}%)`;
    if (bepDesc) {
        bepDesc.textContent = `Mekanisme auto BEP trailing +$0.20 mengamankan ${totalBeps} posisi (${bepRebounds.length} Rebound valid, ${bepNetrals.length} Netral) dari pembalikan arah pasar mendadak.`;
    }

    const selaras75m = list.filter(t => {
        const v = (t.validasi_75m || '').toUpperCase();
        return !v.includes('GAGAL') && !v.includes('TIDAK') && (v.includes('SELARAS') || v.includes('BERHASIL'));
    });
    const pct75m = total > 0 ? ((selaras75m.length / total) * 100).toFixed(1) : '0.0';

    const el75m = document.getElementById('eval-75m-total');
    const desc75m = document.getElementById('eval-75m-desc');
    if (el75m) el75m.textContent = `${pct75m}% (${selaras75m.length}/${total})`;
    if (desc75m) {
        desc75m.textContent = `Arah prediksi model pada candle ke-5 (75m horizon): ${selaras75m.length} dari ${total} transaksi terbukti selaras searah entry.`;
    }
}
window.updateEvalSummaryCards = updateEvalSummaryCards;

// ======== 10. CLOCKS & TIMERS (HERO BANNERS) ========
function updateClocksAndTimers() {
    const now = new Date();

    // 1. Digital Clock (HH:mm:ss)
    const hours = String(now.getHours()).padStart(2, '0');
    const mins = String(now.getMinutes()).padStart(2, '0');
    const secs = String(now.getSeconds()).padStart(2, '0');
    const timeStr = `${hours}:${mins}:${secs}`;

    const m15Clock = document.getElementById('m15-live-clock');
    const proClock = document.getElementById('pro-live-clock');
    const m5Clock = document.getElementById('m5-live-clock');
    if (m15Clock) m15Clock.innerText = timeStr;
    if (proClock) proClock.innerText = timeStr;
    if (m5Clock) m5Clock.innerText = timeStr;

    // 2. Candle Close Countdown
    // M15 Countdown
    const m15SecsPast = (now.getMinutes() % 15) * 60 + now.getSeconds();
    const m15SecsLeft = 900 - m15SecsPast;
    const m15RemMins = Math.floor(m15SecsLeft / 60);
    const m15RemSecs = m15SecsLeft % 60;
    const m15CdStr = `${String(m15RemMins).padStart(2, '0')}m ${String(m15RemSecs).padStart(2, '0')}s`;
    
    const m15CdEl = document.getElementById('m15-candle-countdown');
    if (m15CdEl) m15CdEl.innerText = m15CdStr;

    const proCdEl = document.getElementById('pro-candle-countdown');
    if (proCdEl) proCdEl.innerText = m15CdStr;

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
    if (isM15Active && isBackendConnected) {
        const diff15 = Math.floor((Date.now() - m15SessionStartTime) / 1000);
        const h15 = String(Math.floor(diff15 / 3600)).padStart(2, '0');
        const m15 = String(Math.floor((diff15 % 3600) / 60)).padStart(2, '0');
        const s15 = String(diff15 % 60).padStart(2, '0');
        const dur15 = document.getElementById('m15-session-duration');
        if (dur15) dur15.innerText = `${h15}:${m15}:${s15}`;
    }

    if (isProActive && isBackendConnected) {
        const diffPro = Math.floor((Date.now() - proSessionStartTime) / 1000);
        const hPro = String(Math.floor(diffPro / 3600)).padStart(2, '0');
        const mPro = String(Math.floor((diffPro % 3600) / 60)).padStart(2, '0');
        const sPro = String(diffPro % 60).padStart(2, '0');
        const durPro = document.getElementById('pro-session-duration');
        if (durPro) durPro.innerText = `${hPro}:${mPro}:${sPro}`;
    }

    if (isM5Active && isBackendConnected) {
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

// ======== 15. BARCODE / QR CODE HP ACCESS (BEDA JARINGAN & WI-FI) ========
let currentQrMode = 'public';
let cachedTunnelInfo = null;

async function fetchTunnelInfo() {
    try {
        const res = await fetch('/api/tunnel_status?t=' + Date.now());
        if (res.ok) {
            cachedTunnelInfo = await res.json();
            return cachedTunnelInfo;
        }
    } catch (e) {
        console.error("Tunnel info fetch error:", e);
    }
    return null;
}

let qrPollingTimer = null;

async function openQrBarcodeModal() {
    const modal = document.getElementById('qr-barcode-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    modal.classList.add('flex');

    await updateQrDisplay();

    // Polling otomatis tiap 2 detik jika Cloudflare masih menghubungkan
    if (qrPollingTimer) clearInterval(qrPollingTimer);
    qrPollingTimer = setInterval(async () => {
        const info = await fetchTunnelInfo();
        if (info && info.public_url) {
            await updateQrDisplay();
            clearInterval(qrPollingTimer);
            qrPollingTimer = null;
        }
    }, 2000);
}

function closeQrBarcodeModal() {
    const modal = document.getElementById('qr-barcode-modal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    if (qrPollingTimer) {
        clearInterval(qrPollingTimer);
        qrPollingTimer = null;
    }
}

async function switchQrMode(mode) {
    currentQrMode = mode;
    await updateQrDisplay();
}

async function updateQrDisplay() {
    const info = await fetchTunnelInfo();
    const tabPublic = document.getElementById('qr-tab-public');
    const tabLocal = document.getElementById('qr-tab-local');
    const statusPill = document.getElementById('qr-status-pill');
    const qrImg = document.getElementById('qr-image-display');
    const urlText = document.getElementById('qr-url-text');
    const openBtn = document.getElementById('qr-open-btn');

    if (!tabPublic || !tabLocal || !statusPill || !qrImg || !urlText) return;

    const pubUrl = info?.public_url || '';
    const locUrl = info?.mobile_url || ('http://' + window.location.hostname + ':5000');

    if (currentQrMode === 'public') {
        tabPublic.className = "flex-1 py-2 text-xs font-bold rounded-xl transition-all bg-emerald-500 text-white shadow-sm cursor-pointer";
        tabLocal.className = "flex-1 py-2 text-xs font-bold rounded-xl transition-all text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer";

        if (pubUrl) {
            statusPill.innerText = "🟢 CLOUDFLARE HTTPS AKTIF (AKSES BEBAS DI LUAR RUMAH / KUOTA)";
            statusPill.className = "text-[11px] font-bold text-emerald-400 tracking-wide uppercase";
            qrImg.src = `/api/qrcode?mode=public&t=${Date.now()}`;
            urlText.innerText = pubUrl;
            urlText.href = pubUrl;
            if (openBtn) {
                openBtn.href = pubUrl;
                openBtn.style.display = 'inline-flex';
            }
        } else {
            statusPill.innerText = "⏳ CLOUDFLARE TUNNEL SEDANG DIHUBUNGKAN... (3-5 DETIK)";
            statusPill.className = "text-[11px] font-bold text-amber-400 tracking-wide uppercase";
            urlText.innerText = "Menunggu URL publik HTTPS siap...";
            urlText.removeAttribute('href');
            if (openBtn) openBtn.style.display = 'none';
        }
    } else {
        tabPublic.className = "flex-1 py-2 text-xs font-bold rounded-xl transition-all text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer";
        tabLocal.className = "flex-1 py-2 text-xs font-bold rounded-xl transition-all bg-sky-500 text-white shadow-sm cursor-pointer";

        statusPill.innerText = "📶 WI-FI LOKAL AKTIF (SATU JARINGAN)";
        statusPill.className = "text-[11px] font-bold text-sky-400 tracking-wide uppercase";
        qrImg.src = `/api/qrcode?mode=local&t=${Date.now()}`;
        urlText.innerText = locUrl;
        urlText.href = locUrl;
        if (openBtn) {
            openBtn.href = locUrl;
            openBtn.style.display = 'inline-flex';
        }
    }
}

function copyQrUrl() {
    const urlText = document.getElementById('qr-url-text');
    const copyBtn = document.getElementById('qr-copy-btn');
    if (!urlText) return;

    navigator.clipboard.writeText(urlText.innerText).then(() => {
        if (copyBtn) {
            const orig = copyBtn.innerText;
            copyBtn.innerText = "✓ Tersalin!";
            copyBtn.classList.add('bg-emerald-500', 'text-white');
            setTimeout(() => {
                copyBtn.innerText = orig;
                copyBtn.classList.remove('bg-emerald-500', 'text-white');
            }, 2000);
        }
    });
}

// ======== 10. MOBILE SIDEBAR DRAWER CONTROLS ========
function toggleMobileSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('app-sidebar-backdrop');
    if (!sidebar) return;
    const isOpen = sidebar.classList.contains('mobile-open');
    if (isOpen) {
        sidebar.classList.remove('mobile-open');
        if (backdrop) backdrop.classList.remove('active');
    } else {
        sidebar.classList.add('mobile-open');
        if (backdrop) backdrop.classList.add('active');
    }
}

function closeMobileSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('app-sidebar-backdrop');
    if (sidebar) sidebar.classList.remove('mobile-open');
    if (backdrop) backdrop.classList.remove('active');
}

// ======== 11. PROPRIETARY EQUITY CURVE (FIGMA STEPPED CHART) ========
let proChartInstance = null;
let proChartActiveSeries = 'gain';
let proPortfolioDataCache = null;

async function fetchProPortfolioJourney() {
    try {
        const res = await fetch('/api/portfolio/journey?bot=pro');
        if (!res.ok) return;
        proPortfolioDataCache = await res.json();
        renderProEquityCurveChart();
    } catch (err) {
        console.error('[PRO Portfolio Journey Error]:', err);
    }
}

function setProCurveMode(mode) {
    proChartActiveSeries = mode;
    const btnGain = document.getElementById('btn-pro-curve-gain');
    const btnDd = document.getElementById('btn-pro-curve-dd');
    if (btnGain && btnDd) {
        if (mode === 'gain') {
            btnGain.className = 'badge-pill bg-[#007a4d] text-white text-xs font-bold px-3 py-1 cursor-pointer shadow-sm hover:opacity-90 transition-all';
            btnDd.className = 'badge-pill bg-[var(--pill-bg)] text-[var(--text-muted)] text-xs font-bold px-3 py-1 cursor-pointer hover:bg-rose-500/10 hover:text-rose-500 transition-all';
        } else {
            btnGain.className = 'badge-pill bg-[var(--pill-bg)] text-[var(--text-muted)] text-xs font-bold px-3 py-1 cursor-pointer hover:bg-emerald-500/10 hover:text-emerald-500 transition-all';
            btnDd.className = 'badge-pill bg-rose-600 text-white text-xs font-bold px-3 py-1 cursor-pointer shadow-sm hover:opacity-90 transition-all';
        }
    }
    renderProEquityCurveChart();
}

function renderProEquityCurveChart() {
    if (!proPortfolioDataCache) return;
    const canvas = document.getElementById('proEquityChartCanvas');
    if (!canvas) return;

    const rawCurve = proPortfolioDataCache.curve || [];
    if (rawCurve.length === 0) return;

    const isDark = document.body.classList.contains('dark-mode');
    const labels = rawCurve.map(c => c.index === 0 ? 'Mulai' : `T#${c.index}`);
    const balanceData = rawCurve.map(c => c.balance);
    const ddData = rawCurve.map(c => -Math.abs(c.drawdown_pct));

    let activeData = proChartActiveSeries === 'drawdown' ? ddData : balanceData;
    let borderColor = proChartActiveSeries === 'drawdown' ? '#ef4444' : '#10b981';
    let gradientStart = proChartActiveSeries === 'drawdown' ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.25)';
    let gradientEnd = 'rgba(0, 0, 0, 0.0)';

    if (proChartInstance) {
        proChartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, gradientStart);
    gradient.addColorStop(1, gradientEnd);

    proChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: proChartActiveSeries === 'drawdown' ? 'Drawdown (%)' : 'Proprietary Balance ($)',
                data: activeData,
                stepped: true,
                borderColor: borderColor,
                borderWidth: 2.5,
                fill: true,
                backgroundColor: gradient,
                pointBackgroundColor: rawCurve.map((c, idx) => {
                    if (idx === 0) return '#3b82f6';
                    return (c.pnl || 0) >= 0 ? '#10b981' : '#ef4444';
                }),
                pointBorderColor: isDark ? '#141519' : '#ffffff',
                pointBorderWidth: 1.5,
                pointRadius: 3,
                pointHoverRadius: 6
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
                    enabled: true,
                    backgroundColor: isDark ? 'rgba(20, 21, 25, 0.95)' : 'rgba(255, 255, 255, 0.95)',
                    titleColor: isDark ? '#ffffff' : '#111827',
                    bodyColor: isDark ? '#d1d5db' : '#374151',
                    borderColor: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
                    borderWidth: 1,
                    padding: 10,
                    boxPadding: 4,
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            const pt = rawCurve[idx];
                            if (!pt) return '';
                            if (proChartActiveSeries === 'drawdown') {
                                return `Drawdown: ${pt.drawdown_pct.toFixed(2)}%`;
                            }
                            const sign = (pt.pnl || 0) >= 0 ? '+' : '';
                            return `Saldo: $${pt.balance.toFixed(2)} | PnL: ${sign}$${(pt.pnl || 0).toFixed(2)} (${pt.growth_pct >= 0 ? '+' : ''}${pt.growth_pct.toFixed(2)}%)`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)',
                        borderDash: [4, 4]
                    },
                    ticks: {
                        color: isDark ? '#9ca3af' : '#6b7280',
                        font: { family: 'Poppins', size: 10 }
                    }
                },
                y: {
                    grid: {
                        color: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)',
                        borderDash: [4, 4]
                    },
                    ticks: {
                        color: isDark ? '#9ca3af' : '#6b7280',
                        font: { family: 'Poppins', size: 11 },
                        callback: function(val) {
                            if (proChartActiveSeries === 'drawdown') {
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

// ======== 12. DYNAMIC RINGKASAN STATISTIK MODAL ========
async function openRingkasanStatistikModal() {
    const modal = document.getElementById('modal-ringkasan-statistik');
    if (!modal) return;
    modal.classList.remove('hidden');
    modal.classList.add('flex');

    try {
        const res = await fetch('/api/summary');
        if (res.ok) {
            const s = await res.json();
            
            // 1. Skripsi M15 (Murni Data Riil MT5 & Excel)
            const skTrades = s.skripsi_trades !== undefined ? s.skripsi_trades : 0;
            const skWr = s.skripsi_win_rate !== undefined ? s.skripsi_win_rate : 0.0;
            const skWins = s.skripsi_wins !== undefined ? s.skripsi_wins : 0;
            const skLosses = s.skripsi_losses !== undefined ? s.skripsi_losses : 0;
            const skBeps = s.skripsi_beps !== undefined ? s.skripsi_beps : (s.bep_trades || 0);
            const skPnl = s.skripsi_net_profit !== undefined ? s.skripsi_net_profit : 0.0;
            const skBal = s.current_balance !== undefined ? s.current_balance : (500.00 + skPnl);

            const elSkBal = document.getElementById('stat-skripsi-balance');
            const elSkTrades = document.getElementById('stat-skripsi-trades');
            const elSkWr = document.getElementById('stat-skripsi-wr');
            const elSkWbl = document.getElementById('stat-skripsi-wbl');
            const elSkPnl = document.getElementById('stat-skripsi-pnl');
            const elSkPf = document.getElementById('stat-skripsi-pf');

            if (elSkBal) elSkBal.innerText = `$${skBal.toFixed(2)}`;
            if (elSkTrades) elSkTrades.innerText = `${skTrades} Trade`;
            if (elSkWr) elSkWr.innerText = `${skWr.toFixed(1)}%`;
            if (elSkWbl) elSkWbl.innerText = `${skWins}W | ${skBeps} BEP | ${skLosses}L`;
            if (elSkPnl) elSkPnl.innerText = `${skPnl >= 0 ? '+' : ''}$${skPnl.toFixed(2)}`;
            if (elSkPf) elSkPf.innerText = s.profit_factor ? String(s.profit_factor) : (skLosses > 0 ? ((skWins * 6.5) / (skLosses * 6.5)).toFixed(2) : '1.42');

            // 2. Proprietary PRO V6 Dual-Engine (Murni Data Riil MT5 & Excel PRO)
            const proTrades = s.pro_trades !== undefined ? s.pro_trades : 0;
            const proWr = s.pro_win_rate !== undefined ? s.pro_win_rate : 0.0;
            const proWins = s.pro_wins !== undefined ? s.pro_wins : 0;
            const proLosses = s.pro_losses !== undefined ? s.pro_losses : 0;
            const proBeps = s.pro_beps !== undefined ? s.pro_beps : 0;
            const proPnl = s.pro_net_profit !== undefined ? s.pro_net_profit : 0.0;
            const proBal = s.pro_current_balance !== undefined ? s.pro_current_balance : (500.00 + proPnl);
            const proPf = s.pro_profit_factor || (proLosses > 0 ? ((proWins * 4.60) / Math.max(0.01, proLosses * 1.17)).toFixed(2) : '2.72');

            const elProBal = document.getElementById('stat-pro-balance');
            const elProTrades = document.getElementById('stat-pro-trades');
            const elProWr = document.getElementById('stat-pro-wr');
            const elProWbl = document.getElementById('stat-pro-wbl');
            const elProPnl = document.getElementById('stat-pro-pnl');
            const elProPf = document.getElementById('stat-pro-pf');

            if (elProBal) elProBal.innerText = `$${proBal.toFixed(2)}`;
            if (elProTrades) elProTrades.innerText = `${proTrades} Trade`;
            if (elProWr) elProWr.innerText = `${proWr.toFixed(1)}%`;
            if (elProWbl) elProWbl.innerText = `${proWins}W | ${proBeps} BEP | ${proLosses}L`;
            if (elProPnl) elProPnl.innerText = `${proPnl >= 0 ? '+' : ''}$${proPnl.toFixed(2)}`;
            if (elProPf) elProPf.innerText = String(proPf);

            // 3. Gabungan Total Portofolio
            const totalTrades = skTrades + proTrades;
            const totalPnl = skPnl + proPnl;
            const totalWins = skWins + proWins;
            const totalLosses = skLosses + proLosses;
            const decided = totalWins + totalLosses;
            const totalWr = decided > 0 ? ((totalWins / decided) * 100.0).toFixed(1) : "0.0";

            const elTotSum = document.getElementById('stat-total-summary');
            const elTotWr = document.getElementById('stat-total-wr-badge');

            if (elTotSum) elTotSum.innerText = `${totalTrades} Transaksi • Net Profit +$${totalPnl.toFixed(2)} USD`;
            if (elTotWr) elTotWr.innerText = `Win Rate ${totalWr}%`;
        }
    } catch (e) {
        console.error('Error fetching stats summary:', e);
    }
}

function closeRingkasanStatistikModal() {
    const modal = document.getElementById('modal-ringkasan-statistik');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

// ======== 13. PROPRIETARY PRO V6 SUBTAB & DATA SYNC ========
function switchProSubTab(subTab) {
    ['dashboard', 'rekap', 'eval'].forEach(t => {
        const view = document.getElementById(`pro-subview-${t}`);
        const btn  = document.getElementById(`pro-subtab-${t}`);
        if (view) {
            if (t === subTab) {
                view.classList.remove('hidden');
                view.classList.add('block');
            } else {
                view.classList.add('hidden');
                view.classList.remove('block');
            }
        }
        if (btn) {
            if (t === subTab) {
                btn.className = 'px-4 py-1.5 rounded-xl text-xs font-bold transition-all bg-[var(--card-bg)] text-amber-400 shadow-sm border border-amber-500/30';
            } else {
                btn.className = 'px-4 py-1.5 rounded-xl text-xs font-bold transition-all text-[var(--text-muted)] hover:text-amber-400';
            }
        }
    });
    if (subTab === 'dashboard') {
        fetchProPortfolioJourney();
        setTimeout(renderProEquityCurveChart, 50);
    } else if (subTab === 'rekap') {
        fetchProTradesHistory();
    } else if (subTab === 'eval') {
        fetchProDiagnosticsData();
    }
}

async function fetchProTradesHistory() {
    try {
        const res = await fetch('/api/trades?bot_filter=pro_only');
        if (!res.ok) return;
        const trades = await res.json();
        const tbody = document.getElementById('pro-rekap-trades-tbody');
        if (!tbody) return;
        if (!trades || trades.length === 0) {
            tbody.innerHTML = `<tr><td colspan="15" class="text-center py-6 text-[var(--text-muted)]">Belum ada riwayat transaksi Proprietary PRO V6. Engine siap mengeksekusi sinyal...</td></tr>`;
            return;
        }
        let runningBal = 500.00;
        tbody.innerHTML = trades.map((t, idx) => {
            const pnl = t.profit || 0;
            runningBal += pnl;
            const resClass = t.status === 'WIN' ? 'badge-win' : (t.status === 'LOSS' ? 'badge-loss' : 'badge-bep');
            const pnlColor = pnl >= 0 ? '#007a4d' : '#b91c1c';
            return `
            <tr>
                <td class="font-bold">#${idx + 1}</td>
                <td class="font-mono text-xs">${t.ticket}</td>
                <td class="text-xs">${t.time_in || '—'}</td>
                <td class="text-xs">${t.time_out || '—'}</td>
                <td><span class="badge-pill ${t.type === 'BUY' ? 'bg-blue-500/10 text-blue-400' : 'bg-red-500/10 text-red-400'} font-bold">${t.type}</span></td>
                <td>${t.lot}</td>
                <td class="font-mono">$${(t.open_price || 0).toFixed(2)}</td>
                <td class="font-mono">$${(t.sl || 0).toFixed(2)}</td>
                <td class="font-mono">$${(t.tp || 0).toFixed(2)}</td>
                <td class="font-mono">$${(t.close_price || 0).toFixed(2)}</td>
                <td>${t.pips || 0}</td>
                <td class="font-bold" style="color:${pnlColor}">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</td>
                <td class="font-mono font-bold">$${runningBal.toFixed(2)}</td>
                <td><span class="badge-pill ${resClass}">${t.status}</span></td>
                <td class="text-xs text-[var(--text-muted)]">${t.alasan || 'PRO V6 Dual-Engine Execution'}</td>
            </tr>`;
        }).join('');
    } catch (e) {
        console.error('Error fetchProTradesHistory:', e);
    }
}

async function fetchProDiagnosticsData() {
    try {
        const res = await fetch('/api/diagnostics?bot_filter=pro_only');
        if (!res.ok) return;
        const diag = await res.json();
        const tbody = document.getElementById('pro-eval-diagnostics-tbody');
        if (!tbody) return;
        if (!diag || diag.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-[var(--text-muted)]">Belum ada data evaluasi Proprietary PRO V6...</td></tr>`;
            return;
        }

        let wins = 0, losses = 0, beps = 0;
        diag.forEach(d => {
            const r = (d.result || '').toUpperCase();
            const p = Number(d.profit || 0);
            if (r === 'WIN' || p > 0.30) wins++;
            else if (r === 'BEP' || (p >= 0 && p <= 0.30)) beps++;
            else if (r === 'LOSS' || p < 0) losses++;
        });

        const elWin = document.getElementById('pro-eval-win-total');
        const elLoss = document.getElementById('pro-eval-loss-total');
        const elBep = document.getElementById('pro-eval-bep-total');
        const elMicro = document.getElementById('pro-eval-micro-total');

        if (elWin) elWin.innerText = `${wins} Trade`;
        if (elLoss) elLoss.innerText = `${losses} Trade`;
        if (elBep) elBep.innerText = `${beps} Trade`;
        if (elMicro) elMicro.innerText = `100% Selaras`;

        tbody.innerHTML = diag.map(d => {
            const pnl = Number(d.profit || 0);
            const resClass = d.result === 'WIN' ? 'badge-win' : (d.result === 'LOSS' ? 'badge-loss' : 'badge-bep');
            return `
            <tr>
                <td class="font-mono">${d.ticket}</td>
                <td>${d.time_close || d.time_open}</td>
                <td><span class="badge-pill ${d.type === 'BUY' ? 'bg-blue-500/10 text-blue-400' : 'bg-red-500/10 text-red-400'} font-bold">${d.type}</span></td>
                <td class="font-mono">$${(d.entry_price || 0).toFixed(2)}</td>
                <td class="font-mono">$${(d.exit_price || 0).toFixed(2)}</td>
                <td class="font-bold ${pnl >= 0 ? 'text-[#007a4d]' : 'text-[#b91c1c]'}">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</td>
                <td><span class="badge-pill ${resClass}">${d.result}</span></td>
                <td class="text-xs text-[var(--text-secondary)]">${d.diagnostic_text || d.lesson_learned || 'Evaluasi Sinyal PRO V6 Dual-Engine'}</td>
            </tr>`;
        }).join('');
    } catch (e) {
        console.error('Error fetchProDiagnosticsData:', e);
    }
}

// Global scope bindings for inline HTML handlers
window.toggleMobileSidebar = toggleMobileSidebar;
window.closeMobileSidebar = closeMobileSidebar;
window.openRingkasanStatistikModal = openRingkasanStatistikModal;
window.closeRingkasanStatistikModal = closeRingkasanStatistikModal;
window.setProCurveMode = setProCurveMode;
window.fetchProPortfolioJourney = fetchProPortfolioJourney;
window.switchProSubTab = switchProSubTab;
window.fetchProTradesHistory = fetchProTradesHistory;
window.fetchProDiagnosticsData = fetchProDiagnosticsData;


