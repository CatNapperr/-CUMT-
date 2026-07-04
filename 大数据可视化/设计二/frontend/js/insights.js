import { DEFAULT_ROUTE, DISTRICT_OPTIONS } from "./city-data.js";

function formatNumber(value, fractionDigits = 1) {
    return Number(value || 0).toFixed(fractionDigits);
}

function createAlertCard(alert) {
    return `
    <li class="alert-item">
      <div class="alert-top">
        <div>
          <div class="alert-name">${alert.road_name}</div>
          <div class="alert-district">${alert.district}</div>
        </div>
        <span class="alert-level" data-level="${alert.risk_level}">${alert.risk_level}</span>
      </div>
      <div class="alert-bar"><span style="width: ${formatNumber(alert.risk_score, 0)}%"></span></div>
      <div class="alert-reason">风险分数 ${formatNumber(alert.risk_score, 0)} / 100，${alert.reason}</div>
      <div class="alert-recommendation">${alert.recommendation}</div>
      <div class="route-meta">预计流量 ${alert.predicted_volume} · 预测速度 ${formatNumber(alert.predicted_speed, 2)} km/h</div>
    </li>
  `;
}

function createRouteCard(route) {
    return `
    <li class="route-item">
      <div class="route-top">
        <div class="route-name">${route.route_name}</div>
        <div class="route-score">${formatNumber(route.risk_score, 0)} / 100</div>
      </div>
      <div class="route-summary">${route.summary}</div>
      <div class="route-path">${route.districts.join(" → ")}</div>
      <div class="route-corridors">经过：${route.corridors.join(" / ")}</div>
      <div class="route-meta">预计 ${formatNumber(route.estimated_minutes, 1)} 分钟</div>
    </li>
  `;
}

function renderEmptyState(text) {
    return `<div class="empty-state">${text}</div>`;
}

export function createInsightBoard() {
    const alertList = document.getElementById("alert-list");
    const routeList = document.getElementById("route-list");
    const routeOrigin = document.getElementById("route-origin");
    const routeDestination = document.getElementById("route-destination");
    const routeRefresh = document.getElementById("route-refresh");

    function setDistrictOptions() {
        const optionsMarkup = DISTRICT_OPTIONS.map((district) => `<option value="${district}">${district}</option>`).join("");
        routeOrigin.innerHTML = optionsMarkup;
        routeDestination.innerHTML = optionsMarkup;
        routeOrigin.value = DEFAULT_ROUTE.origin;
        routeDestination.value = DEFAULT_ROUTE.destination;
    }

    function getRouteQuery() {
        return {
            origin: routeOrigin.value,
            destination: routeDestination.value,
        };
    }

    function renderAlerts(alerts) {
        if (!alerts.length) {
            alertList.innerHTML = renderEmptyState("当前没有高风险路段");
            return;
        }

        alertList.innerHTML = alerts.map(createAlertCard).join("");
    }

    function renderRoutes(routes) {
        if (!routes.length) {
            routeList.innerHTML = renderEmptyState("当前起终点暂无可用路径");
            return;
        }

        routeList.innerHTML = routes.map(createRouteCard).join("");
    }

    function bindRouteRefresh(handler) {
        routeRefresh.addEventListener("click", handler);
        routeOrigin.addEventListener("change", handler);
        routeDestination.addEventListener("change", handler);
    }

    return {
        setDistrictOptions,
        getRouteQuery,
        renderAlerts,
        renderRoutes,
        bindRouteRefresh,
    };
}