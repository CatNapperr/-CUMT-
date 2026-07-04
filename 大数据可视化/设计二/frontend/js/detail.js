import { getCurrentTraffic, getRoads, getTrend } from "./api.js";
import { buildSummary, createDashboardCharts } from "./charts.js";

const refs = {
    currentTime: document.getElementById("current-time"),
    statusBadge: document.getElementById("status-badge"),
};

const state = {
    roads: [],
    currentItems: [],
    trend: { timestamps: [], volumes: [], speeds: [], occupancies: [] },
    charts: createDashboardCharts(),
};

function formatClock(date) {
    return new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    }).format(date);
}

function setStatus(text, tone = "neutral") {
    refs.statusBadge.textContent = text;
    refs.statusBadge.dataset.tone = tone;
}

function updateClock() {
    refs.currentTime.textContent = formatClock(new Date());
}

function updateKpis() {
    const summary = buildSummary(state.roads, state.currentItems);
    state.charts.setGaugeChart(summary);
}

function updateCurrentView() {
    state.charts.setBarChart(state.roads, state.currentItems);
    state.charts.setRollingTable(state.currentItems);
    updateKpis();
}

async function refreshRoads() {
    state.roads = await getRoads();
}

async function refreshCurrent() {
    const payload = await getCurrentTraffic();
    state.currentItems = Array.isArray(payload.items) ? payload.items : [];
    updateCurrentView();
    setStatus(`实时数据 ${formatClock(new Date(payload.timestamp))}`, "active");
}

async function refreshTrend() {
    state.trend = await getTrend({ hours: 24 });
    state.charts.setTrendChart(state.trend);
}

async function loadInitialData() {
    setStatus("正在加载数据", "loading");
    try {
        await refreshRoads();
        await Promise.all([refreshCurrent(), refreshTrend()]);
        setStatus("运行正常", "active");
    } catch (error) {
        console.error(error);
        setStatus("数据加载失败，自动重试中", "error");
    }
}

function startTimers() {
    window.setInterval(updateClock, 1000);
    window.setInterval(async () => {
        try {
            await refreshCurrent();
        } catch (error) {
            console.error(error);
            setStatus("实时数据刷新失败，重试中", "error");
        }
    }, 5000);

    window.setInterval(async () => {
        try {
            await refreshTrend();
        } catch (error) {
            console.error(error);
            setStatus("趋势数据刷新失败，重试中", "error");
        }
    }, 120000);
}

function bindEvents() {
    window.addEventListener("resize", () => state.charts.resize());
}

async function bootstrap() {
    updateClock();
    bindEvents();
    await loadInitialData();
    startTimers();
}

bootstrap();