import { apiRequest } from '../core/api.js';
import { showToast } from './toast.js';
import { escapeHtml } from '../utils/helpers.js';

// --- Helper: Gather current config parameters ---
function gatherCurrentParams() {
    return {
        target: document.getElementById('target')?.value || "",
        method: document.getElementById('method')?.value || "GET",
        threads: parseInt(document.getElementById('threads')?.value || '100'),
        duration: parseInt(document.getElementById('duration')?.value || '3600'),
        rpc: parseInt(document.getElementById('rpc')?.value || '100'),
        proxy_type: document.getElementById('proxy_type')?.value || 'SOCKS5',
        proxy_refresh: parseInt(document.getElementById('proxy_refresh')?.value || '0'),
        proxy_list: document.getElementById('proxy_list')?.value || '',
        reflector: document.getElementById('reflector')?.value || '',
        auto_harvest: false, // handled by proxy_list logic now
        smart_rpc: document.getElementById('smart_rpc')?.checked || false,
        autoscale: document.getElementById('autoscale')?.checked || false,
        evasion: document.getElementById('evasion')?.checked || false,
        distribute_to_workers: document.getElementById('distribute_to_workers')?.checked || false,
        debug_mode: document.getElementById('debug_mode')?.checked || false
    };
}

// --- Presets (Profiles) ---
export async function saveCurrentAsPreset() {
    const name = document.getElementById('preset-name').value;
    if (!name) return showToast("Profile name required.", "warning");
    
    const params = gatherCurrentParams();
    
    try {
        const data = await apiRequest('/api/presets', { name, params });
        if (data.status === 'success') {
            showToast(data.message, "success");
            document.getElementById('preset-name').value = '';
            refreshPresets();
        } else {
            showToast(data.message, "error");
        }
    } catch (e) {
        showToast("Failed to save profile.", "error");
    }
}

