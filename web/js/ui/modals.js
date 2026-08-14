import { apiRequest } from '../core/api.js';
import { showToast } from './toast.js';
import { escapeHtml } from '../utils/helpers.js';

export function openToolsModal() {
    const modal = document.getElementById('tools-modal');
    const content = document.getElementById('tools-modal-content');
    if (!modal) return;
    modal.classList.remove('hidden');
    requestAnimationFrame(() => {
        modal.classList.remove('opacity-0');
        if (content) content.style.transform = 'translateY(0) scale(1)';
    });
    const mainTarget = document.getElementById('target')?.value;
    if (mainTarget) {
        const host = mainTarget.replace(/https?:\/\//, '').split('/')[0];
        const toolInput = document.getElementById('tool-target');
        if (toolInput) toolInput.value = host;
    }
}

export function closeToolsModal() {
    const modal = document.getElementById('tools-modal');
    const content = document.getElementById('tools-modal-content');
    if (!modal) return;
    modal.classList.add('opacity-0');
    if (content) content.style.transform = 'translateY(32px) scale(0.98)';
    setTimeout(() => modal.classList.add('hidden'), 300);
}

let currentTool = 'ping';
export function switchToolTab(tool) {
    currentTool = tool;
    document.querySelectorAll('.tool-tab').forEach(t => {
        t.classList.remove('bg-primary/20', 'text-primary');
        t.classList.add('text-on-surface-variant', 'hover:text-primary');
    });
    const active = document.getElementById(`tab-${tool}`);
    if (active) {
        active.classList.add('bg-primary/20', 'text-primary');
        active.classList.remove('text-on-surface-variant', 'hover:text-primary');
    }
}

export function switchAssetTab(tabId) {
    document.querySelectorAll('.asset-tab').forEach(t => {
        t.classList.remove('bg-primary/20', 'text-primary');
        t.classList.add('text-on-surface-variant', 'hover:text-primary');
    });
    const activeBtn = document.getElementById(`asset-tab-${tabId}`);
    if (activeBtn) {
        activeBtn.classList.add('bg-primary/20', 'text-primary');
        activeBtn.classList.remove('text-on-surface-variant', 'hover:text-primary');
    }

    ['proxies', 'files'].forEach(id => {
        const content = document.getElementById(`asset-content-${id}`);
        if (content) {
            if (id === tabId) content.classList.remove('hidden');
            else content.classList.add('hidden');
        }
    });
}

export async function executeTool() {
    const target = document.getElementById('tool-target')?.value;
    const resultArea = document.getElementById('tool-result');
    const btn = document.getElementById('tool-exec-btn');
    if (!target) return showToast("Target required.", "warning");

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">refresh</span> RUNNING';  
    }

    if (resultArea) {
        resultArea.innerHTML = `
            <div class="flex flex-col items-center justify-center py-10 opacity-40 animate-pulse">
                <span class="material-symbols-outlined text-4xl mb-4 text-primary">analytics</span>
                <div class="text-[10px] font-mono uppercase tracking-[0.3em]">Processing_Query...</div>
            </div>
        `;
    }

    try {
        const url = `/api/tools/${currentTool}?${currentTool === 'check' ? 'url' : 'host'}=${encodeURIComponent(target)}`;
        const res = await fetch(url);
        const data = await res.json();

        if (resultArea) {
            resultArea.innerHTML = '';
            if (data.status === 'error') {
                resultArea.innerHTML = `<div class="text-error p-4 border border-error/20 rounded bg-error/5 font-mono text-[11px]">[!] FAILED: ${data.message}</div>`;
            } else {
                renderToolResult(data, currentTool);
            }
        }
    } catch (e) {
        if (resultArea) resultArea.innerHTML = `<div class="text-error p-4 border border-error/20 rounded bg-error/5 font-mono text-[11px]">[!] NETWORK_ERR: ${e.message}</div>`;
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = 'Initiate';
        }
    }
}

function renderToolResult(data, tool) {
    const resultArea = document.getElementById('tool-result');
    if (!resultArea) return;

    const container = document.createElement('div');
    container.className = 'animate-reveal space-y-4';

    container.innerHTML = `
        <div class="flex items-center justify-between border-b border-outline-variant pb-2 mb-2">
            <div class="text-primary font-mono font-bold text-[10px] uppercase">> ${escapeHtml(tool)}_RESULT</div>
        </div>
        <pre class="text-[11px] font-mono leading-relaxed text-on-surface-variant overflow-x-auto whitespace-pre-wrap">${escapeHtml(JSON.stringify(data, null, 2))}</pre>
    `;
    resultArea.appendChild(container);
    resultArea.scrollTop = resultArea.scrollHeight;
}

