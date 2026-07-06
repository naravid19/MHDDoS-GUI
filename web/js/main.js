import { SocketManager } from './core/socket.js';
import { TerminalUI, setLogLevel } from './ui/terminal.js';
import { showToast } from './ui/toast.js';
import { telemetry } from './core/telemetry.js';
import { TelemetryChart } from './core/telemetry-chart.js';
import { TaskManager } from './ui/tasks.js';
import * as engine from './core/engine.js';
import * as modals from './ui/modals.js';
import * as history from './ui/history.js';
import { uiProMax } from './ui/ui-pro-max.js';
import * as helpers from './utils/helpers.js';

// Initialize UI Components
const terminal = new TerminalUI('terminal-content');
const mainChart = new TelemetryChart('networkVelocityChart');
const tasks = new TaskManager('tasks-container');

// Save references for global helper access
window._terminal = terminal;

// Bridge to Global Scope for HTML Event Handlers
window.handleMainAction = engine.handleMainAction;
window.analyzeTarget = engine.analyzeTarget;

window.openToolsModal = modals.openToolsModal;
window.closeToolsModal = modals.closeToolsModal;
window.switchToolTab = modals.switchToolTab;
window.executeTool = modals.executeTool;

window.openSettingsModal = modals.openSettingsModal;
window.closeSettingsModal = modals.closeSettingsModal;
window.saveSettings = modals.saveSettings;

window.openConfigModal = modals.openConfigModal;
window.closeConfigModal = modals.closeConfigModal;
window.addConfigSource = modals.addConfigSource;
window.saveProxyConfig = modals.saveProxyConfig;
window.switchAssetTab = modals.switchAssetTab;

window.setLogLevel = setLogLevel;
window.clearTerminal = () => terminal.clear();
window.copyLogs = async () => {
    await terminal.copy();
    showToast("Console output copied to clipboard", "success");
};
window.toggleTerminalScroll = () => {
    const active = terminal.toggleAutoScroll();
    const icon = document.getElementById('scroll-toggle-icon');
    if (icon) {
        icon.innerText = active ? 'pause' : 'play_arrow';
    }
    showToast(active ? "Auto-scroll resumed" : "Auto-scroll paused", "info");
};

window.switchMainView = (view) => {
    history.switchMainView(view);
};

window.scrollToConfig = () => {
    const el = document.getElementById('config-section');
    if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
        el.classList.add('ring-4', 'ring-primary/20', 'rounded-2xl');
        setTimeout(() => el.classList.remove('ring-4', 'ring-primary/20'), 2000);
    }
};

window.refreshHistory = history.refreshHistory;
window.changeHistoryPage = history.changeHistoryPage;
window.showToast = showToast;
window.uiProMax = uiProMax;
window.uploadAssetFile = modals.uploadAssetFile;
window.deleteAssetFile = modals.deleteAssetFile;

window.toggleAdvancedSettings = function() {
    const container = document.getElementById('advanced-settings-container');
    const icon = document.getElementById('advanced-settings-icon');
    if (container.classList.contains('hidden')) {
        container.classList.remove('hidden');
        if(icon) icon.style.transform = 'rotate(180deg)';
    } else {
        container.classList.add('hidden');
        if(icon) icon.style.transform = 'rotate(0deg)';
    }
}

window.populateFileLists = async function() {
    try {
        const res = await fetch('/api/files/list');
        const data = await res.json();
        if (data.status === 'success') {
            const proxySelect = document.getElementById('proxy_list');
            const reflSelect = document.getElementById('reflector');
            const modalProxyList = document.getElementById('modal-proxy-list');
            const modalReflList = document.getElementById('modal-reflector-list');

            if (proxySelect) {
                proxySelect.innerHTML = '<option value="AUTO">⚡ Auto Harvest (Smart)</option>' +
                    '<option value="">📄 default.txt</option>' +
                    data.proxies.filter(f => f !== 'default.txt').map(f => `<option value="${f}">📄 ${f}</option>`).join('');
            }
            if (reflSelect) {
                reflSelect.innerHTML = '<option value="">None (Standard)</option>' + 
                    '<option value="reflector.txt">📄 reflector.txt</option>' +
                    data.reflectors.filter(f => f !== 'reflector.txt').map(f => `<option value="${f}">📄 ${f}</option>`).join('');
            }
            
            // Populate lists in Asset Manager modal
            if (modalProxyList) {
                modalProxyList.innerHTML = data.proxies.map(f => `
                    <div class="flex justify-between items-center py-1.5 border-b border-white/5 last:border-0 group">
                        <span>${f}</span>
                        ${f !== 'default.txt' ? `<button onclick="deleteAssetFile('proxy', '${f}')" class="text-error opacity-0 group-hover:opacity-100 transition-opacity" title="Delete File"><span class="material-symbols-outlined text-[14px]">delete</span></button>` : ''}
                    </div>`).join('');
            }
            if (modalReflList) {
                modalReflList.innerHTML = data.reflectors.map(f => `
                    <div class="flex justify-between items-center py-1.5 border-b border-white/5 last:border-0 group">
                        <span>${f}</span>
                        ${f !== 'reflector.txt' ? `<button onclick="deleteAssetFile('reflector', '${f}')" class="text-error opacity-0 group-hover:opacity-100 transition-opacity" title="Delete File"><span class="material-symbols-outlined text-[14px]">delete</span></button>` : ''}
                    </div>`).join('');
            }
        }
    } catch (e) { console.error("File list fetch failed", e); }
}

