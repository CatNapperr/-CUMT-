import { getRoadProfile } from "./city-data.js";

const MAP_URL = "./assets/xuzhou_full.json";

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

async function loadXuzhouMap() {
    const response = await fetch(MAP_URL);
    if (!response.ok) {
        throw new Error(`Failed to load Xuzhou map: ${response.status}`);
    }

    const geojson = await response.json();
    echarts.registerMap("xuzhou", geojson);
}

function buildDistrictData(roads, currentItems) {
    const districtTotals = new Map();
    const districtCounts = new Map();
    const currentByRoadId = new Map(currentItems.map((item) => [item.road_id, item]));

    roads.forEach((road) => {
        const profile = getRoadProfile(road.id);
        const current = currentByRoadId.get(road.id);
        const volume = Number(current?.volume ?? 0);
        const occupancy = Number(current?.occupancy ?? 0);
        const score = volume > 0 ? occupancy : 0;

        districtTotals.set(profile.district, (districtTotals.get(profile.district) ?? 0) + score);
        districtCounts.set(profile.district, (districtCounts.get(profile.district) ?? 0) + 1);
    });

    return Array.from(districtCounts.entries()).map(([district, count]) => ({
        name: district,
        value: roundOne((districtTotals.get(district) ?? 0) / count),
    }));
}

function buildRoadMarkers(currentItems) {
    return currentItems.map((item) => {
        const profile = getRoadProfile(item.road_id);
        return {
            name: item.road_name,
            value: [...profile.coordinate, Number(item.volume) || 0],
            district: profile.district,
            volume: item.volume,
            speed: item.speed,
            occupancy: item.occupancy,
        };
    });
}

function roundOne(value) {
    return Math.round(value * 10) / 10;
}

function buildMapOption(districtData, roadMarkers) {
    const maxValue = Math.max(...districtData.map((item) => item.value), 1);

    return {
        backgroundColor: "transparent",
        animationDuration: 1000,
        tooltip: {
            trigger: "item",
            backgroundColor: "rgba(7, 18, 36, 0.96)",
            borderColor: "rgba(111, 168, 255, 0.24)",
            textStyle: { color: "#ffffff" },
            formatter(params) {
                if (params.seriesType === "scatter") {
                    return `
            <strong>${params.data.name}</strong><br/>
            所属区域：${params.data.district}<br/>
            流量：${params.data.volume}<br/>
            速度：${Number(params.data.speed).toFixed(2)} km/h<br/>
            拥堵：${Number(params.data.occupancy).toFixed(2)}
          `;
                }

                return `
          <strong>${params.name}</strong><br/>
          热度值：${Number(params.value ?? 0).toFixed(1)}
        `;
            },
        },
        visualMap: {
            min: 0,
            max: maxValue,
            left: 16,
            bottom: 10,
            text: ["高", "低"],
            calculable: true,
            orient: "horizontal",
            itemWidth: 50,
            itemHeight: 200,
            inRange: {
                color: ["#173d66", "#2b7fff", "#46d39a", "#f2d96b", "#ff6b70"],
            },
            textStyle: { color: "rgba(231, 241, 255, 0.8)", fontSize: 11 },
        },
        geo: {
            map: "xuzhou",
            roam: true,
            zoom: 1.22,
            label: {
                show: true,
                color: "#eaf4ff",
                fontSize: 12,
            },
            itemStyle: {
                areaColor: "rgba(14, 30, 58, 0.92)",
                borderColor: "rgba(112, 180, 255, 0.45)",
                borderWidth: 1,
            },
            emphasis: {
                itemStyle: {
                    areaColor: "rgba(76, 138, 255, 0.35)",
                },
                label: { color: "#ffffff" },
            },
        },
        series: [
            {
                name: "区域热度",
                type: "map",
                map: "xuzhou",
                geoIndex: 0,
                data: districtData,
                emphasis: {
                    label: { color: "#ffffff" },
                },
            },
            {
                name: "路段点位",
                type: "scatter",
                coordinateSystem: "geo",
                symbolSize(value) {
                    return clamp(10 + (Number(value[2]) || 0) / 160, 10, 22);
                },
                data: roadMarkers,
                itemStyle: {
                    color: "#ffffff",
                    shadowBlur: 18,
                    shadowColor: "rgba(86, 168, 255, 0.5)",
                },
                label: {
                    show: true,
                    formatter: "{b}",
                    position: "top",
                    color: "#f0f8ff",
                    fontSize: 11,
                },
            },
        ],
    };
}

export async function createXuzhouMapChart(container) {
    await loadXuzhouMap();
    const chart = echarts.init(container);

    function setData(roads, currentItems) {
        const districtData = buildDistrictData(roads, currentItems);
        const roadMarkers = buildRoadMarkers(currentItems);
        chart.setOption(buildMapOption(districtData, roadMarkers), true);
    }

    function resize() {
        chart.resize();
    }

    return {
        setData,
        resize,
    };
}