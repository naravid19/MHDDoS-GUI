export function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    // Queue limit: max 3 toasts at once, remove oldest
    const currentToasts = container.querySelectorAll('.glass-panel-v2');
    if (currentToasts.length >= 3) {
        currentToasts[0].remove();
    }

    const toast = document.createElement('div');
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.className = `glass-panel-v2 p-4 rounded-lg border-l-4 flex items-center gap-4 min-w-[320px] shadow-2xl animate-reveal relative group overflow-hidden ${getTypeClass(type)}`;
    
    // Add holographic scanline to toast
    const scanline = document.createElement('div');
    scanline.className = 'absolute inset-0 scanline-v2 opacity-5 pointer-events-none';
    toast.appendChild(scanline);

    toast.innerHTML += `
        <div class="size-10 rounded bg-current/10 border border-current/20 flex items-center justify-center shrink-0">
            <span class="material-symbols-rounded text-xl">${getIcon(type)}</span>
        </div>
        <div class="flex flex-col gap-1">
            <div class="text-[10px] font-display font-black uppercase tracking-[0.2em] opacity-60">${type}</div>
            <div class="text-sm font-body font-semibold tracking-tight">${message}</div>
        </div>
        <button class="ml-auto opacity-40 hover:opacity-100 transition-opacity" aria-label="Dismiss notification" onclick="this.parentElement.remove()">
            <span class="material-symbols-rounded">close</span>
        </button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('opacity-0', 'translate-x-full');
            setTimeout(() => toast.remove(), 500);
        }
    }, 5000);
}

function getTypeClass(type) {
    switch (type) {
        case 'success': return 'text-primary border-primary bg-primary/5';
        case 'error': return 'text-danger border-danger bg-danger/5';
        case 'warning': return 'text-warning border-warning bg-warning/5';
        default: return 'text-info border-info bg-info/5';
    }
}

function getIcon(type) {
    switch (type) {
        case 'success': return 'verified_user';
        case 'error': return 'report';
        case 'warning': return 'warning';
        default: return 'info';
    }
}