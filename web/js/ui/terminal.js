/**
 * MHDDoS PRO - Terminal UI Component
 * Handles the display and management of real-time log entries with level filtering.
 */
import { escapeHtml } from '../utils/helpers.js';

export class TerminalUI {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.autoScroll = true;
        this.logLevel = 'INFO_STANDARD';
        
        this.levels = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'SUCCESS': 3,
            'ERROR': 4
        };

        this.filterMap = {
            'DEBUG_VERBOSE': 0,
            'INFO_STANDARD': 1,
            'WARNING_CRIT': 2,
            'SUCCESS_ONLY': 3,
            'ERROR_ONLY': 4
        };
    }

    append(msg, level = 'INFO', taskId = null) {
        if (!this.container) return;
        
        const numericLevel = this.levels[level] ?? 1;
        const threshold = this.filterMap[this.logLevel] ?? 1;

        const entry = document.createElement('div');
        entry.className = `terminal-entry animate-reveal flex flex-col gap-1 p-2 rounded border-l-2 transition-all hover:bg-white/5 group ${this.getLevelClass(level)}`;
        entry.dataset.numericLevel = String(numericLevel);

        if (numericLevel < threshold) {
            entry.classList.add('hidden');
        } else {
            entry.classList.remove('hidden');
        }

        const timestamp = new Date().toLocaleTimeString('en-GB', { hour12: false });

        entry.innerHTML = `
            <div class="flex items-center gap-3">
                <span class="text-[9px] font-mono opacity-40 shrink-0 select-none">${escapeHtml(timestamp)}</span>
                <span class="text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded bg-current/10 border border-current/20 shrink-0">${escapeHtml(level)}</span>
                <span class="font-mono text-[12px] leading-relaxed break-all flex-grow">${escapeHtml(msg)}</span>
                ${taskId ? `<span class="text-[8px] font-mono opacity-30 group-hover:opacity-100 transition-opacity bg-white/10 px-1 rounded uppercase tracking-tighter shrink-0">ID:${escapeHtml(String(taskId).substring(0,6))}</span>` : ''}     
            </div>
        `;

        this.container.appendChild(entry);

        if (this.container.childNodes.length > 500) {
            this.container.removeChild(this.container.firstChild);
        }

        if (this.autoScroll) {
            this.container.scrollTop = this.container.scrollHeight;
        }
    }

    getLevelClass(level) {
        switch(level) {
            case 'SUCCESS': return 'text-primary border-primary/40';
            case 'ERROR': return 'text-error border-error/40';
            case 'WARNING': return 'text-warning border-warning/40';
            case 'DEBUG': return 'text-slate-500 border-slate-700';
            default: return 'text-on-surface-variant border-outline-variant';
        }
    }

    toggleAutoScroll() {
        this.autoScroll = !this.autoScroll;
        return this.autoScroll;
    }

    clear() {
        if (!this.container) return;
        this.container.innerHTML = '';
        this.append("Logs cleared.", "SUCCESS");
    }

    async copy() {
        if (!this.container) return;
        const entries = this.container.querySelectorAll('.terminal-entry');
        const text = Array.from(entries).map(e => {
            const time = e.querySelector('span:nth-child(1)')?.innerText || '';
            const lvl = e.querySelector('span:nth-child(2)')?.innerText || '';
            const m = e.querySelector('span:nth-child(3)')?.innerText || '';
            return `[${time}] [${lvl}] ${m}`;
        }).join('\n');
        await navigator.clipboard.writeText(text);
    }

    setLevel(level) {
        this.logLevel = level;
        const threshold = this.filterMap[this.logLevel] ?? 1;
        
        if (this.container) {
            const entries = this.container.querySelectorAll('.terminal-entry');
            entries.forEach(entry => {
                const numLvl = parseInt(entry.dataset.numericLevel ?? '1', 10);
                if (numLvl < threshold) {
                    entry.classList.add('hidden');
                } else {
                    entry.classList.remove('hidden');
                }
            });
        }
        
        this.append(`Log filtration set to: ${level}`, "INFO");
    }
}

export function setLogLevel(level) {
    if (window._terminal) window._terminal.setLevel(level);
}
