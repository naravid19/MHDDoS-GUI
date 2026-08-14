import { apiRequest } from '../core/api.js';
import { showToast } from '../ui/toast.js';
import { uiProMax } from '../ui/ui-pro-max.js';

let isRunning = false;

export function setIsRunning(val) {
    isRunning = Boolean(val);
}

/**
 * Normalizes a URL or IP to ensure it's in the format start.py expects.
 */
function normalizeTarget(target, port, method) {
    if (!target) return "";
    let clean = target.trim();
    
    // Auto-detect if we should add http://
    const isLayer7 = !['TCP', 'UDP', 'SYN', 'ICMP', 'VSE', 'MINECRAFT', 'MCBOT', 'CONNECTION', 'CPS', 'FIVEM', 'FIVEM-TOKEN', 'TS3', 'MCPE', 'OVH-UDP'].includes(method);
    
    if (isLayer7 && !clean.startsWith('http')) {
        clean = 'http://' + clean;
    }
    
    if (port) {
        try {
            if (clean.startsWith('http://') || clean.startsWith('https://')) {
                const parsed = new URL(clean);
                if (!parsed.port) {
                    parsed.port = port;
                }
                return parsed.toString();
            }
        } catch (e) {
            // Fallback for non-standard formats
        }
        if (!clean.includes(':', clean.indexOf('//') + 3)) {
            if (clean.endsWith('/')) clean = clean.slice(0, -1);
            clean = `${clean}:${port}`;
        }
    }
    
    return clean;
}

export async function handleMainAction() {
    if (isRunning) {
        uiProMax.setAppState('stopping');
        showToast("Stopping all active deployments...", "warning");
        try {
            const res = await apiRequest('/api/attack/status');
            if (res.status === 'success' && res.active_tasks) {
                const stopPromises = res.active_tasks.map(t => apiRequest('/api/attack/stop', { task_id: t.task_id }));
                await Promise.all(stopPromises);
            }
            isRunning = false;
            uiProMax.setAppState('idle');
            showToast("Global sequence terminated.", "success");
        } catch (e) {
            showToast("Termination failed.", "error");
            uiProMax.setAppState('running');
        }
        return;
    }

    const rawTarget = document.getElementById('target').value;
    const method = document.getElementById('method').value;
    const port = document.getElementById('port')?.value;
    
    const target = normalizeTarget(rawTarget, port, method);
    const threads = parseInt(document.getElementById('threads')?.value || '100');
    const duration = parseInt(document.getElementById('duration')?.value || '3600');
    const rpc = parseInt(document.getElementById('rpc')?.value || '100');
    
    // Advanced Parameters
    const proxy_type = document.getElementById('proxy_type')?.value || 'SOCKS5';
    const proxy_refresh = parseInt(document.getElementById('proxy_refresh')?.value || '0');
    const proxy_list = document.getElementById('proxy_list')?.value || '';
    const reflector = document.getElementById('reflector')?.value || '';
    
    // Boolean Flags
    const auto_harvest = false; // handled by proxy_list === 'AUTO'
    const smart_rpc = document.getElementById('smart_rpc')?.checked || false;
    const autoscale = document.getElementById('autoscale')?.checked || false;
    const evasion = document.getElementById('evasion')?.checked || false;
    const distribute_to_workers = false; // not exposed in current UI
    const debug_mode = document.getElementById('debug_mode')?.checked || false;

    if (!rawTarget) return showToast("Target vector required.", "warning");

    uiProMax.setAppState('starting');
    showToast(`Initiating ${method} sequence...`, "info");

    try {
        const payload = {
            target,
            method,
            threads,
            duration,
            rpc,
            proxy_type,
            proxy_refresh,
            proxy_list,
            reflector,
            auto_harvest,
            smart_rpc,
            autoscale,
            evasion,
            distribute_to_workers,
            debug_mode
        };

        const data = await apiRequest('/api/attack/start', payload);
        if (data.status === 'success') {
            isRunning = true;
            uiProMax.setAppState('running');
            showToast("Attack sequence authorized.", "success");
            saveFormSettings();
            if (window.updateTacticalMap) window.updateTacticalMap(target);
        } else {
            isRunning = false;
            uiProMax.setAppState('idle');
            showToast(data.message || "Deployment rejected.", "error");
        }
    } catch (e) {
        isRunning = false;
        uiProMax.setAppState('idle');
        showToast("Backend connection failed.", "error");
    }
}