export function openSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    requestAnimationFrame(() => modal.classList.remove('opacity-0'));
}

export function closeSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (!modal) return;
    modal.classList.add('opacity-0');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

export async function saveSettings() {
    const webhook = document.getElementById('discord_webhook')?.value;
    try {
        await apiRequest('/api/config/notifications', { discord_webhook_url: webhook });
        showToast("Settings synchronized.", 'success');
        closeSettingsModal();
    } catch(e) { showToast("Save failed.", "error"); }
}

let configSources = [];
export async function openConfigModal() {
    const modal = document.getElementById('config-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    requestAnimationFrame(() => modal.classList.remove('opacity-0'));

    const container = document.getElementById('config-sources-container');
    if (container) container.innerHTML = '<div class="text-center py-4"><span class="material-symbols-outlined animate-spin text-primary">refresh</span></div>';

    try {
        const res = await fetch('/api/config/proxies');
        const data = await res.json();
        if (data.status === 'success') renderConfigSources(data.providers);
    } catch (e) { console.error(e); }
}

export function closeConfigModal() {
    const modal = document.getElementById('config-modal');
    if (!modal) return;
    modal.classList.add('opacity-0');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

function renderConfigSources(providers) {
    configSources = providers;
    const container = document.getElementById('config-sources-container');
    if (!container) return;
    container.innerHTML = '';

    providers.forEach((p, index) => {
        const item = document.createElement('div');
        item.className = 'flex items-center gap-3 p-3 bg-black/40 rounded-lg border border-outline-variant group';
        item.innerHTML = `
            <select class="bg-surface border border-outline text-[10px] rounded px-2 py-1 outline-none w-24">       
                <option value="0" ${p.type === 0 ? 'selected' : ''}>ALL</option>
                <option value="1" ${p.type === 1 ? 'selected' : ''}>HTTP</option>
                <option value="4" ${p.type === 4 ? 'selected' : ''}>SOCKS4</option>
                <option value="5" ${p.type === 5 ? 'selected' : ''}>SOCKS5</option>
            </select>
            <input type="text" value="${escapeHtml(p.url)}" class="flex-1 bg-transparent border-b border-outline text-xs px-2 py-1 outline-none" />
            <button class="text-on-surface-variant hover:text-error opacity-0 group-hover:opacity-100 transition-opacity"><span class="material-symbols-outlined text-sm">delete</span></button>
        `;
        container.appendChild(item);

        const selects = item.querySelectorAll('select');
        const inputs = item.querySelectorAll('input');
        const buttons = item.querySelectorAll('button');

        selects[0].onchange = (e) => { configSources[index].type = parseInt(e.target.value); };
        inputs[0].onchange = (e) => { configSources[index].url = e.target.value; };
        buttons[0].onclick = () => { configSources.splice(index, 1); renderConfigSources(configSources); };     
    });
}

export function addConfigSource() {
    configSources.push({ type: 5, url: '', timeout: 10 });
    renderConfigSources(configSources);
}

export async function saveProxyConfig() {
    try {
        const data = await apiRequest('/api/config/proxies', { providers: configSources });
        if(data.status === 'success') {
            showToast("Assets updated.", "success");
            closeConfigModal();
        }
    } catch (e) { console.error(e); }
}

export function uploadAssetFile(fileType) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.txt';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const res = await fetch(`/api/files/upload/${fileType}`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast(data.message, 'success');
                if (window.populateFileLists) window.populateFileLists();
            } else {
                showToast(data.message || 'Upload failed', 'error');
            }
        } catch (err) {
            showToast("Upload failed due to network error", "error");
        }
    };
    input.click();
}

export async function deleteAssetFile(fileType, filename) {
    if(!confirm(`Delete ${filename}?`)) return;
    try {
        const res = await fetch(`/api/files/delete/${fileType}/${filename}`, { method: 'DELETE' });
        const data = await res.json();
        if(data.status === 'success') {
            showToast(data.message, "success");
            if (window.populateFileLists) window.populateFileLists();
        } else {
            showToast(data.message || "Delete failed", "error");
        }
    } catch(e) {
        showToast("Delete failed due to network error", "error");
    }
}

// ESC Key listener to close active modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (!document.getElementById('tools-modal')?.classList.contains('hidden')) {
            closeToolsModal();
        } else if (!document.getElementById('settings-modal')?.classList.contains('hidden')) {
            closeSettingsModal();
        } else if (!document.getElementById('config-modal')?.classList.contains('hidden')) {
            closeConfigModal();
        }
    }
});

