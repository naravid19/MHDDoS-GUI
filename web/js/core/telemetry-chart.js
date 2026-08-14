/**
 * MHDDoS PRO - Telemetry Charting Logic
 * Handles real-time visualization of network metrics using Chart.js
 */

/** Format raw bytes-per-second into compact human-readable string */
function fmtBps(val) {
    if (val === 0 || !val) return '0';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.min(Math.floor(Math.log(val) / Math.log(k)), sizes.length - 1);
    return (val / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
}

/** Format raw packets/requests-per-second into compact string */
function fmtRps(val) {
    if (val >= 1_000_000) return (val / 1_000_000).toFixed(1) + 'M';
    if (val >= 1_000)     return (val / 1_000).toFixed(1) + 'k';
    return Math.round(val).toString();
}

/** Map timeframe label -> number of 1-second data points to display */
const TIMEFRAME_POINTS = {
    '1M':  60,
    '5M':  300,
    '30M': 1800,
    '1H':  3600,
    '3H':  10800,
    '6H':  21600,
    '12H': 43200,
    '1D':  86400,
};

export class TelemetryChart {
    constructor(canvasId) {
        this.ctx = document.getElementById(canvasId)?.getContext('2d');
        if (!this.ctx) return;

        // Rolling history — keeps up to 24 h of 1-second samples
        this.MAX_HISTORY = 86400;
        this.history = { rps: [], bps: [] };

        // How many points the chart window shows (default 1 H)
        this.windowSize = TIMEFRAME_POINTS['1H'];

        this.chart = new Chart(this.ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'RPS',
                        data: [],
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.1)',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'BPS',
                        data: [],
                        borderColor: '#94a3b8',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                if (ctx.datasetIndex === 0) return ` RPS: ${fmtRps(ctx.raw)}`;
                                return ` BPS: ${fmtBps(ctx.raw)}/s`;
                            }
                        }
                    }
                },
                scales: {
                    x: { display: false },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: {
                            color: '#64748b',
                            font: { size: 9 },
                            maxTicksLimit: 5,
                            callback: (v) => fmtRps(v)
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: {
                            color: '#64748b',
                            font: { size: 9 },
                            maxTicksLimit: 5,
                            callback: (v) => fmtBps(v)
                        }
                    }
                }
            }
        });
    }

    /** Append a new data point and redraw the chart window */
    update(agg) {
        if (!this.chart) return;

        this.history.rps.push(agg['current-rps'] || 0);
        this.history.bps.push(agg['current-bps'] || 0);

        // Trim history older than MAX_HISTORY to avoid unbounded growth
        if (this.history.rps.length > this.MAX_HISTORY) {
            this.history.rps.shift();
            this.history.bps.shift();
        }

        this._redraw();
    }

    /** Load telemetry history from backend DB API */
    async loadHistory(timeframeSec = 86400) {
        try {
            const res = await fetch(`/api/telemetry/history?timeframe=${timeframeSec}`);
            if (!res.ok) return;
            const data = await res.json();
            const list = data.history || data.data || [];
            if (Array.isArray(list) && list.length > 0) {
                this.history.rps = list.map(item => Number(item.rps) || 0);
                this.history.bps = list.map(item => Number(item.bps) || 0);
            }
            this._redraw();
        } catch (e) {
            console.error("Failed to load telemetry history", e);
        }
    }

    /** Switch the visible window to a new timeframe label (e.g. '5M', '1H') */
    setTimeframe(label) {
        const points = TIMEFRAME_POINTS[label] ?? TIMEFRAME_POINTS['1H'];
        this.windowSize = points;
        this.loadHistory(points);
    }

    /** Slice history to windowSize and update chart datasets */
    _redraw() {
        if (!this.chart) return;
        const start = Math.max(0, this.history.rps.length - this.windowSize);
        const rpsSlice = this.history.rps.slice(start);
        const bpsSlice = this.history.bps.slice(start);

        const displayRps = rpsSlice.length > 0 ? rpsSlice : [0, 0];
        const displayBps = bpsSlice.length > 0 ? bpsSlice : [0, 0];
        const labels   = Array(displayRps.length).fill('');

        this.chart.data.labels         = labels;
        this.chart.data.datasets[0].data = displayRps;
        this.chart.data.datasets[1].data = displayBps;
        this.chart.update('none'); // 'none' = skip animation for perf
    }
}