export async function deletePreset(name) {
    if (!confirm(`Delete profile '${name}'?`)) return;
    try {
        const res = await fetch(`/api/presets/${encodeURIComponent(name)}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(data.message, "success");
            refreshPresets();
        } else {
            showToast(data.message, "error");
        }
    } catch (e) {
        showToast("Failed to delete profile.", "error");
    }
}

export async function loadPreset(name) {
    try {
        const res = await fetch('/api/presets');
        const data = await res.json();
        if (data.status === 'success' && data.presets[name]) {
            const params = data.presets[name];
            
            // Map values back to DOM
            if (document.getElementById('target')) document.getElementById('target').value = params.target || "";
            if (document.getElementById('method')) document.getElementById('method').value = params.method || "GET";
            if (document.getElementById('threads')) document.getElementById('threads').value = params.threads || 100;
            if (document.getElementById('threads-slider')) document.getElementById('threads-slider').value = params.threads || 100;
            if (document.getElementById('duration')) document.getElementById('duration').value = params.duration || 3600;
            if (document.getElementById('rpc')) document.getElementById('rpc').value = params.rpc || 100;
            if (document.getElementById('proxy_type')) document.getElementById('proxy_type').value = params.proxy_type || "SOCKS5";
            if (document.getElementById('proxy_refresh')) document.getElementById('proxy_refresh').value = params.proxy_refresh || 0;
            if (document.getElementById('proxy_list')) document.getElementById('proxy_list').value = params.proxy_list || "";
            if (document.getElementById('reflector')) document.getElementById('reflector').value = params.reflector || "";
            
            // Boolean flags
            if (document.getElementById('smart_rpc')) document.getElementById('smart_rpc').checked = !!params.smart_rpc;
            if (document.getElementById('autoscale')) document.getElementById('autoscale').checked = !!params.autoscale;
            if (document.getElementById('evasion')) document.getElementById('evasion').checked = !!params.evasion;
            if (document.getElementById('debug_mode')) document.getElementById('debug_mode').checked = !!params.debug_mode;
            
            // Trigger UI updates
            if (window.handleMethodChange) window.handleMethodChange();
            
            showToast(`Profile '${name}' loaded.`, "success");
        }
    } catch (e) {
        showToast("Failed to load profile.", "error");
    }
}

export async function refreshPresets() {
    const container = document.getElementById('presets-container');
    if (!container) return;
    
    try {
        const res = await fetch('/api/presets');
        const data = await res.json();
        
        if (data.status === 'success') {
            const presets = data.presets || {};
            const keys = Object.keys(presets);
            
            if (keys.length === 0) {
                container.innerHTML = '<div class="text-center py-10 opacity-50 text-[10px] font-mono uppercase tracking-widest">No profiles saved.</div>';
                return;
            }
            
            container.innerHTML = keys.map(k => {
                const p = presets[k];
                return `
                    <div class="bg-black/40 border border-outline-variant rounded-xl p-4 group">
                        <div class="flex justify-between items-start mb-2">
                            <h4 class="font-bold text-primary truncate max-w-[200px]" title="${escapeHtml(k)}">${escapeHtml(k)}</h4>
                            <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onclick="loadPreset('${escapeHtml(k)}')" class="text-secondary hover:text-secondary-container" title="Load Profile"><span class="material-symbols-outlined text-[16px]">download</span></button>
                                <button onclick="deletePreset('${escapeHtml(k)}')" class="text-error hover:text-error-container" title="Delete Profile"><span class="material-symbols-outlined text-[16px]">delete</span></button>
                            </div>
                        </div>
                        <div class="text-[9px] font-mono text-on-surface-variant flex gap-3">
                            <span><span class="text-on-surface">M:</span> ${escapeHtml(p.method)}</span>
                            <span><span class="text-on-surface">T:</span> ${escapeHtml(p.threads)}</span>
                            <span><span class="text-on-surface">D:</span> ${escapeHtml(p.duration)}s</span>
                            ${p.proxy_refresh > 0 ? `<span><span class="text-on-surface">R:</span> ${escapeHtml(p.proxy_refresh)}min</span>` : ''}
                        </div>
                        <div class="text-[9px] font-mono text-on-surface-variant mt-1 truncate" title="${escapeHtml(p.target || 'None')}">
                            <span class="text-on-surface">TARGET:</span> ${escapeHtml(p.target || 'None')}
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        container.innerHTML = '<div class="text-center py-10 text-error text-[10px] font-mono uppercase tracking-widest">Error loading profiles.</div>';
    }
}

// --- Schedule (Automation) ---
export async function scheduleCurrentAttack() {
    const name = document.getElementById('schedule-name').value;
    const dateStr = document.getElementById('schedule-date').value;
    const timeStr = document.getElementById('schedule-time').value;
    
    if (!name) return showToast("Operation identifier required.", "warning");
    if (!dateStr || !timeStr) return showToast("Execution date and time required.", "warning");
    
    // Construct ISO string
    const dt = new Date(`${dateStr}T${timeStr}`);
    if (isNaN(dt.getTime())) return showToast("Invalid date/time format.", "error");
    
    const datetime_iso = dt.toISOString();
    const params = gatherCurrentParams();
    
    try {
        const data = await apiRequest('/api/schedule', { name, datetime_iso, params });
        if (data.status === 'success') {
            showToast(`Operation queued for ${dt.toLocaleString()}`, "success");
            document.getElementById('schedule-name').value = '';
            refreshSchedule();
        } else {
            showToast(data.message, "error");
        }
    } catch (e) {
        showToast("Failed to schedule operation.", "error");
    }
}

export async function deleteSchedule(taskId) {
    if (!confirm(`Cancel scheduled operation?`)) return;
    try {
        const res = await fetch(`/api/schedule/${taskId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') {
            showToast("Operation cancelled.", "success");
            refreshSchedule();
        } else {
            showToast(data.message, "error");
        }
    } catch (e) {
        showToast("Failed to cancel operation.", "error");
    }
}

export async function refreshSchedule() {
    const container = document.getElementById('schedule-container');
    if (!container) return;
    
    try {
        const res = await fetch('/api/schedule');
        const data = await res.json();
        
        if (data.status === 'success') {
            const schedule = data.schedule || {};
            const keys = Object.keys(schedule);
            
            if (keys.length === 0) {
                container.innerHTML = '<div class="text-center py-10 opacity-50 text-[10px] font-mono uppercase tracking-widest">No operations queued.</div>';
                return;
            }
            
            const now = new Date();
            
            container.innerHTML = keys.map(k => {
                const s = schedule[k];
                const execTime = new Date(s.datetime_iso);
                const isPast = execTime < now;
                const statusColor = isPast ? 'text-on-surface-variant' : 'text-primary';
                const statusText = isPast ? 'EXECUTED/MISSED' : 'PENDING';
                
                return `
                    <div class="bg-black/40 border ${isPast ? 'border-outline-variant/50' : 'border-primary/30'} rounded-xl p-4">
                        <div class="flex justify-between items-start mb-2">
                            <div>
                                <h4 class="font-bold text-on-surface" title="${escapeHtml(s.name)}">${escapeHtml(s.name)}</h4>
                                <div class="text-[9px] font-mono font-black ${statusColor} tracking-widest uppercase mt-0.5">${statusText}</div>
                            </div>
                            <button onclick="deleteSchedule('${escapeHtml(k)}')" class="text-error hover:text-error-container" title="Abort Operation"><span class="material-symbols-outlined text-[16px]">cancel</span></button>
                        </div>
                        <div class="text-[10px] font-mono text-on-surface-variant flex gap-2 items-center bg-black/50 px-2 py-1 rounded">
                            <span class="material-symbols-outlined text-[12px]">schedule</span>
                            ${execTime.toLocaleString()}
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        container.innerHTML = '<div class="text-center py-10 text-error text-[10px] font-mono uppercase tracking-widest">Error loading queue.</div>';
    }
}