export async function analyzeTarget() {
    const target = document.getElementById('target').value;
    if (!target) return showToast("Target required for radar scan.", "warning");

    showToast("Analyzing infrastructure...", "info");
    try {
        const data = await apiRequest('/api/recon/analyze', { target });
        if (data.status === 'success') {
            document.getElementById('method').value = data.recommendation;
            showToast(`Target identified. Recommended: ${data.recommendation}`, "success");
            
            // Auto-fill port if standard
            if (data.status_code === 443) document.getElementById('port').value = "443";
            else if (data.status_code === 80) document.getElementById('port').value = "80";
            
            saveFormSettings();
            if (window.updateTacticalMap) window.updateTacticalMap(target);
        }
    } catch (e) {
        showToast("Reconnaissance failed.", "error");
    }
}

/** LocalStorage key for form persistence */
const STORAGE_KEY = 'mhddos_gui_params';

/** Saves current form inputs into localStorage */
export function saveFormSettings() {
    try {
        const params = {
            target:        document.getElementById('target')?.value || '',
            port:          document.getElementById('port')?.value || '',
            method:        document.getElementById('method')?.value || 'GET',
            threads:       document.getElementById('threads')?.value || '100',
            duration:      document.getElementById('duration')?.value || '3600',
            rpc:           document.getElementById('rpc')?.value || '100',
            proxy_type:    document.getElementById('proxy_type')?.value || 'SOCKS5',
            proxy_refresh: document.getElementById('proxy_refresh')?.value || '0',
            proxy_list:    document.getElementById('proxy_list')?.value || '',
            reflector:     document.getElementById('reflector')?.value || '',
            smart_rpc:     document.getElementById('smart_rpc')?.checked || false,
            autoscale:     document.getElementById('autoscale')?.checked || false,
            evasion:       document.getElementById('evasion')?.checked || false,
            debug_mode:    document.getElementById('debug_mode')?.checked || false,
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(params));
    } catch (e) {
        console.warn('Failed to save settings to localStorage', e);
    }
}

/** Restores form inputs from localStorage if present */
export function restoreFormSettings() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const params = JSON.parse(raw);

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el && val != null && val !== '') el.value = val;
        };
        const setCheck = (id, val) => {
            const el = document.getElementById(id);
            if (el && val != null) el.checked = Boolean(val);
        };

        setVal('target',        params.target);
        setVal('port',          params.port);
        setVal('method',        params.method);
        setVal('threads',       params.threads);
        const slider = document.getElementById('threads-slider');
        if (slider && params.threads) slider.value = params.threads;
        setVal('duration',      params.duration);
        setVal('rpc',           params.rpc);
        setVal('proxy_type',    params.proxy_type);
        setVal('proxy_refresh', params.proxy_refresh);
        setVal('proxy_list',    params.proxy_list);
        setVal('reflector',     params.reflector);

        setCheck('smart_rpc',  params.smart_rpc);
        setCheck('autoscale',  params.autoscale);
        setCheck('evasion',    params.evasion);
        setCheck('debug_mode', params.debug_mode);
    } catch (e) {
        console.warn('Failed to restore settings from localStorage', e);
    }
}

/** Attach auto-save listeners on all form fields */
export function setupFormAutoSave() {
    restoreFormSettings();

    const textIds = ['target', 'port', 'method', 'threads', 'duration', 'rpc', 'proxy_type', 'proxy_refresh', 'proxy_list', 'reflector'];
    textIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', saveFormSettings);
    });

    const checkIds = ['smart_rpc', 'autoscale', 'evasion', 'debug_mode'];
    checkIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', saveFormSettings);
    });
}

