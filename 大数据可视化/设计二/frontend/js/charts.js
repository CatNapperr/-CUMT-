const SPEED_GOOD = "rgba(43, 228, 155, 0.96)";
const SPEED_MID = "rgba(255, 209, 102, 0.96)";
const SPEED_BAD = "rgba(255, 92, 112, 0.96)";

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function formatTime(value) {
    const date = value instanceof Date ? value : new Date(value);
    return new Intl.DateTimeFormat("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    }).format(date);
}

function formatDateTime(value) {
    const date = value instanceof Date ? value : new Date(value);
    return new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    }).format(date);
}

function interpolateColor(ratio) {
    const normalized = clamp(ratio, 0, 1);
    const stops = [
        { ratio: 0, color: [43, 228, 155] },
        { ratio: 0.5, color: [255, 209, 102] },
        { ratio: 1, color: [255, 92, 112] },
    ];

    const left = stops[normalized <= 0.5 ? 0 : 1];
    const right = stops[normalized <= 0.5 ? 1 : 2];
    const span = right.ratio - left.ratio;
    const inner = span === 0 ? 0 : (normalized - left.ratio) / span;
    const rgb = left.color.map((value, index) => Math.round(value + (right.color[index] - value) * inner));
    return `rgb(${rgb.join(",")})`;
}

function buildBarSeries(values) {
    const maxValue = Math.max(...values, 1);
    return values.map((value) => ({
        value,
        itemStyle: {
            color: interpolateColor(value / maxValue),
        },
    }));
}

function buildTrendGradient() {
    return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: "rgba(86, 168, 255, 0.52)" },
        { offset: 1, color: "rgba(86, 168, 255, 0.04)" },
    ]);
}

function formatGaugeAxisValue(value) {
    return `${Math.round(value)}`;
}

function createGaugeOption(summary) {
    const speedMax = 70;
    return {
        backgroundColor: "transparent",
        animationDuration: 1200,
        series: [
            {
                name: "平均速度",
                type: "gauge",
                center: ["30%", "58%"],
                radius: "78%",
                min: 0,
                max: speedMax,
                startAngle: 220,
                endAngle: -40,
                splitNumber: 7,
                axisLine: {
                    lineStyle: {
                        width: 16,
                        color: [
                            [0.5, "#2be49b"],
                            [0.75, "#ffd166"],
                            [1, "#ff5c70"],
                        ],
                    },
                },
                axisTick: { distance: -18, length: 8, lineStyle: { color: "#7da6d8" } },
                splitLine: { distance: -18, length: 16, lineStyle: { color: "#d8e9ff" } },
                axisLabel: {
                    color: "rgba(220, 232, 255, 0.82)",
                    distance: 18,
                    formatter: formatGaugeAxisValue,
                },
                pointer: { length: "68%", width: 5 },
                itemStyle: { color: SPEED_GOOD },
                title: {
                    offsetCenter: ["0%", "70%"],
                    color: "rgba(232, 241, 255, 0.88)",
                    fontSize: 14,
                },
                detail: {
                    valueAnimation: true,
                    formatter: (value) => `${Number(value).toFixed(1)} km/h`,
                    color: "#eaf4ff",
                    fontSize: 26,
                    offsetCenter: ["0%", "34%"],
                },
                data: [{ value: summary.averageSpeed, name: "平均速度" }],
            },
            {
                name: "拥堵指数",
                type: "gauge",
                center: ["74%", "58%"],
                radius: "78%",
                min: 0,
                max: 10,
                startAngle: 220,
                endAngle: -40,
                splitNumber: 5,
                axisLine: {
                    lineStyle: {
                        width: 16,
                        color: [
                            [0.35, "#2be49b"],
                            [0.7, "#ffd166"],
                            [1, "#ff5c70"],
                        ],
                    },
                },
                axisTick: { distance: -18, length: 8, lineStyle: { color: "#7da6d8" } },
                splitLine: { distance: -18, length: 16, lineStyle: { color: "#d8e9ff" } },
                axisLabel: {
                    color: "rgba(220, 232, 255, 0.82)",
                    distance: 18,
                    formatter: formatGaugeAxisValue,
                },
                pointer: { length: "68%", width: 5 },
                itemStyle: { color: SPEED_BAD },
                title: {
                    offsetCenter: ["0%", "70%"],
                    color: "rgba(232, 241, 255, 0.88)",
                    fontSize: 14,
                },
                detail: {
                    valueAnimation: true,
                    formatter: (value) => `${Number(value).toFixed(2)}`,
                    color: "#eaf4ff",
                    fontSize: 26,
                    offsetCenter: ["0%", "34%"],
                },
                data: [{ value: summary.congestionIndex, name: "拥堵指数" }],
            },
        ],
    };
}

