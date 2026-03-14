const term = document.getElementById('terminal-content');
        const STATE = { IDLE: 'idle', STARTING: 'starting', RUNNING: 'running', STOPPING: 'stopping' };
        let currentAppState = STATE.IDLE;
        let ws = null;
        let currentLogFilter = 'ALL';
        let currentTaskFilter = null;
        const LOG_LEVELS = { 'DEBUG': 0, 'INFO': 1, 'ERROR': 2 };
        let currentLogLevel = localStorage.getItem('mhddos_log_level') || 'INFO';

        // --- Log Isolation ---
        function setTaskFilter(taskId) {
            if (currentTaskFilter === taskId) {
                currentTaskFilter = null;
                showToast("Terminal isolation disabled. Showing all traffic.", 'info');
            } else {
                currentTaskFilter = taskId;
                showToast(`Terminal isolated to Task ${taskId.toUpperCase()}.`, 'success');
            }
            refreshLogVisibility();
            refreshTasks(); // Update UI to show which one is isolated
        }

        // --- Toast System ---
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            const icons = {
                'info': 'info',
                'success': 'check_circle',
                'warning': 'warning',
                'error': 'error'
            };
            const colors = {
                'info': 'bg-slate-900 border-secondary/30 text-secondary',
                'success': 'bg-slate-900 border-primary/30 text-primary',
                'warning': 'bg-slate-900 border-warning/30 text-warning',
                'error': 'bg-slate-900 border-danger/30 text-danger'
            };
            
            toast.className = `toast glass-card border ${colors[type]} p-4 rounded-2xl flex items-center gap-4 shadow-2xl`;
            toast.innerHTML = `
                <div class="size-10 rounded-xl bg-white/5 flex items-center justify-center">
                    <span class="material-symbols-rounded">${icons[type]}</span>
                </div>
                <div class="flex-1">
                    <div class="text-[10px] font-black uppercase tracking-widest opacity-50">${type}_signal</div>
                    <div class="text-xs font-bold text-white">${message}</div>
                </div>
            `;
            
            container.appendChild(toast);
            setTimeout(() => {
                toast.classList.add('toast-exit');
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }

        // --- Theme Management ---
        function setTheme(theme) {
            document.body.dataset.theme = theme;
            localStorage.setItem('mhddos_theme', theme);
            showToast(`Tactical interface updated to ${theme.toUpperCase()} mode.`, 'info');
        }

        // --- Keyboard Shortcuts ---
        window.addEventListener('keydown', (e) => {
            if (e.altKey && e.key === 'd') {
                e.preventDefault();
                startAttack();
            }
            if (e.altKey && e.key === 's') {
                e.preventDefault();
                stopAllAttacks();
            }
            if (e.key === 'Escape') {
                closeToolsModal();
                closeConfigModal();
            }
        });

        // --- Sidebar Module Toggles ---
        function toggleModule(id) {
            const content = document.getElementById(id);
            const icon = document.getElementById(id + '-icon');
            if (content.classList.contains('collapsed')) {
                content.classList.remove('collapsed');
                content.style.maxHeight = content.scrollHeight + 'px';
                if(icon) icon.style.transform = 'rotate(0deg)';
            } else {
                content.style.maxHeight = content.scrollHeight + 'px';
                setTimeout(() => {
                    content.classList.add('collapsed');
                    if(icon) icon.style.transform = 'rotate(180deg)';
                }, 10);
            }
        }

        // Initialize modules
        document.addEventListener('DOMContentLoaded', () => {
            ['mod-target', 'mod-payload'].forEach(id => {
                const el = document.getElementById(id);
                if(el) el.style.maxHeight = el.scrollHeight + 'px';
            });
        });

        // --- UI State Management ---
        function setAppState(state) {
            currentAppState = state;
            document.body.dataset.appState = state;
            const startBtn = document.getElementById('start-btn');
            const stopBtn = document.getElementById('stop-btn');
            const loader = document.getElementById('action-loader');
            // Select all inputs except specific buttons we manage manually
            const inputs = document.querySelectorAll('aside input, aside select, aside button:not(#stop-btn):not(#start-btn)');

            switch(state) {
                case STATE.IDLE:
                    startBtn.classList.remove('hidden');
                    stopBtn.classList.add('hidden');
                    loader.classList.add('hidden');
                    startBtn.disabled = false;
                    inputs.forEach(i => { i.disabled = false; i.style.opacity = "1"; });
                    document.getElementById('header-status-text').textContent = "SYSTEM_READY";
                    document.getElementById('header-status-text').className = "text-xs font-mono font-bold text-primary";
                    break;
                case STATE.STARTING:
                    startBtn.classList.add('hidden');
                    stopBtn.classList.add('hidden');
                    loader.classList.remove('hidden');
                    inputs.forEach(i => { i.disabled = true; i.style.opacity = "0.5"; });
                    break;
                case STATE.RUNNING:
                    startBtn.classList.remove('hidden'); // Ensure we can start MORE tasks
                    startBtn.disabled = false;
                    stopBtn.classList.remove('hidden'); // Show abort button to stop all tasks
                    loader.classList.add('hidden');
                    stopBtn.disabled = false;
                    inputs.forEach(i => { i.disabled = false; i.style.opacity = "1"; }); // Ensure inputs are usable again
                    document.getElementById('header-status-text').textContent = "SEQUENCE_ACTIVE";
                    document.getElementById('header-status-text').className = "text-xs font-mono font-bold text-warning animate-pulse";
                    break;
                case STATE.STOPPING:
                    startBtn.classList.add('hidden');
                    stopBtn.classList.remove('hidden');
                    stopBtn.disabled = true;
                    loader.classList.add('hidden');
                    inputs.forEach(i => { i.disabled = true; i.style.opacity = "0.5"; });
                    break;
            }
        }

        // --- Maps ---
        let map = null;
        let marker = null;

        function initMap(lat = 0, lon = 0) {
            if (map) map.remove();
            map = L.map('tactical-map', {
                center: [lat, lon],
                zoom: 3,
                zoomControl: false,
                attributionControl: false
            });
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                maxZoom: 19
            }).addTo(map);
            if(lat !== 0) marker = L.circleMarker([lat, lon], { color: '#10b981', radius: 8, fillOpacity: 0.6 }).addTo(map);
        }

        // --- Time-Series Analytics & Charts ---
        let historyBuffer = [];
        try {
            const stored = localStorage.getItem('mhddos_telemetry');
            if (stored) {
                historyBuffer = JSON.parse(stored);
                // Prune records older than 1 Week
                const cutoff = Date.now() - (604800 * 1000);
                historyBuffer = historyBuffer.filter(d => d.time >= cutoff);
            }
        } catch (e) {
            console.error("Failed to parse telemetry history.", e);
        }
        let currentTimeframe = 3600; // Default to 1H (in seconds)
        // Max buffer: 1W = 7 * 24 * 3600 = 604800 points. 
        const MAX_BUFFER_SIZE = 604800;

        const tfMap = {
            '1M': 60,
            '5M': 300,
            '15M': 900,
            '1H': 3600,
            '4H': 14400,
            '1D': 86400,
            '1W': 604800
        };

        function setTimeframe(tfString) {
            currentTimeframe = tfMap[tfString] || 3600;
            
            // UI styling
            document.querySelectorAll('.tf-btn').forEach(btn => {
                btn.className = "tf-btn px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all duration-300 text-slate-500 hover:text-white";
            });
            const active = document.getElementById(`tf-${tfString}`);
            if (active) {
                active.className = "tf-btn active px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all duration-300 bg-primary/20 text-primary border border-primary/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]";
            }
            
            renderCharts();
        }

        const chartConfig = (color, title, unitType) => ({
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: title,
                    data: [],
                    borderColor: color,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.4, // Smoother lines
                    fill: true,
                    backgroundColor: (context) => {
                        const ctx = context.chart.ctx;
                        const gradient = ctx.createLinearGradient(0, 0, 0, 200);
                        gradient.addColorStop(0, color + '33'); // More transparent
                        gradient.addColorStop(1, color + '00');
                        return gradient;
                    }
                }]
            },
            options: {
                plugins: {
                    shadow: {
                        blur: 15,
                        color: color,
                    }
                },
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { 
                        display: true,
                        position: 'top',
                        align: 'end',
                        labels: { 
                            color: '#94a3b8', 
                            font: { family: '"Inter", sans-serif', size: 10, weight: 'bold' },
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#94a3b8',
                        bodyColor: '#f1f5f9',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { family: '"Inter", sans-serif', size: 10, weight: 'bold' },
                        bodyFont: { family: '"JetBrains Mono", monospace', size: 12 },
                        callbacks: {
                            label: function(context) {
                                let val = context.raw;
                                if (unitType === 'bytes') return ` ${title}: ${formatBytes(val)}`;
                                if (unitType === 'ms') return ` ${title}: ${val.toFixed(1)} ms`;
                                return ` ${title}: ${formatHuman(val)} PPS`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: { color: 'rgba(255, 255, 255, 0.02)' },
                        ticks: { color: '#64748b', font: { family: '"JetBrains Mono", monospace', size: 9 }, maxTicksLimit: 10 }
                    },
                    y: { 
                        display: true,
                        position: 'right',
                        grid: { color: 'rgba(255, 255, 255, 0.02)' },
                        ticks: { 
                            color: '#475569', 
                            font: { family: '"JetBrains Mono", monospace', size: 8 },
                            callback: function(value) {
                                if (unitType === 'bytes') {
                                    if (value >= 1024*1024*1024) return (value/(1024*1024*1024)).toFixed(1) + 'G';
                                    if (value >= 1024*1024) return (value/(1024*1024)).toFixed(1) + 'M';
                                    if (value >= 1024) return (value/1024).toFixed(1) + 'K';
                                    return value;
                                }
                                return formatHuman(value);
                            }
                        },
                        suggestedMin: 0
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                },
                interaction: { mode: 'nearest', axis: 'x', intersect: false }
            }
        });

        const ppsChart = new Chart(document.getElementById('networkVelocityChart'), chartConfig('#10b981', 'Network Velocity', 'pps'));
        const bpsChart = new Chart(document.getElementById('dataThroughputChart'), chartConfig('#3b82f6', 'Data Throughput', 'bytes'));
        const latChart = new Chart(document.getElementById('latencyChart'), chartConfig('#f59e0b', 'Target Latency', 'ms'));

        // Impact Distribution Chart (Doughnut)
        const impactChart = new Chart(document.getElementById('impactChart'), {
            type: 'doughnut',
            data: {
                labels: ['Success (2xx/3xx)', 'Mitigated (4xx)', 'Failed (5xx)', 'Timeout'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        '#10b981', // Success
                        '#f59e0b', // WAF
                        '#ef4444', // Error
                        '#64748b'  // Timeout
                    ],
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'COMBAT IMPACT DISTRIBUTION',
                        color: '#94a3b8',
                        font: { size: 9, weight: '800', family: 'Inter' },
                        padding: { bottom: 10 }
                    }
                }
            }
        });

        let peakThreads = 0;
        let avgSuccessRate = 100;
        let globalTarget = "None";

        // Render historical data initially if available
        if (historyBuffer.length > 0) {
            setTimeout(renderCharts, 100);
        }

        function formatTimeLabel(timestamp, timeframe) {
            const d = new Date(timestamp);
            if (timeframe > 86400) { // > 1D
                return `${d.getDate()}/${d.getMonth()+1} ${d.getHours().toString().padStart(2, '0')}:00`;
            } else if (timeframe > 3600) { // > 1H
                return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
            }
            return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`;
        }

        function downsample(data, targetLength, taskId = null) {
            if (data.length <= targetLength) return data;
            const factor = Math.ceil(data.length / targetLength);
            const res = [];
            for (let i = 0; i < data.length; i += factor) {
                const chunk = data.slice(i, i + factor);
                
                let rps = 0, bps = 0, lat = 0, count = 0;
                let s = 0, w = 0, e = 0, t = 0;
                
                chunk.forEach(point => {
                    if (taskId) {
                        const m = point.tasks?.[taskId];
                        if (m) {
                            rps += m.rps || 0;
                            bps += m.bps || 0;
                            lat += m.lat || 0;
                            s += m.s || 0; w += m.w || 0; e += m.e || 0; t += m.t || 0;
                            count++;
                        }
                    } else {
                        rps += point.rps || 0;
                        bps += point.bps || 0;
                        lat += point.lat || 0;
                        s += point.s || 0; w += point.w || 0; e += point.e || 0; t += point.t || 0;
                        count++;
                    }
                });

                res.push({
                    time: chunk[chunk.length - 1].time,
                    rps: count > 0 ? rps / (taskId ? 1 : chunk.length) : 0, 
                    bps: count > 0 ? bps / (taskId ? 1 : chunk.length) : 0,
                    lat: count > 0 ? lat / count : 0,
                    s, w, e, t
                });
            }
            return res;
        }

        function renderCharts() {
            const now = Date.now();
            const cutoff = now - (currentTimeframe * 1000);
            
            // Optimization: Filter data using binary search or efficient slicing
            let visibleData = historyBuffer.filter(d => d.time >= cutoff);
            
            if (visibleData.length < 2) {
                visibleData = [
                    { time: cutoff, rps: 0, bps: 0, lat: 0, s:0, w:0, e:0, t:0 },
                    { time: now, rps: 0, bps: 0, lat: 0, s:0, w:0, e:0, t:0 }
                ];
            }

            const sampled = downsample(visibleData, 80, currentTaskFilter);
            const labels = sampled.map(d => formatTimeLabel(d.time, currentTimeframe));
            
            ppsChart.data.labels = labels;
            ppsChart.data.datasets[0].data = sampled.map(d => d.rps);
            ppsChart.update('none');

            bpsChart.data.labels = labels;
            bpsChart.data.datasets[0].data = sampled.map(d => d.bps);
            bpsChart.update('none');

            latChart.data.labels = labels;
            latChart.data.datasets[0].data = sampled.map(d => d.lat);
            latChart.update('none');

            // Update Impact Chart with latest aggregate
            const last = visibleData[visibleData.length - 1];
            if (last) {
                impactChart.data.datasets[0].data = [last.s || 0, last.w || 0, last.e || 0, last.t || 0];
                impactChart.update('none');
            }
        }

        let successHistory = [];
        let peakRPS = 0;
        let peakLat = 0;

        window._taskMetrics = {}; // Per-task telemetry store

        function formatHuman(num) {
            if (num >= 1000000) return (num / 1000000).toFixed(2) + 'm';
            if (num >= 1000) return (num / 1000).toFixed(2) + 'k';
            return num.toString();
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B/s';
            const k = 1024;
            const sizes = ['B/s', 'kB/s', 'MB/s', 'GB/s', 'TB/s'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function updateMetrics(taskId, rpsStr, bpsStr, latStr, poolActive, poolTotal, impactData = null) {
            if (!taskId) return;

            // 1. Parse individual task metrics
            let valRps = parseFloat(rpsStr.replace(/[^0-9.]/g, ''));
            if (isNaN(valRps)) valRps = 0;
            if (rpsStr.toLowerCase().includes('k')) valRps *= 1000;
            else if (rpsStr.toLowerCase().includes('m')) valRps *= 1000000;

            let valBps = parseFloat(bpsStr.replace(/[^0-9.]/g, ''));
            if (isNaN(valBps)) valBps = 0;
            const bpsLower = bpsStr.toLowerCase();
            if (bpsLower.includes('gb')) valBps *= 1024 * 1024 * 1024;
            else if (bpsLower.includes('mb')) valBps *= 1024 * 1024;
            else if (bpsLower.includes('kb')) valBps *= 1024;

            let valLat = parseFloat(latStr.replace(/[^0-9.]/g, ''));
            if (isNaN(valLat)) valLat = 0;

            // 2. Store in global registry
            const m = window._taskMetrics[taskId] || {};
            window._taskMetrics[taskId] = {
                lastUpdate: Date.now(),
                rps: valRps,
                rpsStr: rpsStr,
                bps: valBps,
                bpsStr: bpsStr,
                lat: valLat,
                latStr: latStr,
                poolActive: parseInt(poolActive) || 0,
                poolTotal: parseInt(poolTotal) || 0,
                s: impactData ? impactData.s : (m.s || 0),
                w: impactData ? impactData.w : (m.w || 0),
                e: impactData ? impactData.e : (m.e || 0),
                t: impactData ? impactData.t : (m.t || 0)
            };

            // 3. Purge stale task data (> 10s)
            const now = Date.now();
            Object.keys(window._taskMetrics).forEach(id => {
                if (now - window._taskMetrics[id].lastUpdate > 10000) delete window._taskMetrics[id];
            });

            // 4. Calculate Fleet Aggregates
            const activeMetrics = Object.values(window._taskMetrics);
            const totalRps = activeMetrics.reduce((s, m) => s + m.rps, 0);
            const totalBps = activeMetrics.reduce((s, m) => s + m.bps, 0);
            const maxLat = activeMetrics.reduce((max, m) => Math.max(max, m.lat), 0);
            const avgLat = activeMetrics.length > 0 ? activeMetrics.reduce((s, m) => s + m.lat, 0) / activeMetrics.length : 0;
            const aggActive = activeMetrics.reduce((s, m) => s + m.poolActive, 0);
            const aggTotal = activeMetrics.reduce((s, m) => s + m.poolTotal, 0);
            
            const totalS = activeMetrics.reduce((s, m) => s + m.s, 0);
            const totalW = activeMetrics.reduce((s, m) => s + m.w, 0);
            const totalE = activeMetrics.reduce((s, m) => s + m.e, 0);
            const totalT = activeMetrics.reduce((s, m) => s + m.t, 0);

            // 5. Update Global Command Center Cards
            if (document.getElementById('current-rps')) {
                document.getElementById('current-rps').textContent = formatHuman(totalRps);
                if (totalRps > peakRPS) {
                    peakRPS = totalRps;
                    document.getElementById('peak-rps').textContent = formatHuman(peakRPS);
                }
            }

            if (document.getElementById('current-bps')) {
                document.getElementById('current-bps').textContent = formatBytes(totalBps);
                if (!window._peakBpsVal) window._peakBpsVal = 0;
                if (totalBps > window._peakBpsVal) {
                    window._peakBpsVal = totalBps;
                    document.getElementById('peak-bps').textContent = formatBytes(window._peakBpsVal);
                }
            }

            if (document.getElementById('current-latency')) {
                document.getElementById('current-latency').textContent = maxLat > 0 ? maxLat.toFixed(1) + 'ms' : (latStr === 'TIMEOUT' ? 'TIMEOUT' : '0.0ms');
            }

            if (document.getElementById('proxy-stats')) {
                document.getElementById('proxy-stats').innerText = `${aggActive}/${aggTotal}`;
                const efficiency = aggTotal > 0 ? Math.round((aggActive / aggTotal) * 100) : 0;
                document.getElementById('proxy-efficiency').innerText = `${efficiency}%`;
            }

            // 6. Update Task-Specific UI Elements in Fleet Grid
            const rowRps = document.getElementById(`task-rps-${taskId}`);
            const rowBps = document.getElementById(`task-bps-${taskId}`);
            const rowLat = document.getElementById(`task-lat-${taskId}`);
            if (rowRps) rowRps.textContent = rpsStr;
            if (rowBps) rowBps.textContent = bpsStr;
            if (rowLat) rowLat.textContent = latStr;

            // 7. Update Global Analytics History (v1.2.2: Store Task-Specific Details)
            const tasksSnapshot = {};
            Object.entries(window._taskMetrics).forEach(([id, m]) => {
                tasksSnapshot[id] = { rps: m.rps, bps: m.bps, lat: m.lat, s: m.s, w: m.w, e: m.e, t: m.t };
            });

            // Update Bypass Sync Visual Indicator
            const fleetBypassStatus = document.getElementById('bypass-sync-status');
            const fleetBypassCount = document.getElementById('bypass-fleet-count');
            const isSyncActive = activeMetrics.some(m => m.rps > 0); // Simplified check
            
            if (fleetBypassStatus) {
                if (isSyncActive) {
                    fleetBypassStatus.textContent = 'ACTIVE_SYNC';
                    fleetBypassStatus.classList.remove('text-slate-300');
                    fleetBypassStatus.classList.add('text-primary');
                } else {
                    fleetBypassStatus.textContent = 'Standby';
                    fleetBypassStatus.classList.add('text-slate-300');
                    fleetBypassStatus.classList.remove('text-primary');
                }
            }
            if (fleetBypassCount) {
                fleetBypassCount.textContent = `${activeMetrics.length} Nodes`;
            }

            historyBuffer.push({
                time: now,
                bps: totalBps,
                rps: totalRps,
                lat: avgLat,
                s: totalS, w: totalW, e: totalE, t: totalT,
                tasks: tasksSnapshot
            });

            if (historyBuffer.length > MAX_BUFFER_SIZE) historyBuffer.shift();
            renderCharts();
            
            // Auto-save history every 5s
            if (!window.lastTelemetrySave || now - window.lastTelemetrySave > 5000) {
                try {
                    const dataToSave = historyBuffer.length > 2000 ? downsample(historyBuffer, 2000) : historyBuffer;
                    localStorage.setItem('mhddos_telemetry', JSON.stringify(dataToSave));
                } catch(e) {}
                window.lastTelemetrySave = now;
            }
        }

        // --- Core Logic ---
        function getMsgLevel(msg) {
            if (msg.includes("[!]") || msg.includes("ENGINE_CRASH") || msg.includes("API_FAIL") || msg.includes("ERROR")) return 'ERROR';
            if (msg.includes("[*]") || msg.includes("LAUNCHING") || msg.includes("DEPLOYED") || msg.includes("COMMAND") || msg.includes("Scoring complete")) return 'INFO';
            return 'DEBUG';
        }

        function setLogLevel(level) {
            currentLogLevel = level;
            localStorage.setItem('mhddos_log_level', level);
            refreshLogVisibility();
        }

        function refreshLogVisibility() {
            const filter = currentLogFilter;
            const levelThreshold = LOG_LEVELS[currentLogLevel];
            const taskFilter = currentTaskFilter;
            
            document.querySelectorAll('.log-entry').forEach(entry => {
                const entryType = entry.dataset.type;
                const entryLevel = entry.dataset.level;
                const entryTaskId = entry.dataset.taskId;
                const entryLevelVal = LOG_LEVELS[entryLevel] || 0;
                
                const matchesFilter = (filter === 'ALL' || entryType === filter);
                const matchesLevel = (entryLevelVal >= levelThreshold);
                const matchesTask = (!taskFilter || entryTaskId === taskFilter);
                
                entry.style.display = (matchesFilter && matchesLevel && matchesTask) ? 'flex' : 'none';
            });
        }

        function appendLog(msg, type = 'SYSTEM', taskId = null) {
            if (!msg) return;
            const lines = msg.split('\n');
            if (lines.length > 1) {
                lines.forEach(line => appendLog(line, type, taskId));
                return;
            }

            const cleanMsg = msg.replace(/\x1B\[[0-9;]*[mK]/g, '').trim();
            if (!cleanMsg) return;

            const rpsMatch = cleanMsg.match(/PPS:\s*([^,]+)/i);
            const bpsMatch = cleanMsg.match(/BPS:\s*([^,]+)/i);
            const latMatch = cleanMsg.match(/Latency:\s*([^,]+)/i);
            const poolMatch = cleanMsg.match(/Pool:\s*(\d+)\/(\d+)/i);
            
            if (rpsMatch || bpsMatch) {
                updateMetrics(
                    taskId,
                    rpsMatch ? rpsMatch[1] : "0", 
                    bpsMatch ? bpsMatch[1].split(',')[0].trim() : "0 B", 
                    latMatch ? latMatch[1] : "0 ms",
                    poolMatch ? poolMatch[1] : "0",
                    poolMatch ? poolMatch[2] : "0"
                );
                return;
            }

            const entry = document.createElement('div');
            let logType = type;
            if (cleanMsg.includes("[!]")) logType = 'ERROR';
            else if (cleanMsg.includes("LAUNCHING") || cleanMsg.includes("DEPLOYED")) logType = 'ATTACK';
            else if (cleanMsg.includes("[*]")) logType = 'SYSTEM';

            const entryLevel = getMsgLevel(cleanMsg);
            entry.dataset.level = entryLevel;
            entry.dataset.type = logType;
            if(taskId) entry.dataset.taskId = taskId;

            const matchesLevel = (LOG_LEVELS[entryLevel] >= LOG_LEVELS[currentLogLevel]);
            const matchesFilter = (currentLogFilter === 'ALL' || logType === currentLogFilter);
            const matchesTask = (!currentTaskFilter || taskId === currentTaskFilter);

            if (!(matchesLevel && matchesFilter && matchesTask)) entry.style.display = 'none';

            entry.className = `log-entry flex gap-4 ${logType === 'ERROR' ? 'text-danger' : entryLevel === 'DEBUG' ? 'text-slate-500 opacity-60' : 'text-slate-400'}`;
            const label = document.createElement('span');
            label.className = `shrink-0 font-bold w-20 ${logType === 'ERROR' ? 'text-danger' : logType === 'ATTACK' ? 'text-primary' : 'text-slate-600'}`;
            label.textContent = taskId ? `[${taskId.toUpperCase()}]` : `[${logType}]`;
            const content = document.createElement('span');
            content.className = "flex-1 break-all";
            content.textContent = cleanMsg;
            entry.appendChild(label);
            entry.appendChild(content);
            term.appendChild(entry);
            
            if (term.scrollHeight - term.clientHeight <= term.scrollTop + 100) term.scrollTop = term.scrollHeight;
            while (term.childNodes.length > 1000) { term.removeChild(term.firstChild); }
        }

        function setLogFilter(filter) {
            currentLogFilter = filter;
            document.querySelectorAll('.filter-chip').forEach(c => {
                c.classList.remove('active', 'bg-primary', 'text-slate-950');
                c.classList.add('text-slate-500');
            });
            const activeChip = document.getElementById(`filter-${filter}`);
            if (activeChip) {
                activeChip.classList.add('active', 'bg-primary', 'text-slate-950');
                activeChip.classList.remove('text-slate-500');
            }
            refreshLogVisibility();
        }

        async function analyzeTarget() {
            const target = document.getElementById('target').value;
            if (!target) return appendLog("[!] RECON_ERR: Target required for radar scan.", "ERROR");
            appendLog(`[*] INITIATING RADAR SCAN: Analyzing infrastructure for ${target}...`);
            try {
                const res = await fetch('/api/recon/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    appendLog(`[*] RADAR LOCK: Detected Stack = [${data.server}], HTTP ${data.status_code}`);
                    appendLog(`[*] TACTICAL RECOMMENDATION: Applying ${data.recommendation} sequence.`);
                    document.getElementById('method').value = data.recommendation;
                    updateVisibility();
                    const badgeContainer = document.getElementById('recon-waf-badge');
                    const wafClass = (data.server || '').toLowerCase().replace(/[\/\s]/g, '');
                    badgeContainer.innerHTML = `<span class="recon-badge badge-${wafClass}">${data.server} PROTECTED</span>`;
                } else { appendLog(`[!] RECON_FAIL: ${data.message}`, "ERROR"); }
            } catch (e) { appendLog(`[!] API_FAIL: ${e.message}`, "ERROR"); }
            
            try {
                const geoRes = await fetch(`/api/recon/geo?target=${encodeURIComponent(target)}`);
                const geoData = await geoRes.json();
                if (geoData.status === 'success') {
                    document.getElementById('geo-isp').textContent = geoData.isp;
                    document.getElementById('geo-loc').textContent = `${geoData.city}, ${geoData.country}`;
                    initMap(geoData.lat, geoData.lon);
                }
            } catch (e) { console.error(e); }
        }

        async function startAttack() {
            const target = document.getElementById('target').value;
            if (!target) return appendLog("[!] VALIDATION_FAILED: Destination target required.", "ERROR");
            setAppState(STATE.STARTING);
            const params = {
                target: target,
                method: document.getElementById('method').value,
                threads: parseInt(document.getElementById('threads').value),
                duration: parseInt(document.getElementById('duration').value),
                proxy_type: document.getElementById('proxy_type').value,
                proxy_list: document.getElementById('auto_harvest').checked ? "auto_harvest.txt" : document.getElementById('proxy_list').value,
                rpc: parseInt(document.getElementById('rpc').value),
                reflector: document.getElementById('reflector').value,
                proxy_refresh: document.getElementById('auto_refresh').checked ? parseInt(document.getElementById('proxy_refresh').value) : 0,
                auto_harvest: document.getElementById('auto_harvest').checked,
                smart_rpc: document.getElementById('smart_rpc').checked,
                autoscale: document.getElementById('auto_scale').checked,
                evasion: document.getElementById('advanced_evasion').checked,
                distribute_to_workers: document.getElementById('distribute_to_workers').checked
            };
            try {
                const res = await fetch('/api/attack/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });
                const data = await res.json();
                if (data.status === 'error') {
                    showToast(`Deployment Failed: ${data.message}`, 'error');
                    appendLog(`[!] DEPLOYMENT_ERR: ${data.message}`, "ERROR");
                    setAppState(STATE.IDLE);
                } else { 
                    saveToMemory(); 
                    refreshTasks(); 
                    setAppState(STATE.RUNNING);
                    showToast(`Deployment Successful. Sequence ${data.recommendation} active.`, 'success');
                }
            } catch (e) {
                showToast(`Critical API Failure: ${e.message}`, 'error');
                appendLog(`[!] API_FAIL: ${e.message}`, "ERROR");
                setAppState(STATE.IDLE);
            }
        }

        async function stopAttack(taskId = null) {
            if (!taskId) {
                showToast("Task ID missing for termination.", 'warning');
                return;
            }

            const btn = document.querySelector(`[data-stop-id="${taskId}"]`);
            const originalText = btn ? btn.innerHTML : null;
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<span class="material-symbols-rounded animate-spin text-sm">refresh</span><span>Purging...</span>`;
            }

            try {
                const res = await fetch('/api/attack/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task_id: taskId })
                });
                const data = await res.json();
                if (data.status === 'error') {
                    showToast(`Purge Error: ${data.message}`, 'error');
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = originalText;
                    }
                } else {
                    showToast(`Task ${taskId} successfully purged.`, 'success');
                    // Fast UI removal
                    const row = document.querySelector(`[data-task-row-id="${taskId}"]`);
                    if (row) {
                        row.style.opacity = '0';
                        row.style.transform = 'translateX(20px)';
                        setTimeout(() => row.remove(), 300);
                    }
                }
                setTimeout(refreshTasks, 800);
            } catch (e) {
                showToast(`Purge API Failure: ${e.message}`, 'error');
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }
            }
        }

        async function stopAllAttacks() {
            setAppState(STATE.STOPPING);
            showToast("Initiating global termination sequence...", 'warning');
            try {
                const res = await fetch('/api/attack/status');
                const data = await res.json();
                if(data.status === 'success' && data.active_tasks) {
                    for(let t of data.active_tasks) {
                        await fetch('/api/attack/stop', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ task_id: t.task_id })
                        });
                    }
                }
                setTimeout(refreshTasks, 1000);
            } catch(e) {
                 appendLog(`[!] API_FAIL: ${e.message}`, "ERROR");
            }
        }

        async function refreshTasks() {
            try {
                const res = await fetch('/api/attack/status');
                const data = await res.json();
                if (data.status === 'success') {
                    renderTasksList(data.active_tasks);
                    if (data.active_tasks.length === 0) {
                        setAppState(STATE.IDLE);
                    } else {
                        setAppState(STATE.RUNNING);
                    }
                }
            } catch (e) { console.error("Error refreshing tasks:", e); }
        }

        function formatDuration(seconds) {
            if (seconds === Infinity || isNaN(seconds)) return "UNLIMITED";
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = Math.floor(seconds % 60);
            return `${h > 0 ? h + ':' : ''}${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }

        let lastTasksJson = '';
        function renderTasksList(tasks) {
            const container = document.getElementById('tasks-container');
            const emptyState = document.getElementById('tasks-empty-state');
            const countBadge = document.getElementById('active-tasks-count');

            if(countBadge) countBadge.textContent = tasks.length;

            // Update Active Threads & Target
            let totalThreads = 0;
            let currentTarget = "None";
            if (tasks.length > 0) {
                totalThreads = tasks.reduce((sum, t) => sum + (t.threads || 0), 0);
                if (tasks.length === 1) currentTarget = tasks[0].target;
                else currentTarget = "Multiple Targets";
                document.getElementById('target-status').textContent = "Engaged";
                document.getElementById('target-status').className = "text-danger";
            } else {
                currentTarget = "None";
                document.getElementById('target-status').textContent = "Standby";
                document.getElementById('target-status').className = "text-warning";
            }

            document.getElementById('current-threads').textContent = totalThreads;
            if (totalThreads > peakThreads) {
                peakThreads = totalThreads;
                document.getElementById('peak-threads').textContent = peakThreads;
            }
            document.getElementById('current-target').textContent = currentTarget;

            if (!container) return;

            // Optimization: Only re-render if task list structure changed
            const currentTasksJson = JSON.stringify(tasks.map(t => ({ id: t.task_id, target: t.target, method: t.method })));
            if (currentTasksJson === lastTasksJson && container.children.length > 0) {
                // Just update metrics inside existing cards
                tasks.forEach(t => {
                    const metrics = window._taskMetrics[t.task_id] || { rpsStr: '0', bpsStr: '0 B', latStr: '0ms' };
                    const rpsEl = document.getElementById(`task-rps-${t.task_id}`);
                    const bpsEl = document.getElementById(`task-bps-${t.task_id}`);
                    const latEl = document.getElementById(`task-lat-${t.task_id}`);
                    if (rpsEl) rpsEl.textContent = metrics.rpsStr;
                    if (bpsEl) bpsEl.textContent = metrics.bpsStr;
                    if (latEl) latEl.textContent = metrics.latStr;
                });
                return; 
            }
            lastTasksJson = currentTasksJson;

            if (tasks.length === 0) {
                container.innerHTML = '';
                if(emptyState) container.appendChild(emptyState);
                return;
            }

            container.innerHTML = '';
            tasks.forEach(t => {
                const isIsolated = currentTaskFilter === t.task_id;
                const metrics = window._taskMetrics[t.task_id] || { rpsStr: '0', bpsStr: '0 B', latStr: '0ms' };
                const timeLeft = Math.max(0, t.duration - t.elapsed);
                const progress = Math.min(100, (t.elapsed / t.duration) * 100);

                const row = document.createElement('div');
                row.setAttribute('data-task-row-id', t.task_id);
                row.onclick = () => setTaskFilter(t.task_id);
                row.className = `glass-card cursor-pointer border rounded-2xl p-4 flex flex-col gap-4 transition-all group module-enter relative overflow-hidden ${isIsolated ? 'border-primary shadow-[0_0_20px_rgba(16,185,129,0.1)]' : 'border-white/5 hover:border-primary/30'}`;
                row.innerHTML = `
                    <div class="absolute inset-0 bg-gradient-to-r from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

                    <div class="flex items-start justify-between relative z-10">
                        <div class="flex items-center gap-4 min-w-0">
                            <div class="size-10 shrink-0 rounded-xl flex items-center justify-center relative transition-all bg-slate-900 border ${isIsolated ? 'border-primary text-primary shadow-inner' : 'border-white/10 text-slate-400 group-hover:border-primary/50 group-hover:text-primary'}">
                                <span class="material-symbols-rounded text-xl">${isIsolated ? 'visibility' : 'radar'}</span>
                                <span class="absolute -top-1 -right-1 size-2.5 bg-primary rounded-full animate-ping opacity-75"></span>
                                <span class="absolute -top-1 -right-1 size-2.5 bg-primary rounded-full "></span>
                            </div>
                            <div class="min-w-0">
                                <div class="text-xs font-mono font-black text-white mb-1 truncate max-w-[200px] md:max-w-[300px]" data-tooltip="${t.target}">${t.target}</div>
                                <div class="flex items-center gap-2">
                                    <span class="bg-primary/10 text-primary text-[8px] font-black uppercase tracking-[0.2em] px-2 py-0.5 rounded-md border border-primary/20">${t.method}</span>
                                    <span class="text-slate-500 text-[9px] font-mono font-bold uppercase tracking-widest">${t.threads} WORKERS</span>
                                </div>
                            </div>
                        </div>

                        <button onclick="event.stopPropagation(); stopAttack('${t.task_id}')" data-stop-id="${t.task_id}" class="bg-danger/10 hover:bg-danger text-danger hover:text-white border border-danger/30 rounded-lg px-3 py-2 text-[9px] font-black uppercase tracking-widest transition-all flex items-center gap-2 shadow-sm group/btn">
                            <span class="material-symbols-rounded text-sm group-hover/btn:rotate-90 transition-transform">close</span>
                            <span class="hidden sm:inline">Purge</span>
                        </button>
                    </div>

                    <div class="grid grid-cols-3 gap-2 relative z-10 bg-slate-950/40 p-3 rounded-xl border border-white/5">
                        <div class="text-center">
                            <div class="text-[7px] font-black text-slate-500 uppercase tracking-tighter mb-0.5">Velocity</div>
                            <div id="task-rps-${t.task_id}" class="text-[10px] font-mono font-black text-primary">${metrics.rpsStr}</div>
                        </div>
                        <div class="text-center border-x border-white/5">
                            <div class="text-[7px] font-black text-slate-500 uppercase tracking-tighter mb-0.5">Throughput</div>
                            <div id="task-bps-${t.task_id}" class="text-[10px] font-mono font-black text-success">${metrics.bpsStr}</div>
                        </div>
                        <div class="text-center">
                            <div class="text-[7px] font-black text-slate-500 uppercase tracking-tighter mb-0.5">Latency</div>
                            <div id="task-lat-${t.task_id}" class="text-[10px] font-mono font-black text-warning">${metrics.latStr}</div>
                        </div>
                    </div>

                    <div class="flex items-center justify-between relative z-10 px-1">
                        <div class="flex gap-4">
                            <div>
                                <div class="text-[7px] font-black uppercase tracking-widest text-slate-500 mb-0.5">Elapsed</div>
                                <div class="text-[9px] font-mono font-black text-white tabular-nums">${t.elapsed}s</div>
                            </div>
                            <div>
                                <div class="text-[7px] font-black uppercase tracking-widest text-slate-500 mb-0.5">Remaining</div>
                                <div class="text-[9px] font-mono font-black text-primary-light tabular-nums">${formatDuration(timeLeft)}</div>
                            </div>
                        </div>
                        <div class="flex-1 max-w-[100px] ml-4">
                            <div class="h-1 bg-white/5 rounded-full overflow-hidden">
                                <div class="h-full bg-primary shadow-[0_0_8px_#10b981]" style="width: ${progress}%"></div>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(row);
            });        }

        function updateVisibility() {
            const method = document.getElementById('method').value;
            const L7 = ["BYPASS", "CFB", "GET", "POST", "OVH", "STRESS", "DYN", "SLOW", "HEAD", "NULL", "COOKIE", "PPS", "EVEN", "GSB", "DGB", "AVB", "CFBUAM", "APACHE", "XMLRPC", "BOT", "BOMB", "DOWNLOADER", "KILLER", "TOR", "RHEX", "STOMP", "IMPERSONATE", "HTTP3"];
            const L4_AMP = ["MEM", "NTP", "DNS", "RDP", "ARD", "CLDAP", "CHAR"];
            document.getElementById('rpc-container').style.display = L7.includes(method) ? 'block' : 'none';
            document.getElementById('reflector-container').style.display = L4_AMP.includes(method) ? 'block' : 'none';
        }

        function toggleRefreshDropdown() {
            const checked = document.getElementById('auto_refresh').checked;
            const container = document.getElementById('refresh-interval-container');
            container.style.opacity = checked ? "1" : "0.3";
            container.style.pointerEvents = checked ? "auto" : "none";
        }

        function toggleHarvest() {
            const checked = document.getElementById('auto_harvest').checked;
            const proxyListInput = document.getElementById('proxy_list');
            if (checked) {
                proxyListInput.disabled = true;
                proxyListInput.style.opacity = "0.5";
            } else {
                proxyListInput.disabled = false;
                proxyListInput.style.opacity = "1";
            }
        }

        const memoryFields = ['target', 'method', 'threads', 'duration', 'proxy_type', 'proxy_list', 'rpc', 'reflector', 'auto_refresh', 'proxy_refresh', 'auto_harvest', 'smart_rpc', 'auto_scale', 'advanced_evasion', 'distribute_to_workers'];
        function saveToMemory() {
            memoryFields.forEach(id => {
                const el = document.getElementById(id);
                if(el) localStorage.setItem('mhddos_gui_v113_' + id, el.type === 'checkbox' ? el.checked : el.value);
            });
        }

        function loadFromMemory() {
            memoryFields.forEach(id => {
                const val = localStorage.getItem('mhddos_gui_v113_' + id);
                if (val !== null) {
                    const el = document.getElementById(id);
                    if (el) {
                        if (el.type === 'checkbox') el.checked = (val === 'true');
                        else el.value = val;
                    }
                }
            });
            // Attach auto-save listeners to all fields
            memoryFields.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    const eventType = (el.tagName === 'SELECT' || el.type === 'checkbox' || el.type === 'number') ? 'change' : 'input';
                    el.addEventListener(eventType, saveToMemory);
                }
            });
        }

        async function checkC2Status() {
            document.getElementById('c2-node-id').textContent = 'C2_MASTER';
            document.getElementById('c2-node-id').className = 'text-xs font-mono font-bold text-secondary';
            document.getElementById('session-uuid').textContent = 'MODE: C2_CONTROLLER | LISTENING';
        }

        async function refreshC2Nodes() {
            try {
                const res = await fetch('/api/c2/nodes');
                const data = await res.json();
                if (data.status === 'success') {
                    const tbody = document.getElementById('c2-worker-list');
                    const countBadge = document.getElementById('c2-worker-count');
                    const countFooter = document.getElementById('c2-worker-count-footer');

                    if(countBadge) countBadge.textContent = data.workers.length;
                    if(countFooter) countFooter.textContent = data.workers.length;

                    if (data.workers.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="4" class="py-12 text-center text-slate-600 italic uppercase tracking-[0.2em] text-[9px] font-black">No worker nodes connected.</td></tr>';
                        return;
                    }

                    tbody.innerHTML = data.workers.map(w => `
                        <tr class="hover:bg-slate-800/50 transition-colors group border-b border-white/5 last:border-0">
                            <td class="py-4 px-6 text-secondary font-mono font-bold flex items-center gap-3 tracking-wider"><div class="size-2 rounded-full bg-secondary  pulse-active"></div>${w.node_id}</td>
                            <td class="py-4 px-6 text-slate-400 font-mono group-hover:text-white transition-colors">${w.hostname} <span class="text-[9px] text-slate-600 block uppercase tracking-widest mt-1 font-sans font-black">${w.os}</span></td>
                            <td class="py-4 px-6">
                                <div class="flex items-center gap-3 mb-1.5">
                                    <div class="w-16 h-1 bg-slate-800 rounded-full overflow-hidden"><div class="h-full bg-primary" style="width: ${w.cpu_percent}%"></div></div>
                                    <span class="text-[10px] text-slate-400 w-8 font-mono font-bold">${w.cpu_percent}%</span>
                                </div>
                                <div class="flex items-center gap-3">
                                    <div class="w-16 h-1 bg-slate-800 rounded-full overflow-hidden"><div class="h-full bg-warning" style="width: ${w.ram_percent}%"></div></div>
                                    <span class="text-[10px] text-slate-400 w-8 font-mono font-bold">${w.ram_percent}%</span>
                                </div>
                            </td>
                            <td class="py-4 px-6 text-right">
                                <span class="px-3 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-[0.2em] font-sans ${w.status === 'busy' ? 'bg-warning/10 text-warning border border-warning/20' : 'bg-primary/10 text-primary border border-primary/20 shadow-inner'}">
                                    ${w.status === 'busy' ? 'COMBAT' : 'IDLE'}
                                </span>
                            </td>
                        </tr>
                    `).join('');
                }
            } catch(e) { console.error("Error fetching C2 nodes:", e); }
        }
        async function setupWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);
            ws.onopen = () => {
                document.getElementById('connection-status').className = 'size-2 rounded-full bg-primary pulse-active';
                document.getElementById('header-status-text').textContent = "GRID_CONNECTED";
            };
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if(data.task_id) {
                        if (data.type === 'impact') {
                            updateMetrics(
                                data.task_id, 
                                "0", "0 B", "0 ms", "0", "0", 
                                data.data
                            );
                            return;
                        }
                        
                        appendLog(data.msg, 'SYSTEM', data.task_id);
                        if (data.msg.includes("COMMAND DEPLOYED")) {
                            setAppState(STATE.RUNNING);
                            refreshTasks();
                        }
                        if (data.msg.includes("COMMAND TERMINATED")) {
                            setTimeout(refreshTasks, 1000);
                        }
                    }
                } catch(e) {
                    // Fallback for non-JSON logs
                    const msg = event.data;
                    appendLog(msg);
                    if (msg.includes("COMMAND DEPLOYED")) setAppState(STATE.RUNNING);
                    if (msg.includes("COMMAND TERMINATED")) setTimeout(refreshTasks, 1000);
                }
            };
            ws.onclose = () => {
                document.getElementById('connection-status').className = 'size-2 rounded-full bg-danger pulse-active';
                document.getElementById('header-status-text').textContent = "OFFLINE_RECONNECTING";
                setTimeout(setupWebSocket, 3000);
            };
        }

        async function browseFile(inputId) {
            try {
                const res = await fetch('/api/select_file');
                const data = await res.json();
                if (data.path) document.getElementById(inputId).value = data.path;
            } catch (e) { console.error(e); }
        }

        function clearTerminal() { term.innerHTML = ''; appendLog("Buffer purged. Intelligence matrix re-calibrated."); }
        async function copyLogs() {
            const text = Array.from(document.querySelectorAll('.log-entry')).map(e => e.innerText).join('\n');
            await navigator.clipboard.writeText(text);
            appendLog("Matrix data exported to clipboard.");
        }

        // --- Config Modal Logic ---
        async function openConfigModal() {
            const modal = document.getElementById('config-modal');
            const content = document.getElementById('config-modal-content');
            const container = document.getElementById('config-sources-container');
            modal.classList.remove('hidden');
            setTimeout(() => { modal.classList.remove('opacity-0'); content.classList.remove('translate-y-4'); }, 10);
            container.innerHTML = '<div class="text-center text-slate-500 py-4"><span class="material-symbols-rounded animate-spin">refresh</span></div>';
            try {
                const res = await fetch('/api/config/proxies');
                const data = await res.json();
                if (data.status === 'success') renderConfigSources(data.providers);
            } catch (e) { console.error(e); }
        }

        function closeConfigModal() {
            const modal = document.getElementById('config-modal');
            const content = document.getElementById('config-modal-content');
            modal.classList.add('opacity-0'); content.classList.add('translate-y-4');
            setTimeout(() => modal.classList.add('hidden'), 300);
        }

        let configSources = [];
        function renderConfigSources(providers) {
            configSources = providers;
            const container = document.getElementById('config-sources-container');
            container.innerHTML = '';
            if (providers.length === 0) { container.innerHTML = '<div class="text-center text-slate-500 py-4 text-xs">No resources defined.</div>'; return; }
            providers.forEach((p, index) => {
                const item = document.createElement('div');
                item.className = 'flex items-center gap-3 p-3 bg-slate-950 rounded-xl border border-white/5 group';
                item.innerHTML = `
                    <select onchange="updateConfigSource(${index}, 'type', parseInt(this.value))" class="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1.5 focus:border-primary outline-none w-24 shrink-0">
                        <option value="0" ${p.type === 0 ? 'selected' : ''}>ALL</option>
                        <option value="1" ${p.type === 1 ? 'selected' : ''}>HTTP</option>
                        <option value="4" ${p.type === 4 ? 'selected' : ''}>SOCKS4</option>
                        <option value="5" ${p.type === 5 ? 'selected' : ''}>SOCKS5</option>
                    </select>
                    <input type="text" value="${p.url}" onchange="updateConfigSource(${index}, 'url', this.value)" class="flex-1 bg-transparent border-b border-slate-800 text-slate-300 text-xs px-2 py-1 focus:border-primary outline-none" />
                    <button onclick="removeConfigSource(${index})" class="text-slate-600 hover:text-danger opacity-0 group-hover:opacity-100 transition-all"><span class="material-symbols-rounded">delete</span></button>
                `;
                container.appendChild(item);
            });
        }

        function updateConfigSource(index, field, value) { configSources[index][field] = value; }
        function removeConfigSource(index) { configSources.splice(index, 1); renderConfigSources(configSources); }
        function addConfigSource() { configSources.push({ type: 5, url: '', timeout: 10 }); renderConfigSources(configSources); }
        async function saveProxyConfig() {
            try {
                const res = await fetch('/api/config/proxies', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ providers: configSources }) });
                const data = await res.json();
                if(data.status === 'success') closeConfigModal();
            } catch (e) { console.error(e); }
        }

        async function scanSubdomains() {
            const target = document.getElementById('target').value;
            if(!target) {
                showToast("Target required for surface scan.", "warning");
                return;
            }
            const btn = document.getElementById('subdomain-scan-btn');
            const table = document.getElementById('subdomain-results');
            btn.disabled = true; btn.innerHTML = '<span class="material-symbols-rounded text-sm animate-spin">refresh</span> Scanning...';
            table.innerHTML = '<tr><td colspan="3" class="py-12 text-center text-primary animate-pulse font-bold uppercase tracking-widest text-[9px]">Discovering attack surfaces...</td></tr>';
            try {
                const res = await fetch('/api/recon/subdomains', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target }) });
                const data = await res.json();
                if(data.status === 'success' && data.subdomains.length > 0) {
                    table.innerHTML = data.subdomains.map(s => `<tr class="hover:bg-slate-800/50 transition-colors group border-b border-white/5 last:border-0"><td class="py-3 px-6 text-white font-mono font-bold tracking-wider">${s.subdomain}</td><td class="py-3 px-6 text-slate-400 font-mono group-hover:text-white transition-colors">${s.ip}</td><td class="py-3 px-6 text-right"><button onclick="quickAttack('${s.subdomain}')" class="text-primary hover:text-white hover:bg-primary uppercase font-black font-sans text-[9px] tracking-widest border border-primary/30 px-3 py-1.5 rounded-lg transition-all shadow-[0_0_10px_rgba(19,236,91,0.1)] hover:">Lock-On</button></td></tr>`).join('');
                } else { table.innerHTML = '<tr><td colspan="3" class="py-12 text-center text-slate-600 italic uppercase tracking-[0.2em] text-[9px] font-black">No additional endpoints identified.</td></tr>'; }
            } catch(e) { console.error(e); }
            btn.disabled = false; btn.innerHTML = '<span class="material-symbols-rounded text-sm">radar</span> Scan Network';
        }

        function quickAttack(target) { document.getElementById('target').value = target; analyzeTarget(); }

        // --- Tactical Tools Logic ---
        let currentTool = 'ping';

        function openToolsModal() {
            const modal = document.getElementById('tools-modal');
            const content = document.getElementById('tools-modal-content');
            modal.classList.remove('hidden');
            setTimeout(() => { modal.classList.remove('opacity-0'); content.classList.remove('translate-y-4'); }, 10);
            const mainTarget = document.getElementById('target').value;
            if (mainTarget) {
                const host = mainTarget.replace(/https?:\/\//, '').split('/')[0];
                document.getElementById('tool-target').value = host;
            }
        }

        function closeToolsModal() {
            const modal = document.getElementById('tools-modal');
            const content = document.getElementById('tools-modal-content');
            modal.classList.add('opacity-0'); content.classList.add('translate-y-4');
            setTimeout(() => modal.classList.add('hidden'), 300);
        }

        function switchToolTab(tool) {
            currentTool = tool;
            document.querySelectorAll('.tool-tab').forEach(t => { t.classList.remove('bg-primary', 'text-slate-950', 'shadow-[0_0_15px_rgba(16,185,129,0.3)]'); t.classList.add('text-slate-500', 'hover:text-white'); });
            const active = document.getElementById(`tab-${tool}`);
            active.classList.add('bg-primary', 'text-slate-950', 'shadow-[0_0_15px_rgba(16,185,129,0.3)]'); active.classList.remove('text-slate-500', 'hover:text-white');
            const label = document.getElementById('tool-input-label');
            if (tool === 'check') label.textContent = 'Target URL'; else label.textContent = 'Target Host / IP';
        }

        async function executeTool() {
            const target = document.getElementById('tool-target').value;
            const resultArea = document.getElementById('tool-result');
            const btn = document.getElementById('tool-exec-btn');
            if (!target) return alert("Target required for diagnostic.");
            btn.disabled = true; btn.innerHTML = '<span class="material-symbols-rounded animate-spin">refresh</span> Processing...';
            resultArea.innerHTML = `<div class="text-primary font-bold animate-pulse">> Initializing ${currentTool.toUpperCase()} protocol...</div>`;
            try {
                const res = await fetch(`/api/tools/${currentTool}?${currentTool === 'check' ? 'url' : 'host'}=${encodeURIComponent(target)}`);
                const data = await res.json();
                if (data.status === 'error') { resultArea.innerHTML = `<div class="text-danger">[!] ERROR: ${data.message}</div>`; } else { renderToolResult(data); }
            } catch (e) { resultArea.innerHTML = `<div class="text-danger">[!] NETWORK_FAIL: ${e.message}</div>`; } finally { btn.disabled = false; btn.innerHTML = '<span class="material-symbols-rounded text-lg">play_arrow</span> Run'; }
        }

        function renderToolResult(data) {
            const resultArea = document.getElementById('tool-result');
            let html = `<div class="text-primary font-bold mb-4">> ${currentTool.toUpperCase()} DATA RETRIEVED</div>`;
            if (currentTool === 'ping') {
                html += `<div class="grid grid-cols-2 gap-4"><div class="space-y-1"><span class="text-slate-600">Resolved:</span> ${data.address}</div><div class="space-y-1"><span class="text-slate-600">Status:</span> ${data.is_alive ? '<span class="text-primary">ONLINE</span>' : '<span class="text-danger">DEAD</span>'}</div><div class="space-y-1"><span class="text-slate-600">Avg RTT:</span> ${data.avg_rtt.toFixed(2)} ms</div><div class="space-y-1"><span class="text-slate-600">Loss:</span> ${((data.packets_sent - data.packets_received)/data.packets_sent*100).toFixed(0)}%</div></div>`;
            } else if (currentTool === 'check') {
                html += `<div class="flex items-center gap-4"><div class="text-3xl font-black ${data.online ? 'text-primary' : 'text-danger'}">${data.status_code}</div><div><div class="font-bold">${data.online ? 'WEB_SERVER_ACTIVE' : 'WEB_SERVER_OFFLINE'}</div><div class="text-[10px] text-slate-600">Target responded to HTTP/S handshake.</div></div></div>`;
            } else if (currentTool === 'info') {
                html += `<div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2">${Object.entries(data).map(([k, v]) => `<div class="flex justify-between border-b border-white/5 py-1"><span class="text-slate-600 capitalize">${k.replace(/_/g, ' ')}:</span><span class="text-slate-300 font-bold">${v}</span></div>`).join('')}</div>`;
            } else if (currentTool === 'ports') {
                if(data.ports && data.ports.length > 0) {
                    html += `<div class="grid grid-cols-2 md:grid-cols-3 gap-2">${data.ports.map(p => `<div class="bg-slate-900 border border-primary/20 p-2 rounded-lg text-center"><div class="text-primary font-bold text-lg">${p.port}</div><div class="text-[9px] uppercase tracking-widest text-slate-500">${p.status}</div></div>`).join('')}</div>`;
                } else {
                    html += `<div class="text-slate-500 italic">No common ports detected as open.</div>`;
                }
            } else if (currentTool === 'tech') {
                if(data.tech_stack && data.tech_stack.length > 0) {
                    html += `<div class="flex flex-wrap gap-2">${data.tech_stack.map(t => `<span class="px-3 py-1 bg-secondary/10 border border-secondary/30 text-secondary rounded-full text-xs font-bold">${t}</span>`).join('')}</div>`;
                } else {
                    html += `<div class="text-slate-500 italic">Could not accurately identify the technology stack.</div>`;
                }
            } else if (currentTool === 'dns') {
                html += `<div class="space-y-4">`;
                for(const [type, records] of Object.entries(data.records || {})) {
                    if(records.length > 0) {
                        html += `<div><div class="text-primary font-bold mb-1">${type} Records</div><div class="bg-slate-900 p-2 rounded-lg space-y-1">${records.map(r => `<div class="text-slate-300 break-all">${r}</div>`).join('')}</div></div>`;
                    }
                }
                html += `</div>`;
            }
            resultArea.innerHTML = html;
        }

        // --- History & Analytics Logic ---
        let historyPage = 1;
        let activeHistoryChart = null;

        function switchMainView(view) {
            const views = ['dashboard', 'history'];
            views.forEach(v => {
                document.getElementById(`view-${v}`).classList.add('hidden');
                const tab = document.getElementById(`tab-nav-${v}`);
                tab.classList.remove('border-primary', 'text-primary', 'hover:text-primary-light');
                tab.classList.add('border-transparent', 'text-slate-500', 'hover:text-white');
            });
            
            document.getElementById(`view-${view}`).classList.remove('hidden');
            const activeTab = document.getElementById(`tab-nav-${view}`);
            activeTab.classList.remove('border-transparent', 'text-slate-500', 'hover:text-white');
            activeTab.classList.add('border-primary', 'text-primary', 'hover:text-primary-light');

            if (view === 'history') {
                refreshHistory();
            }
        }

        async function refreshHistory() {
            const tbody = document.getElementById('history-table-body');
            tbody.innerHTML = '<tr><td colspan="7" class="py-12 text-center"><span class="material-symbols-rounded animate-spin text-primary text-2xl">refresh</span></td></tr>';
            try {
                const res = await fetch(`/api/history/sessions?page=${historyPage}&limit=10&t=${Date.now()}`);
                const data = await res.json();
                if (data.status === 'success') {
                    document.getElementById('history-total-records').textContent = `Total: ${data.total} operations`;
                    document.getElementById('history-page-indicator').textContent = `PAGE ${historyPage} / ${data.pages || 1}`;
                    document.getElementById('history-prev-btn').disabled = historyPage <= 1;
                    document.getElementById('history-next-btn').disabled = historyPage >= data.pages;

                    if (data.sessions.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="7" class="py-12 text-center text-slate-700 italic uppercase tracking-[0.2em] text-[9px] font-black">No operations recorded.</td></tr>';
                        return;
                    }

                    tbody.innerHTML = data.sessions.map(s => {
                        const statusColor = s.exit_status === 'error' ? 'text-danger bg-danger/10 border-danger/20' : 
                                            s.exit_status === 'completed' ? 'text-success bg-success/10 border-success/20' : 
                                            s.exit_status === 'aborted' ? 'text-secondary bg-secondary/10 border-secondary/20' :
                                            'text-warning bg-warning/10 border-warning/20';
                        const dur = s.duration_actual !== null ? Math.round(s.duration_actual) + 's' : '-';
                        return `<tr class="hover:bg-slate-800/50 transition-colors group border-b border-white/5 last:border-0 cursor-pointer" onclick="openHistoryDetail('${s.session_id}')">
                            <td class="py-3 px-6 text-slate-400 font-mono text-[9px]">${(s.start_time || '').replace('T', ' ').substring(0, 19)}</td>
                            <td class="py-3 px-6 text-white font-mono font-bold tracking-wider truncate max-w-[200px]" title="${s.target}">${s.target}</td>
                            <td class="py-3 px-6 text-secondary font-black text-[9px] tracking-widest">${s.method}</td>
                            <td class="py-3 px-6 text-slate-400 font-mono">${dur}</td>
                            <td class="py-3 px-6 text-right font-mono text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]">
                                <div>${(s.peak_pps || 0).toLocaleString()} <span class="text-[8px] text-slate-500">PPS</span></div>
                                <div class="text-[8px] text-slate-500">${formatBytes(s.peak_bps || 0)}</div>
                            </td>                            <td class="py-3 px-6 text-center"><span class="px-2 py-0.5 rounded-md border text-[8px] font-black uppercase tracking-widest ${statusColor}">${s.exit_status || 'UNKNOWN'}</span></td>
                            <td class="py-3 px-6 text-center" onclick="event.stopPropagation()"><button onclick="quickAttack('${s.target}')" class="text-primary hover:text-white transition-colors" data-tooltip="Re-deploy against asset"><span class="material-symbols-rounded text-sm">rocket_launch</span></button></td>
                        </tr>`;
                    }).join('');
                } else {
                    tbody.innerHTML = `<tr><td colspan="7" class="py-12 text-center text-danger font-bold">${data.message}</td></tr>`;
                }
            } catch (e) {
                tbody.innerHTML = `<tr><td colspan="7" class="py-12 text-center text-danger">Connection Error: ${e.message}</td></tr>`;
            }
        }

        function changeHistoryPage(delta) {
            historyPage += delta;
            if (historyPage < 1) historyPage = 1;
            refreshHistory();
        }

        async function openHistoryDetail(sessionId) {
            document.getElementById('history-detail-panel').classList.remove('hidden');
            document.getElementById('detail-session-id').textContent = sessionId;
            document.getElementById('history-detail-panel').scrollIntoView({ behavior: 'smooth', block: 'end' });
            
            const eventLog = document.getElementById('history-event-log');
            eventLog.innerHTML = '<div class="text-center text-slate-500 py-4"><span class="material-symbols-rounded animate-spin text-primary">refresh</span></div>';

            try {
                // Fetch events
                const evRes = await fetch(`/api/history/sessions/${sessionId}/events`);
                const evData = await evRes.json();
                if (evData.status === 'success') {
                    if (evData.events.length === 0) {
                        eventLog.innerHTML = '<div class="text-slate-600 italic">No events logged for this mission.</div>';
                    } else {
                        eventLog.innerHTML = evData.events.map(e => {
                            const time = e.timestamp.split('T')[1].substring(0, 8);
                            let color = 'text-slate-400';
                            if (e.event_type === 'error') color = 'text-danger font-bold';
                            else if (e.event_type === 'start') color = 'text-primary';
                            else if (e.event_type === 'stop') color = 'text-warning';
                            return `<div class="flex gap-3 border-b border-white/5 pb-1"><span class="text-slate-600 shrink-0">[${time}]</span> <span class="${color}">${e.message}</span></div>`;
                        }).join('');
                    }
                }

                // Fetch metrics & draw chart
                const metRes = await fetch(`/api/history/sessions/${sessionId}/metrics`);
                const metData = await metRes.json();
                
                if (activeHistoryChart) activeHistoryChart.destroy();
                const ctx = document.getElementById('historyDetailChart').getContext('2d');
                
                if (metData.status === 'success' && metData.metrics.length > 0) {
                    const labels = metData.metrics.map(m => {
                        const d = new Date(m.timestamp + 'Z');
                        return d.toLocaleTimeString([], { hour12: false });
                    });
                    const ppsData = metData.metrics.map(m => m.pps);
                    const bpsData = metData.metrics.map(m => m.bps);
                    const cpuData = metData.metrics.map(m => m.cpu_percent || 0);
                    const ramData = metData.metrics.map(m => m.ram_percent || 0);
                    
                    const rootStyle = getComputedStyle(document.body);
                    const sysPrimary = rootStyle.getPropertyValue('--primary').trim() || '#10b981';
                    const sysSecondary = rootStyle.getPropertyValue('--secondary').trim() || '#3b82f6';
                    const sysWarning = '#f59e0b';
                    const sysDanger = '#ef4444';
                    
                    activeHistoryChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [
                                { label: 'Network Velocity', data: ppsData, borderColor: sysSecondary, backgroundColor: 'transparent', borderWidth: 2, pointRadius: 0, tension: 0.3, yAxisID: 'y' },
                                { label: 'Data Throughput', data: bpsData, borderColor: sysPrimary, backgroundColor: 'transparent', borderWidth: 1, borderDash: [5, 5], pointRadius: 0, tension: 0.3, yAxisID: 'y1' },
                                { label: 'CPU %', data: cpuData, borderColor: sysWarning, backgroundColor: 'transparent', borderWidth: 1.5, pointRadius: 0, tension: 0.3, yAxisID: 'y2', hidden: false },
                                { label: 'RAM %', data: ramData, borderColor: sysDanger, backgroundColor: 'transparent', borderWidth: 1.5, pointRadius: 0, tension: 0.3, yAxisID: 'y2', hidden: true }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: { mode: 'index', intersect: false },
                            plugins: { 
                                legend: { display: true, labels: { color: '#94a3b8', font: { family: "'Fira Code', monospace", size: 10 } } }, 
                                tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.9)', titleColor: sysPrimary, bodyFont: { family: "'Fira Code', monospace", size: 10 }, padding: 10, cornerRadius: 8, borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1 } 
                            },
                            scales: {
                                x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#64748b', font: { family: "'Fira Code', monospace", size: 9 }, maxTicksLimit: 10 } },
                                y: { type: 'linear', display: true, position: 'left', grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: sysSecondary, font: { family: "'Fira Code', monospace", size: 9 }, callback: function(val) { return val > 1000 ? (val/1000).toFixed(1)+'k' : val; } } },
                                y1: { type: 'linear', display: false, position: 'right', grid: { drawOnChartArea: false }, ticks: { color: sysPrimary, font: { family: "'Fira Code', monospace", size: 9 }, callback: function(val) { return val > 1000000 ? (val/1000000).toFixed(1)+'MB' : val > 1000 ? (val/1000).toFixed(1)+'KB' : val; } } },
                                y2: { type: 'linear', display: true, position: 'right', min: 0, max: 100, grid: { drawOnChartArea: false }, ticks: { color: sysWarning, font: { family: "'Fira Code', monospace", size: 9 }, callback: function(val) { return val + '%'; } } }
                            }
                        }
                    });
                } else {
                    activeHistoryChart = new Chart(ctx, { type: 'line', data: { labels: [], datasets: [] }, options: { plugins: { title: { display: true, text: 'No telemetry data retained for this mission', color: '#64748b' } } } });
                }
            } catch (e) {
                console.error("Failed to load history details:", e);
                eventLog.innerHTML = `<div class="text-danger">Failed to fetch telemetry: ${e.message}</div>`;
            }
        }

        function closeHistoryDetail() {
            document.getElementById('history-detail-panel').classList.add('hidden');
            if (activeHistoryChart) activeHistoryChart.destroy();
        }

        function exportHistory(format) {
            window.location.href = `/api/history/export?format=${format}`;
        }

        window.onload = () => {
            loadFromMemory(); 
            // Synchronize UI logic after load
            updateVisibility(); 
            toggleRefreshDropdown(); 
            toggleHarvest(); 
            setupWebSocket(); 
            setLogFilter('ALL'); 
            checkC2Status(); 
            refreshC2Nodes();
            refreshTasks();
            setInterval(refreshC2Nodes, 5000); // Poll C2 nodes every 5s
            setInterval(refreshTasks, 5000);   // Poll active tasks every 5s
            initMap();
            document.getElementById('log-level-selector').value = currentLogLevel; 
            refreshLogVisibility();
            fetch('/api/health').then(r => r.json()).then(d => { if (d.engine_active) setAppState(STATE.RUNNING); });

            // Setup Drag & Drop for Proxy List
            const proxyInput = document.getElementById('proxy_list');
            if(proxyInput) {
                proxyInput.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    proxyInput.classList.add('border-primary', 'bg-primary/10');
                });
                proxyInput.addEventListener('dragleave', () => {
                    proxyInput.classList.remove('border-primary', 'bg-primary/10');
                });
                proxyInput.addEventListener('drop', async (e) => {
                    e.preventDefault();
                    proxyInput.classList.remove('border-primary', 'bg-primary/10');
                    const file = e.dataTransfer.files[0];
                    if(file) {
                        const fd = new FormData();
                        fd.append('file', file);
                        try {
                            const res = await fetch('/api/upload/proxy', { method: 'POST', body: fd });
                            const data = await res.json();
                            if (data.status === 'success') {
                                proxyInput.value = file.name;
                                showToast(`Proxy list ${file.name} uploaded`, 'success');
                            } else {
                                showToast(`Upload failed: ${data.message}`, 'error');
                            }
                        } catch(err) {
                            showToast("Upload error", "error");
                        }
                    }
                });
            }
        };

        // Modal Handlers for UX Enhancements
        function openSettingsModal() { 
            document.getElementById('settings-modal').classList.remove('hidden');
            setTimeout(() => {
                document.getElementById('settings-modal').classList.remove('opacity-0');
                document.getElementById('settings-modal-content').classList.remove('translate-y-8');
            }, 10);
            fetch('/api/config/notifications').then(r=>r.json()).then(d => {
                if(d.status==='success') document.getElementById('discord_webhook').value = d.notifications.discord_webhook_url || '';
            });
        }
        function closeSettingsModal() {
            document.getElementById('settings-modal').classList.add('opacity-0');
            document.getElementById('settings-modal-content').classList.add('translate-y-8');
            setTimeout(() => document.getElementById('settings-modal').classList.add('hidden'), 500);
        }
        async function saveSettings() {
            const webhook = document.getElementById('discord_webhook').value;
            await fetch('/api/config/notifications', {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({discord_webhook_url: webhook})
            });
            showToast("Notification settings saved.", 'success');
            closeSettingsModal();
        }

        function openPresetsModal() {
            document.getElementById('presets-modal').classList.remove('hidden');
            setTimeout(() => {
                document.getElementById('presets-modal').classList.remove('opacity-0');
                document.getElementById('presets-modal-content').classList.remove('translate-y-8');
            }, 10);
            loadPresets();
        }
        function closePresetsModal() {
            document.getElementById('presets-modal').classList.add('opacity-0');
            document.getElementById('presets-modal-content').classList.add('translate-y-8');
            setTimeout(() => document.getElementById('presets-modal').classList.add('hidden'), 500);
        }
        async function loadPresets() {
            const res = await fetch('/api/presets');
            const data = await res.json();
            const list = document.getElementById('presets-list');
            if(data.status==='success' && Object.keys(data.presets).length > 0) {
                list.innerHTML = Object.entries(data.presets).map(([k, v]) => `
                    <div class="flex items-center justify-between bg-slate-900 p-3 rounded-lg border border-white/5">
                        <div class="font-mono text-xs text-white">${k} <span class="text-slate-500 uppercase ml-2 text-[9px]">${v.method} -> ${v.target}</span></div>
                        <div class="flex gap-2">
                            <button onclick='applyPreset(${JSON.stringify(v)})' class="text-primary hover:text-white transition-colors"><span class="material-symbols-rounded text-sm">download</span></button>
                            <button onclick="deletePreset('${k}')" class="text-danger hover:text-white transition-colors"><span class="material-symbols-rounded text-sm">delete</span></button>
                        </div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<div class="text-slate-500 text-xs italic">No saved presets.</div>';
            }
        }
        async function savePreset() {
            const name = document.getElementById('preset_name').value;
            if(!name) return showToast("Preset name required", "warning");
            const params = {
                target: document.getElementById('target').value,
                method: document.getElementById('method').value,
                threads: parseInt(document.getElementById('threads').value),
                duration: parseInt(document.getElementById('duration').value),
                proxy_type: document.getElementById('proxy_type').value,
                proxy_list: document.getElementById('auto_harvest').checked ? "auto_harvest.txt" : document.getElementById('proxy_list').value,
                rpc: parseInt(document.getElementById('rpc').value),
                reflector: document.getElementById('reflector').value,
                proxy_refresh: document.getElementById('auto_refresh').checked ? parseInt(document.getElementById('proxy_refresh').value) : 0,
                auto_harvest: document.getElementById('auto_harvest').checked,
                smart_rpc: document.getElementById('smart_rpc').checked,
                autoscale: document.getElementById('auto_scale').checked,
                evasion: document.getElementById('advanced_evasion').checked,
                distribute_to_workers: document.getElementById('distribute_to_workers').checked
            };
            await fetch('/api/presets', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name, params}) });
            loadPresets();
            showToast("Preset saved", "success");
        }
        async function deletePreset(name) {
            await fetch(`/api/presets/${name}`, { method: 'DELETE' });
            loadPresets();
        }
        function applyPreset(p) {
            document.getElementById('target').value = p.target;
            document.getElementById('method').value = p.method;
            document.getElementById('threads').value = p.threads;
            document.getElementById('duration').value = p.duration;
            document.getElementById('proxy_type').value = p.proxy_type;
            if(p.proxy_list !== 'auto_harvest.txt') document.getElementById('proxy_list').value = p.proxy_list;
            document.getElementById('rpc').value = p.rpc;
            document.getElementById('reflector').value = p.reflector;
            document.getElementById('proxy_refresh').value = p.proxy_refresh;
            document.getElementById('auto_harvest').checked = p.auto_harvest;
            document.getElementById('smart_rpc').checked = p.smart_rpc;
            document.getElementById('auto_scale').checked = p.autoscale;
            document.getElementById('advanced_evasion').checked = p.evasion;
            document.getElementById('distribute_to_workers').checked = p.distribute_to_workers;
            updateVisibility();
            toggleHarvest();
            toggleRefreshDropdown();
            showToast("Preset applied", "success");
            closePresetsModal();
        }

        function openScheduleModal() {
            document.getElementById('schedule-modal').classList.remove('hidden');
            setTimeout(() => {
                document.getElementById('schedule-modal').classList.remove('opacity-0');
                document.getElementById('schedule-modal-content').classList.remove('translate-y-8');
            }, 10);
            loadSchedule();
        }
        function closeScheduleModal() {
            document.getElementById('schedule-modal').classList.add('opacity-0');
            document.getElementById('schedule-modal-content').classList.add('translate-y-8');
            setTimeout(() => document.getElementById('schedule-modal').classList.add('hidden'), 500);
        }
        async function loadSchedule() {
            const res = await fetch('/api/schedule');
            const data = await res.json();
            const list = document.getElementById('schedule-list');
            if(data.status==='success' && Object.keys(data.schedule).length > 0) {
                list.innerHTML = Object.entries(data.schedule).map(([k, v]) => `
                    <div class="flex items-center justify-between bg-slate-900 p-3 rounded-lg border border-white/5">
                        <div class="font-mono text-xs text-white">${new Date(v.datetime_iso).toLocaleString()} <span class="text-slate-500 uppercase ml-2 text-[9px]">${v.params.target}</span></div>
                        <div class="flex gap-2">
                            <button onclick="deleteSchedule('${k}')" class="text-danger hover:text-white transition-colors"><span class="material-symbols-rounded text-sm">delete</span></button>
                        </div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<div class="text-slate-500 text-xs italic">No scheduled tasks.</div>';
            }
        }
        async function saveSchedule() {
            const timeStr = document.getElementById('schedule_time').value;
            if(!timeStr) return showToast("Time required", "warning");
            const d = new Date(timeStr);
            const iso = d.toISOString();

            const params = {
                target: document.getElementById('target').value,
                method: document.getElementById('method').value,
                threads: parseInt(document.getElementById('threads').value),
                duration: parseInt(document.getElementById('duration').value),
                proxy_type: document.getElementById('proxy_type').value,
                proxy_list: document.getElementById('auto_harvest').checked ? "auto_harvest.txt" : document.getElementById('proxy_list').value,
                rpc: parseInt(document.getElementById('rpc').value),
                reflector: document.getElementById('reflector').value,
                proxy_refresh: document.getElementById('auto_refresh').checked ? parseInt(document.getElementById('proxy_refresh').value) : 0,
                auto_harvest: document.getElementById('auto_harvest').checked,
                smart_rpc: document.getElementById('smart_rpc').checked,
                autoscale: document.getElementById('auto_scale').checked,
                evasion: document.getElementById('advanced_evasion').checked,
                distribute_to_workers: document.getElementById('distribute_to_workers').checked
            };
            await fetch('/api/schedule', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: 'task', datetime_iso: iso, params}) });
            loadSchedule();
            showToast("Task scheduled", "success");
        }

