import { apiRequest } from '../core/api.js';
import { showToast } from './toast.js';
import { escapeHtml, formatBytes, formatHuman } from '../utils/helpers.js';
import { telemetry } from '../core/telemetry.js';

export class TaskManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.interval = null;
        this.currentTaskIds = [];
        
        window.addEventListener('telemetry-update', () => {
            this.updateStats();
        });
    }

    startPolling() {
        this.refresh();
        this.interval = setInterval(() => this.refresh(), 2000);
    }

    stopPolling() {
        if (this.interval) clearInterval(this.interval);
    }

    async refresh() {
        try {
            const data = await apiRequest('/api/attack/status');
            if (data.status === 'success') {
                const newTaskIds = data.active_tasks.map(t => t.task_id).join(',');
                const oldTaskIds = this.currentTaskIds.join(',');
                
                if (newTaskIds !== oldTaskIds) {
                    this.render(data.active_tasks);
                    this.currentTaskIds = data.active_tasks.map(t => t.task_id);
                }
                
                this.updateStats();
                
                const badge = document.getElementById('active-tasks-count');
                if (badge) badge.innerText = data.active_tasks.length;
            }
        } catch (e) {
            console.error("Task refresh failed", e);
        }
    }

    updateStats() {
        if (!this.currentTaskIds || this.currentTaskIds.length === 0) return;
        
        for (const taskId of this.currentTaskIds) {
            const metrics = telemetry.taskMetrics[taskId] || {};
            const rps = metrics.rps || 0;
            const bps = metrics.bps || 0;
            
            const rpsEl = document.getElementById(`task-rps-${taskId}`);
            const bpsEl = document.getElementById(`task-bps-${taskId}`);
            
            if (rpsEl) rpsEl.innerHTML = `${formatHuman(rps)} <span class="text-[9px] font-normal text-on-surface-variant">RPS</span>`;
            if (bpsEl) bpsEl.innerHTML = `${formatBytes(bps)}<span class="text-[9px] font-normal text-on-surface-variant">/s</span>`;
        }
    }

    render(tasks) {
        if (!this.container) return;

        if (!tasks || tasks.length === 0) {
            this.container.innerHTML = `
                <div class="flex flex-col items-center justify-center py-12 col-span-full border border-dashed border-outline-variant/50 rounded-2xl bg-black/10">
                    <span class="material-symbols-outlined text-3xl mb-3 text-on-surface-variant/30">radar</span>
                    <p class="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">No Active Deployments</p>
                </div>
            `;
            return;
        }

        this.container.innerHTML = tasks.map(t => `
            <div class="glass-card border border-outline-variant/30 rounded-2xl p-5 flex flex-col gap-4 group hover:border-primary/50 transition-all relative overflow-hidden bg-gradient-to-br from-surface-container-high/40 to-black/40 shadow-lg">
                <div class="absolute top-0 left-0 w-1 h-full bg-primary/80 group-hover:bg-primary transition-colors"></div>
                
                <div class="flex justify-between items-start pl-2">
                    <div class="space-y-1 overflow-hidden pr-2">
                        <div class="text-xs font-bold text-on-surface truncate max-w-[200px]" title="${escapeHtml(t.target)}">
                            ${escapeHtml(t.target)}
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-[9px] font-black px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 uppercase tracking-widest">${escapeHtml(t.method)}</span>
                            <span class="text-[9px] font-mono text-on-surface-variant/60 uppercase">ID:${escapeHtml(String(t.task_id || '').substring(0, 8))}</span>
                        </div>
                    </div>
                    <button onclick="stopTask('${escapeHtml(t.task_id || '')}')" class="text-on-surface-variant hover:text-error bg-surface-container-high hover:bg-error/10 border border-outline-variant hover:border-error/30 p-1.5 rounded-lg transition-all active:scale-95 shrink-0" title="Terminate Task">
                        <span class="material-symbols-outlined text-[18px]">stop</span>
                    </button>
                </div>
                
                <div class="grid grid-cols-2 gap-3 pl-2">
                    <div class="bg-black/30 p-2.5 rounded-xl border border-outline-variant/30 shadow-inner">
                        <p class="text-[8px] font-mono text-on-surface-variant/70 uppercase tracking-widest mb-1">Velocity</p>
                        <p id="task-rps-${escapeHtml(t.task_id || '')}" class="text-xs font-mono font-bold text-primary">0 <span class="text-[9px] font-normal text-on-surface-variant">RPS</span></p>
                    </div>
                    <div class="bg-black/30 p-2.5 rounded-xl border border-outline-variant/30 shadow-inner">
                        <p class="text-[8px] font-mono text-on-surface-variant/70 uppercase tracking-widest mb-1">Throughput</p>
                        <p id="task-bps-${escapeHtml(t.task_id || '')}" class="text-xs font-mono font-bold text-on-surface">0 B/s</p>
                    </div>
                </div>
                
                <div class="space-y-2 pl-2 mt-1">
                    <div class="flex justify-between text-[9px] font-mono text-on-surface-variant uppercase tracking-widest">
                        <span>Threads: <span class="text-on-surface font-bold">${t.threads}</span></span>
                        <span>RPC: <span class="text-on-surface font-bold">${t.rpc}</span></span>
                    </div>
                    <div class="h-1 w-full bg-black/50 rounded-full overflow-hidden shadow-inner">
                        <div class="h-full bg-primary/80 animate-pulse relative" style="width: 100%"></div>
                    </div>
                </div>
            </div>
        `).join('');
    }
}

window.stopTask = async (taskId) => {
    try {
        const data = await apiRequest('/api/attack/stop', { task_id: taskId });
        if (data.status === 'success') {
            showToast("Task termination sequence initiated.", "success");
        }
    } catch (e) {
        showToast("Termination failed.", "error");
    }
};