function createBarOption(labels, values) {
    return {
        backgroundColor: "transparent",
        animationDuration: 900,
        animationDurationUpdate: 700,
        grid: {
            left: 28,
            right: 18,
            top: 34,
            bottom: 42,
            containLabel: true,
        },
        tooltip: {
            trigger: "axis",
            axisPointer: { type: "shadow" },
            backgroundColor: "rgba(7, 18, 36, 0.96)",
            borderColor: "rgba(111, 168, 255, 0.24)",
            textStyle: { color: "#ffffff" },
        },
        xAxis: {
            type: "category",
            data: labels,
            axisLabel: { color: "rgba(225, 236, 255, 0.76)", interval: 0, rotate: 18 },
            axisLine: { lineStyle: { color: "rgba(164, 195, 255, 0.3)" } },
            axisTick: { show: false },
        },
        yAxis: {
            type: "value",
            axisLabel: { color: "rgba(225, 236, 255, 0.7)" },
            splitLine: { lineStyle: { color: "rgba(255, 255, 255, 0.08)" } },
        },
        series: [
            {
                type: "bar",
                data: buildBarSeries(values),
                barWidth: "56%",
                label: {
                    show: true,
                    position: "top",
                    color: "#dff1ff",
                },
                itemStyle: {
                    borderRadius: [8, 8, 0, 0],
                },
                emphasis: {
                    itemStyle: {
                        shadowBlur: 18,
                        shadowColor: "rgba(86, 168, 255, 0.36)",
                    },
                },
            },
        ],
    };
}

function createTrendOption(timestamps, volumes) {
    return {
        backgroundColor: "transparent",
        animationDuration: 1100,
        grid: {
            left: 28,
            right: 18,
            top: 34,
            bottom: 42,
            containLabel: true,
        },
        tooltip: {
            trigger: "axis",
            backgroundColor: "rgba(7, 18, 36, 0.96)",
            borderColor: "rgba(111, 168, 255, 0.24)",
            textStyle: { color: "#ffffff" },
        },
        xAxis: {
            type: "category",
            data: timestamps.map(formatTime),
            boundaryGap: false,
            axisLabel: { color: "rgba(225, 236, 255, 0.76)" },
            axisLine: { lineStyle: { color: "rgba(164, 195, 255, 0.3)" } },
        },
        yAxis: {
            type: "value",
            axisLabel: { color: "rgba(225, 236, 255, 0.7)" },
            splitLine: { lineStyle: { color: "rgba(255, 255, 255, 0.08)" } },
        },
        series: [
            {
                name: "5 分钟总流量",
                type: "line",
                smooth: true,
                symbol: "circle",
                symbolSize: 8,
                showSymbol: false,
                data: volumes,
                lineStyle: {
                    width: 3,
                    color: "#56a8ff",
                },
                areaStyle: {
                    color: buildTrendGradient(),
                },
                itemStyle: {
                    color: "#56a8ff",
                },
            },
        ],
    };
}

function renderRollingRows(items) {
    if (items.length === 0) {
        return `
      <tr class="is-current"><td>暂无数据</td><td>0</td><td>0.00</td><td>--</td></tr>
      <tr><td>暂无数据</td><td>0</td><td>0.00</td><td>--</td></tr>
    `;
    }

    const rows = items.map((item, index) => `
    <tr class="${index === 0 ? "is-current" : ""}">
      <td>${item.road_name}</td>
      <td>${item.volume}</td>
      <td>${Number(item.speed).toFixed(2)} km/h</td>
      <td>${formatDateTime(item.timestamp)}</td>
    </tr>
  `).join("");

    return `${rows}${rows}`;
}

export function createDashboardCharts() {
    const barChart = echarts.init(document.getElementById("bar-chart"));
    const trendChart = echarts.init(document.getElementById("trend-chart"));
    const gaugeChart = echarts.init(document.getElementById("gauge-chart"));
    const tableBody = document.getElementById("latest-table-body");
    const tableWrap = document.querySelector(".table-wrap");

    function resize() {
        barChart.resize();
        trendChart.resize();
        gaugeChart.resize();
    }

    function setBarChart(roads, currentItems) {
        const itemByRoadId = new Map(currentItems.map((item) => [item.road_id, item]));
        const labels = roads.length > 0 ? roads.map((road) => road.name) : currentItems.map((item) => item.road_name);
        const values = roads.length > 0
            ? roads.map((road) => itemByRoadId.get(road.id)?.volume ?? 0)
            : currentItems.map((item) => item.volume);

        barChart.setOption(createBarOption(labels, values), true);
    }

    function setTrendChart(trend) {
        const timestamps = trend.timestamps.map((value) => new Date(value));
        trendChart.setOption(createTrendOption(timestamps, trend.volumes), true);
    }

    function setGaugeChart(summary) {
        gaugeChart.setOption(createGaugeOption(summary), true);
    }

    function setRollingTable(currentItems) {
        tableBody.innerHTML = renderRollingRows(currentItems);
        const rowCount = Math.max(currentItems.length, 1);
        const duration = Math.max(12, rowCount * 2.2);
        tableWrap.style.setProperty("--scroll-duration", `${duration}s`);
    }

    return {
        resize,
        setBarChart,
        setTrendChart,
        setGaugeChart,
        setRollingTable,
    };
}

export function buildSummary(roads, currentItems) {
    const totalVolume = currentItems.reduce((sum, item) => sum + Number(item.volume || 0), 0);
    const weightedSpeed = totalVolume > 0
        ? currentItems.reduce((sum, item) => sum + Number(item.speed || 0) * Number(item.volume || 0), 0) / totalVolume
        : 0;

    const roadSpeedBase = roads.length > 0
        ? roads.reduce((sum, road) => sum + Number(road.free_flow_speed || 0), 0) / roads.length
        : 0;

    const congestionIndex = clamp(10 * (roadSpeedBase > 0 ? 1 - weightedSpeed / roadSpeedBase : 0), 0, 10);

    return {
        totalVolume,
        averageSpeed: weightedSpeed,
        congestionIndex,
        freeFlowAverage: roadSpeedBase,
    };
}
