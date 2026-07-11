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
    
    // If port is specified, append it (only if not already there)
    if (port && !clean.includes(':', clean.indexOf('//') + 3)) {
        // Strip trailing slash if present
        if (clean.endsWith('/')) clean = clean.slice(0, -1);
        clean = `${clean}:${port}`;
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
                for (let t of res.active_tasks) {
                    await apiRequest('/api/attack/stop', { task_id: t.task_id });
                }
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
            
            if (window.updateTacticalMap) window.updateTacticalMap(target);
        }
    } catch (e) {
        showToast("Reconnaissance failed.", "error");
    }
}
