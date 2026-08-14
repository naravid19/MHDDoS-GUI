export function formatBytes(bytes) {
    if (bytes === 0) return '0 B/s';
    const k = 1024;
    const sizes = ['B/s', 'kB/s', 'MB/s', 'GB/s', 'TB/s'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatBytesTotal(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'kB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatHuman(num) {
    if (num == null || isNaN(num)) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(2) + 'm';
    if (num >= 1000) return (num / 1000).toFixed(2) + 'k';
    return num.toString();
}

export function formatDuration(seconds) {
    if (seconds === Infinity || isNaN(seconds)) return "UNLIMITED";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${h > 0 ? h + ':' : ''}${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

export function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}