function handleMethodChange() {
    const method = document.getElementById('method').value;
    const reflContainer = document.getElementById('reflector-container');
    
    // List of methods requiring reflector (Amplification)
    const ampMethods = ["MEM", "NTP", "DNS", "ARD", "CLDAP", "CHAR", "RDP"];
    
    if (ampMethods.includes(method)) {
        reflContainer.classList.remove('hidden');
    } else {
        reflContainer.classList.add('hidden');
    }
}

function populateMethods() {
    const methodSelect = document.getElementById('method');
    if (!methodSelect) return;

    // Full list synced with resource/start.py -> Methods class
    const l7 = ["CFB", "BYPASS", "GET", "POST", "OVH", "STRESS", "DYN", "SLOW", "HEAD", "NULL", "COOKIE", "PPS", "EVEN", "GSB", "DGB", "AVB", "CFBUAM", "APACHE", "XMLRPC", "BOT", "BOMB", "DOWNLOADER", "KILLER", "TOR", "RHEX", "STOMP", "PGET", "OPTIONS", "PURGE"];
    const l4_amp = ["MEM", "NTP", "DNS", "ARD", "CLDAP", "CHAR", "RDP"];
    const l4_normal = ["TCP", "UDP", "SYN", "VSE", "MINECRAFT", "MCBOT", "CONNECTION", "CPS", "FIVEM", "FIVEM-TOKEN", "TS3", "MCPE", "ICMP", "OVH-UDP"];

    methodSelect.innerHTML = `
        <optgroup label="Layer 7 (Web / Apps)">
            ${l7.map(m => `<option value="${m}" ${m === 'GET' ? 'selected' : ''}>${m}</option>`).join('')}
        </optgroup>
        <optgroup label="Layer 4 (Transport / Network)">
            ${l4_normal.map(m => `<option value="${m}">${m}</option>`).join('')}
        </optgroup>
        <optgroup label="Layer 4 (Amplification)">
            ${l4_amp.map(m => `<option value="${m}">${m}</option>`).join('')}
        </optgroup>
    `;
    
    methodSelect.addEventListener('change', handleMethodChange);
    handleMethodChange(); // Initial check
}