// --- Tooltip System Logic ---
        const tooltipEl = document.createElement('div');
        tooltipEl.id = 'custom-tooltip';
        document.body.appendChild(tooltipEl);

        let rafId = null;

        document.addEventListener('mouseover', (e) => {
            const target = e.target.closest('[data-tooltip]');
            if (target) {
                const text = target.getAttribute('data-tooltip');
                if(!text) return;
                
                tooltipEl.innerHTML = `<span class="tt-header">SYS_INFO</span><span>${text}</span>`;
                tooltipEl.classList.add('active');
                
                // Position initial
                let x = e.pageX + 15;
                let y = e.pageY + 15;
                tooltipEl.style.left = x + 'px';
                tooltipEl.style.top = y + 'px';
            }
        });

        document.addEventListener('mousemove', (e) => {
            if (tooltipEl.classList.contains('active')) {
                if (rafId) cancelAnimationFrame(rafId);
                rafId = requestAnimationFrame(() => {
                    const tRect = tooltipEl.getBoundingClientRect();
                    let x = e.pageX + 15;
                    let y = e.pageY + 15;
                    
                    if (x + tRect.width > window.innerWidth) x = e.pageX - tRect.width - 10;
                    if (y + tRect.height > window.innerHeight + window.scrollY) y = e.pageY - tRect.height - 10;
                    
                    tooltipEl.style.left = x + 'px';
                    tooltipEl.style.top = y + 'px';
                });
            }
        });

        document.addEventListener('mouseout', (e) => {
            const target = e.target.closest('[data-tooltip]');
            if (target) {
                tooltipEl.classList.remove('active');
            }
        });