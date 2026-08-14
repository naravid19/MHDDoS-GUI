export async function apiRequest(endpoint, params = {}, method = 'POST') {
    try {
        const options = {
            method: method.toUpperCase(),
            headers: { 'Content-Type': 'application/json' },
        };
        if (options.method !== 'GET' && options.method !== 'HEAD') {
            options.body = JSON.stringify(params);
        }
        const res = await fetch(endpoint, options);
        if (!res.ok) {
            let errorText = `HTTP Error ${res.status}: ${res.statusText}`;
            try {
                const errJson = await res.json();
                if (errJson && errJson.detail) errorText = errJson.detail;
                else if (errJson && errJson.message) errorText = errJson.message;
            } catch (_) {}
            throw new Error(errorText);
        }
        return await res.json();
    } catch (err) {
        console.error(`API Request failed for ${endpoint}:`, err);
        return { status: 'error', message: err.message || 'Unknown network error' };
    }
}

export async function fetchStatus() {
    try {
        const res = await fetch('/api/attack/status');
        if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error('Failed to fetch status:', err);
        return { status: 'error', active_tasks: {}, active_workers: 0 };
    }
}