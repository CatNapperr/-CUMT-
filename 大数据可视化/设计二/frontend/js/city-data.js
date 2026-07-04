export const DISTRICT_OPTIONS = [
    "鼓楼区",
    "云龙区",
    "泉山区",
    "铜山区",
    "贾汪区",
    "丰县",
    "沛县",
    "邳州市",
    "睢宁县",
    "新沂市",
];

export const DEFAULT_ROUTE = {
    origin: "鼓楼区",
    destination: "铜山区",
};

export const ROAD_CITY_PROFILE = {
    1: { roadName: "徐贾快速路", district: "铜山区", coordinate: [117.115, 34.198] },
    2: { roadName: "淮海东路", district: "云龙区", coordinate: [117.285, 34.245] },
    3: { roadName: "中山北路", district: "鼓楼区", coordinate: [117.191, 34.288] },
    4: { roadName: "泉山南路", district: "泉山区", coordinate: [117.173, 34.206] },
    5: { roadName: "贾汪连接线", district: "贾汪区", coordinate: [117.452, 34.442] },
    6: { roadName: "丰县东环路", district: "丰县", coordinate: [116.600, 34.700] },
    7: { roadName: "沛县迎宾大道", district: "沛县", coordinate: [116.930, 34.730] },
    8: { roadName: "邳州运河路", district: "邳州市", coordinate: [118.020, 34.330] },
    9: { roadName: "睢宁中央大街", district: "睢宁县", coordinate: [117.950, 33.890] },
    10: { roadName: "新沂新安大道", district: "新沂市", coordinate: [118.350, 34.380] },
};

export function getRoadProfile(roadId) {
    return ROAD_CITY_PROFILE[roadId] ?? {
        roadName: `路段 ${roadId}`,
        district: "未知",
        coordinate: [117.18, 34.25],
    };
}