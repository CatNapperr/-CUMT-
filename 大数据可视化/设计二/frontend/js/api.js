const API_BASE = window.__API_BASE__ || "/api";
const DEFAULT_TIMEOUT = 8000;
const DEFAULT_RETRIES = 2;

function sleep(duration) {
    return new Promise((resolve) => {
        window.setTimeout(resolve, duration);
    });
}

function buildUrl(path, params = {}) {
    const url = new URL(`${API_BASE}${path}`, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
            url.searchParams.set(key, String(value));
        }
    });
    return url;
}

async function requestJson(path, { params, method = "GET", body, retries = DEFAULT_RETRIES, timeout = DEFAULT_TIMEOUT } = {}) {
    let lastError;

    for (let attempt = 0; attempt <= retries; attempt += 1) {
        const controller = new AbortController();
        const timer = window.setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(buildUrl(path, params), {
                method,
                headers: body ? { "Content-Type": "application/json" } : undefined,
                body: body ? JSON.stringify(body) : undefined,
                signal: controller.signal,
            });

            if (!response.ok) {
                throw new Error(`Request failed with status ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            lastError = error;
            if (attempt < retries) {
                await sleep(350 * 2 ** attempt);
            }
        } finally {
            window.clearTimeout(timer);
        }
    }

    throw lastError;
}

export function getRoads() {
    return requestJson("/roads");
}

export function getCurrentTraffic() {
    return requestJson("/current");
}

export function getTrend({ hours = 24, roadId } = {}) {
    return requestJson("/trend", {
        params: {
            hours,
            road_id: roadId,
        },
    });
}

export function getAlerts({ limit = 5 } = {}) {
    return requestJson("/alerts", {
        params: {
            limit,
        },
    });
}

export function getRoutes({ origin, destination } = {}) {
    return requestJson("/routes", {
        params: {
            origin,
            destination,
        },
    });
}

export function sendAssistantMessage({ question, history = [] } = {}) {
    return requestJson("/assistant/chat", {
        method: "POST",
        body: {
            question,
            history,
        },
    });
}

function parseSseBlock(block, onEvent) {
    const lines = block
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);

    for (const line of lines) {
        if (!line.startsWith("data:")) {
            continue;
        }

        const raw = line.slice(5).trim();
        if (!raw || raw === "[DONE]") {
            continue;
        }

        try {
            const payload = JSON.parse(raw);
            onEvent(payload);
        } catch (error) {
            console.error("Failed to parse assistant stream event:", error);
        }
    }
}

export async function streamAssistantMessage({ question, history = [], onEvent } = {}) {
    const response = await fetch(buildUrl("/assistant/chat/stream"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history }),
    });

    if (!response.ok) {
        throw new Error(`Stream request failed with status ${response.status}`);
    }

    if (!response.body) {
        throw new Error("Streaming is not supported in this browser environment");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) {
            break;
        }

        buffer += decoder.decode(value, { stream: true });

        let separatorIndex = buffer.search(/\r?\n\r?\n/);
        while (separatorIndex !== -1) {
            const block = buffer.slice(0, separatorIndex);
            const separatorLength = buffer[separatorIndex] === "\r" ? 4 : 2;
            buffer = buffer.slice(separatorIndex + separatorLength);
            parseSseBlock(block, onEvent);
            separatorIndex = buffer.search(/\r?\n\r?\n/);
        }
    }

    const tail = decoder.decode();
    if (tail) {
        buffer += tail;
    }

    if (buffer.trim()) {
        parseSseBlock(buffer, onEvent);
    }
}
