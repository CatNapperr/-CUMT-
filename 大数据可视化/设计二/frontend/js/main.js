import { getAlerts, getCurrentTraffic, getRoads, getRoutes } from "./api.js";
import { buildSummary } from "./charts.js";
import { createInsightBoard } from "./insights.js";
import { createTrafficAssistant } from "./traffic-assistant.js";
import { createXuzhouMapChart } from "./xuzhou-map.js";

const refs = {
    currentTime: document.getElementById("current-time"),
    statusBadge: document.getElementById("status-badge"),
    totalVolume: document.getElementById("kpi-total-volume"),
    averageSpeed: document.getElementById("kpi-average-speed"),
    congestionIndex: document.getElementById("kpi-congestion-index"),
};

const state = {
    roads: [],
    currentItems: [],
    latestAlerts: [],
    latestRoutes: [],
    mapChart: null,
    insights: createInsightBoard(),
};

const assistant = createTrafficAssistant(() => ({
    roads: state.roads,
    currentItems: state.currentItems,
    alerts: state.latestAlerts,
    routes: state.latestRoutes,
}));

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
    refs.totalVolume.textContent = summary.totalVolume.toLocaleString("zh-CN");
    refs.averageSpeed.textContent = summary.averageSpeed.toFixed(2);
    refs.congestionIndex.textContent = summary.congestionIndex.toFixed(2);
}

function updateCurrentView() {
    if (state.mapChart) {
        state.mapChart.setData(state.roads, state.currentItems);
    }
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

async function refreshInsights() {
    const { origin, destination } = state.insights.getRouteQuery();
    const [alertsPayload, routesPayload] = await Promise.all([
        getAlerts({ limit: 5 }),
        getRoutes({ origin, destination }),
    ]);
    state.latestAlerts = alertsPayload.alerts ?? [];
    state.latestRoutes = routesPayload.options ?? [];
    state.insights.renderAlerts(state.latestAlerts);
    state.insights.renderRoutes(state.latestRoutes);
}

async function loadInitialData() {
    setStatus("正在加载数据", "loading");
    try {
        await refreshRoads();
        try {
            state.mapChart = await createXuzhouMapChart(document.getElementById("xuzhou-map"));
        } catch (error) {
            console.error(error);
            state.mapChart = null;
            setStatus("徐州地图加载失败，继续展示基础数据", "error");
        }
        state.insights.setDistrictOptions();
        state.insights.bindRouteRefresh(() => {
            refreshInsights().catch((error) => {
                console.error(error);
                setStatus("绕行推荐刷新失败，重试中", "error");
            });
        });
        await refreshCurrent();
        try {
            await refreshInsights();
        } catch (error) {
            console.error(error);
            setStatus("预警或路线服务暂不可用", "error");
        }
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

        try {
            await refreshInsights();
        } catch (error) {
            console.error(error);
            setStatus("预警或路线服务刷新失败，重试中", "error");
        }
    }, 5000);
}

function bindEvents() {
    window.addEventListener("resize", () => {
        if (state.mapChart) {
            state.mapChart.resize();
        }
    });
}

async function bootstrap() {
    updateClock();
    bindEvents();
    await loadInitialData();
    startTimers();
}

bootstrap();