// WebSocket Orchestration
const handleSocketData = (data) => {
    if (!data) return;
    if (data.type === 'batch' && Array.isArray(data.items)) {
        data.items.forEach(item => {
            const parsed = typeof item === 'string' ? JSON.parse(item) : item;
            handleSocketData(parsed);
        });
        return;
    }
    if (data.type === 'state_reconcile' || data.type === 'state_update') {
        const state = data.payload || {};
        const status = String(state.status || 'idle').toLowerCase();
        
        // Update global app state and UI deploy button
        if (status === 'running') {
            uiProMax.setAppState('running');
            if (engine.setIsRunning) engine.setIsRunning(true);
        } else if (status === 'starting') {
            uiProMax.setAppState('starting');
        } else if (status === 'stopping') {
            uiProMax.setAppState('stopping');
        } else {
            uiProMax.setAppState('idle');
            if (engine.setIsRunning) engine.setIsRunning(false);
        }
        
        const statusEl = document.getElementById('attack-status');
        if (statusEl) statusEl.textContent = status.toUpperCase();
        
        // Update stats counters
        const activeTasksEl = document.getElementById('active-tasks-count');
        if (activeTasksEl) {
            activeTasksEl.innerText = state.active_tasks || (status === 'running' ? 1 : 0);
        }
        
        // Update form fields if reconciled from SSOT (always sync if running/starting or on initial reconcile, or if field is empty)
        const forceSync = (data.type === 'state_reconcile') || (status === 'running') || (status === 'starting');
        if (state.target) {
            const targetEl = document.getElementById('target');
            if (targetEl && (forceSync || !targetEl.value)) targetEl.value = state.target;
        }
        if (state.method) {
            const methodEl = document.getElementById('method');
            if (methodEl && (forceSync || !methodEl.value)) methodEl.value = state.method;
        }
        if (state.threads) {
            const threadsEl = document.getElementById('threads');
            if (threadsEl && (forceSync || !threadsEl.value)) {
                threadsEl.value = state.threads;
                const slider = document.getElementById('threads-slider');
                if (slider) slider.value = state.threads;
            }
        }
        if (state.duration) {
            const durationEl = document.getElementById('duration');
            if (durationEl && (forceSync || !durationEl.value)) durationEl.value = state.duration;
        }
        if (state.rpc) {
            const rpcEl = document.getElementById('rpc');
            if (rpcEl && (forceSync || !rpcEl.value)) rpcEl.value = state.rpc;
        }
    } else if (data.type === 'log') {
        terminal.append(data.msg, data.level, data.task_id);
    } else if (data.type === 'telemetry') {
        telemetry.updateTask(data.task_id, data);
        const agg = telemetry.getAggregate();
        
        const statUpdates = [
            { id: 'current-rps',       text: helpers.formatHuman(agg['current-rps'] || 0) },
            { id: 'peak-rps',          text: helpers.formatHuman(agg['peak-rps'] || 0) },
            { id: 'current-bps',       text: helpers.formatBytes(agg['current-bps'] || 0) },
            { id: 'peak-bps',          text: `PEAK: ${helpers.formatBytes(agg['peak-bps'] || 0)}` },
            { id: 'current-latency',   text: `${(agg['current-latency'] || 0).toFixed(1)}ms` },
            { id: 'peak-latency',      text: `PEAK: ${(agg['peak-latency'] || 0).toFixed(1)}ms` },
            { id: 'current-threads',   text: helpers.formatHuman(agg['current-threads'] || 0) },
            { id: 'peak-threads',      text: `PEAK: ${helpers.formatHuman(agg['peak-threads'] || 0)}` },
            { id: 'active-tasks-count', text: String(agg['active-tasks-count'] || 0) },
        ];
        statUpdates.forEach(({ id, text }) => {
            const el = document.getElementById(id);
            if (el) el.innerText = text;
        });

        mainChart.update(agg);

        window.dispatchEvent(new CustomEvent('telemetry-update', {
            detail: agg
        }));
    }
};

const socket = new SocketManager('/ws', handleSocketData);

let map;
let mapMarker;

window.updateTacticalMap = async function(target) {
    if (!map || !target) return;
    try {
        const res = await fetch(`/api/recon/geo?target=${encodeURIComponent(target)}`);
        const data = await res.json();
        if (data.status === 'success' && data.lat && data.lon) {
            const latlng = [data.lat, data.lon];
            map.setView(latlng, 5, { animate: true, duration: 1.5 });
            
            if (mapMarker) {
                mapMarker.setLatLng(latlng);
            } else {
                // Create a custom pulsing cyan icon
                const icon = L.divIcon({
                    className: 'custom-div-icon',
                    html: `<div class="w-4 h-4 bg-primary rounded-full shadow-[0_0_15px_#06b6d4] status-pulse"></div>`,
                    iconSize: [16, 16],
                    iconAnchor: [8, 8]
                });
                mapMarker = L.marker(latlng, { icon }).addTo(map);
            }
            
            const infoText = `${data.country || 'Unknown'} - ${data.isp || 'Unknown ISP'} (${data.ip})`;
            document.getElementById('map-target-info').innerText = `LOCKED: ${infoText}`;
        }
    } catch (e) {
        console.error("Geo-IP fetch failed", e);
    }
};

function initMap() {
    const mapEl = document.getElementById('tactical-map');
    if (!mapEl) return;
    
    // Initialize map with dark theme tiles
    map = L.map('tactical-map', {
        zoomControl: false,
        attributionControl: false,
        dragging: false,
        scrollWheelZoom: false,
        doubleClickZoom: false
    }).setView([20, 0], 2);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
    }).addTo(map);
}

// Bootstrap
document.addEventListener('DOMContentLoaded', () => {
    socket.connect();
    uiProMax.init();
    tasks.startPolling();
    populateMethods();
    populateFileLists();
    initMap();
    showToast('MHDDoS PRO Operational', 'success');
});
