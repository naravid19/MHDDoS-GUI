import { apiRequest } from '../core/api.js';
import { formatBytes, escapeHtml } from '../utils/helpers.js';

let historyPage = 1;

export function switchMainView(view) {
    const views = ['dashboard', 'history', 'config'];
    views.forEach(v => {
        const el = document.getElementById(`view-${v}`);
        if (el) el.classList.add('hidden');

        const tab = document.getElementById(`tab-nav-${v}`);
        if (tab) {
            tab.classList.remove('bg-primary/10', 'text-primary', 'border-primary');
            tab.classList.add('text-on-surface-variant', 'border-transparent');
        }
    });

    const activeView = document.getElementById(`view-${view}`);
    if (activeView) activeView.classList.remove('hidden');

    const activeTab = document.getElementById(`tab-nav-${view}`);
    if (activeTab) {
        activeTab.classList.add('bg-primary/10', 'text-primary', 'border-primary');
        activeTab.classList.remove('text-on-surface-variant', 'border-transparent');
    }

    if (view === 'history') {
        refreshHistory();
    } else if (view === 'config') {
        if (window.refreshPresets) window.refreshPresets();
        if (window.refreshSchedule) window.refreshSchedule();
    }
}

export async function refreshHistory() {
    const tbody = document.getElementById('history-table-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5" class="py-12 text-center"><span class="material-symbols-rounded animate-spin text-primary text-2xl">refresh</span></td></tr>';
    try {
        const res = await fetch(`/api/history/sessions?page=${historyPage}&limit=10&t=${Date.now()}`);
        const data = await res.json();
        if (data.status === 'success') {
            renderHistoryTable(data);
        } else {
            tbody.innerHTML = `<tr><td colspan="5" class="py-12 text-center text-danger">Error: ${data.message || 'Unknown error'}</td></tr>`;
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" class="py-12 text-center text-danger">Connection Error: ${e.message}</td></tr>`;
    }
}

function renderHistoryTable(data) {
    const tbody = document.getElementById('history-table-body');
    const totalRecords = document.getElementById('history-total-records');
    const pageIndicator = document.getElementById('history-page-indicator');
    
    if (totalRecords) totalRecords.textContent = `Total: ${data.total} operations`;
    if (pageIndicator) pageIndicator.textContent = `PAGE ${historyPage} / ${data.pages || 1}`; 

    if (!tbody) return;

    if (data.sessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="py-12 text-center text-slate-700 italic uppercase tracking-[0.2em] text-[9px] font-black">No operations recorded.</td></tr>';
        return;
    }

    tbody.innerHTML = data.sessions.map(s => `
        <tr class="hover:bg-surface-container-high transition-colors border-b border-outline-variant last:border-0 cursor-pointer">
            <td class="py-3 px-6 text-on-surface-variant font-mono text-[9px]">${escapeHtml((s.start_time || '').replace('T', ' ').substring(0, 19))}</td>
            <td class="py-3 px-6 text-on-surface font-mono font-bold truncate max-w-[200px]" title="${escapeHtml(s.target)}">${escapeHtml(s.target)}</td>        
            <td class="py-3 px-6 text-primary font-black text-[9px] tracking-widest">${escapeHtml(s.method)}</td>
            <td class="py-3 px-6 text-right font-mono text-on-surface">
                <div>${(s.peak_pps || 0).toLocaleString()} PPS</div>
                <div class="text-[8px] text-on-surface-variant">${formatBytes(s.peak_bps || 0)}</div>
            </td>
            <td class="py-3 px-6 text-center"><span class="px-2 py-0.5 rounded-md border border-outline-variant text-[8px] font-black uppercase tracking-widest">${escapeHtml(s.exit_status)}</span></td>
        </tr>
    `).join('');
}

export function changeHistoryPage(delta) {
    historyPage += delta;
    if (historyPage < 1) historyPage = 1;
    refreshHistory();
}
