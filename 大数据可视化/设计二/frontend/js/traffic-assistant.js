import { DISTRICT_OPTIONS, getRoadProfile } from "./city-data.js";
import { sendAssistantMessage, streamAssistantMessage } from "./api.js";

function normalizeText(value) {
    return String(value ?? "")
        .trim()
        .replace(/[？?。！!，,；;\s]+/g, " ")
        .replace(/\s+/g, " ");
}

function formatNumber(value, fractionDigits = 1) {
    return Number(value || 0).toFixed(fractionDigits);
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function nowLabel() {
    return new Intl.DateTimeFormat("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date());
}

function isQuestionAboutRoutes(text) {
    return /怎么走|路线|绕行|通行|到.*(怎么走|路线|绕行)/.test(text);
}

function isQuestionAboutOverview(text) {
    return /概览|总览|整体|当前情况|全局|汇总/.test(text);
}

function isQuestionAboutRisk(text) {
    return /最堵|拥堵|风险|预警|异常|高峰/.test(text);
}

function findDistricts(text) {
    return DISTRICT_OPTIONS.filter((district) => text.includes(district));
}

function findRoadMention(text, roads = [], currentItems = []) {
    const allRoadNames = new Map();

    roads.forEach((road) => {
        allRoadNames.set(String(road.name ?? ""), road);
    });

    currentItems.forEach((item) => {
        allRoadNames.set(String(item.road_name ?? ""), item);
    });

    for (const [name, value] of allRoadNames.entries()) {
        if (name && text.includes(name)) {
            return value;
        }
    }

    return null;
}

function buildDistrictStats(roads = [], currentItems = []) {
    const itemsByRoadId = new Map(currentItems.map((item) => [Number(item.road_id), item]));
    const districtMap = new Map();

    roads.forEach((road) => {
        const profile = getRoadProfile(road.id);
        const current = itemsByRoadId.get(Number(road.id));
        const bucket = districtMap.get(profile.district) ?? {
            district: profile.district,
            roadCount: 0,
            totalOccupancy: 0,
            totalVolume: 0,
            totalSpeed: 0,
            currentCount: 0,
        };

        bucket.roadCount += 1;
        if (current) {
            bucket.totalOccupancy += Number(current.occupancy ?? 0);
            bucket.totalVolume += Number(current.volume ?? 0);
            bucket.totalSpeed += Number(current.speed ?? 0);
            bucket.currentCount += 1;
        }

        districtMap.set(profile.district, bucket);
    });

    return Array.from(districtMap.values()).map((item) => ({
        ...item,
        averageOccupancy: item.currentCount ? item.totalOccupancy / item.currentCount : 0,
        averageVolume: item.currentCount ? item.totalVolume / item.currentCount : 0,
        averageSpeed: item.currentCount ? item.totalSpeed / item.currentCount : 0,
    }));
}

function pickTopCongestion(districtStats) {
    return [...districtStats].sort((a, b) => b.averageOccupancy - a.averageOccupancy)[0] ?? null;
}

function pickTopAlert(alerts = []) {
    return [...alerts].sort((a, b) => Number(b.risk_score ?? 0) - Number(a.risk_score ?? 0))[0] ?? null;
}

function summarizeRoad(road, currentItems = []) {
    if (!road) {
        return "没有找到匹配的路段。你可以直接说出路名，或者问某个区县的路况。";
    }

    const roadId = Number(road.id ?? road.road_id ?? 0);
    const profile = getRoadProfile(roadId);
    const current = currentItems.find((item) => Number(item.road_id) === roadId);

    if (!current) {
        return `${road.road_name ?? profile.roadName} 属于${profile.district}，当前没有实时数值，但它已纳入监测列表。`;
    }

    return `${road.road_name ?? current.road_name ?? profile.roadName} 位于${profile.district}，当前流量 ${Number(current.volume ?? 0).toLocaleString("zh-CN")}，速度 ${formatNumber(current.speed, 2)} km/h，拥堵指数 ${formatNumber(current.occupancy, 2)}。`;
}

function summarizeOverview({ roads = [], currentItems = [], alerts = [], routes = [] }) {
    const districtStats = buildDistrictStats(roads, currentItems);
    const topDistrict = pickTopCongestion(districtStats);
    const topAlert = pickTopAlert(alerts);
    const topRoute = routes[0];
    const totalVolume = currentItems.reduce((sum, item) => sum + Number(item.volume ?? 0), 0);
    const averageSpeed = currentItems.length
        ? currentItems.reduce((sum, item) => sum + Number(item.speed ?? 0), 0) / currentItems.length
        : 0;

    const lines = [
        `当前覆盖 ${roads.length} 条监测路段，总流量约 ${totalVolume.toLocaleString("zh-CN")}，平均速度 ${formatNumber(averageSpeed, 2)} km/h。`,
    ];

    if (topDistrict) {
        lines.push(`拥堵压力最高的区域是 ${topDistrict.district}，平均拥堵指数 ${formatNumber(topDistrict.averageOccupancy, 2)}。`);
    }

    if (topAlert) {
        lines.push(`风险最高的预警来自 ${topAlert.road_name}，等级 ${topAlert.risk_level}，评分 ${formatNumber(topAlert.risk_score, 0)}。`);
    }

    if (topRoute) {
        lines.push(`系统当前优先推荐 ${topRoute.route_name}，预计 ${formatNumber(topRoute.estimated_minutes, 1)} 分钟。`);
    }

    return lines.join("\n");
}

function answerQuestion(question, context) {
    const text = normalizeText(question);
    const { roads = [], currentItems = [], alerts = [], routes = [] } = context;

    if (!text) {
        return "请输入一个问题，例如：今天哪个区最堵、鼓楼区到铜山区怎么走、徐贾快速路现在情况如何。";
    }

    const road = findRoadMention(text, roads, currentItems);
    if (road) {
        return summarizeRoad(road, currentItems);
    }

    const districts = findDistricts(text);
    if (isQuestionAboutRoutes(text) && districts.length >= 2) {
        const [origin, destination] = districts;
        const matched = routes.find((route) => route.districts?.[0] === origin && route.districts?.[route.districts.length - 1] === destination);

        if (matched) {
            return `${origin} 到 ${destination} 的推荐结果是 ${matched.route_name}，预计 ${formatNumber(matched.estimated_minutes, 1)} 分钟，风险分数 ${formatNumber(matched.risk_score, 0)}。\n经过线路：${matched.corridors.join(" / ")}`;
        }

        return `${origin} 到 ${destination} 当前没有直接匹配的推荐路径，但你可以切换到绕行推荐面板查看备选线路。`;
    }

    if (districts.length === 1) {
        const district = districts[0];
        const districtStats = buildDistrictStats(roads, currentItems).find((item) => item.district === district);
        const districtAlerts = alerts.filter((item) => item.district === district);

        if (districtStats) {
            const alertText = districtAlerts.length
                ? `，其中最高预警为 ${districtAlerts[0].road_name}（${districtAlerts[0].risk_level}）`
                : "，当前暂无该区的高风险预警";

            return `${district} 当前共有 ${districtStats.roadCount} 条监测路段，平均拥堵指数 ${formatNumber(districtStats.averageOccupancy, 2)}，平均速度 ${formatNumber(districtStats.averageSpeed, 2)} km/h${alertText}。`;
        }

        return `${district} 已在系统区划中，但当前没有匹配到实时路段数据。`;
    }

    if (isQuestionAboutRisk(text) && alerts.length) {
        const topAlert = pickTopAlert(alerts);
        return `当前最需要关注的是 ${topAlert.road_name}，位于 ${topAlert.district}，风险等级 ${topAlert.risk_level}，评分 ${formatNumber(topAlert.risk_score, 0)}。建议：${topAlert.recommendation}`;
    }

    if (isQuestionAboutOverview(text)) {
        return summarizeOverview(context);
    }

    return [
        "我可以基于当前监测数据回答这些问题：",
        "1. 今天哪个区最堵",
        "2. 某个区县现在路况如何",
        "3. 鼓楼区到铜山区怎么走",
        "4. 某条路现在的速度、流量和拥堵情况",
        "如果你愿意，我也可以直接给你一段当前交通概览。",
    ].join("\n");
}

function createMessage(role, content, options = {}) {
    return {
        role,
        content,
        time: nowLabel(),
        type: options.type ?? "text",
        done: options.done ?? true,
        steps: options.steps ?? [],
        reasoning: options.reasoning ?? "",
        provider: options.provider ?? "",
        model: options.model ?? "",
    };
}

function renderMessage(message) {
    if (message.type === "thinking") {
        const stepsMarkup = (message.steps || []).map((step) => `<li>${escapeHtml(step)}</li>`).join("");
        const reasoningMarkup = message.reasoning
            ? `<div class="qa-thinking-live">${escapeHtml(message.reasoning).replace(/\n/g, "<br />")}</div>`
            : "";
        const statusText = message.done ? "思考完成" : "正在思考";
        const loaderMarkup = message.done ? "" : '<span class="qa-thinking-loader"><span></span><span></span><span></span></span>';

        return `
        <div class="qa-message qa-message-thinking" data-role="assistant">
            <div class="qa-bubble qa-bubble-thinking">
                <div class="qa-thinking-head">
                    <span class="qa-thinking-status">${statusText}</span>
                    ${loaderMarkup}
                </div>
                ${stepsMarkup ? `<ul class="qa-thinking-steps">${stepsMarkup}</ul>` : ""}
                ${reasoningMarkup}
            </div>
            <div class="qa-meta">AI 助手 · ${message.time}</div>
        </div>
        `;
    }

    const providerMeta = message.provider ? ` · ${escapeHtml(message.provider)}${message.model ? `(${escapeHtml(message.model)})` : ""}` : "";
    const streamingClass = message.type === "answer" && !message.done ? " qa-bubble-streaming" : "";

    return `
        <div class="qa-message" data-role="${message.role}">
            <div class="qa-bubble${streamingClass}">${escapeHtml(message.content).replace(/\n/g, "<br />")}</div>
            <div class="qa-meta">${message.role === "assistant" ? "AI 助手" : "你"}${providerMeta} · ${message.time}</div>
        </div>
    `;
}

export function createTrafficAssistant(getContext) {
    const modal = document.getElementById("qa-modal");
    const openButton = document.getElementById("qa-open");
    const closeButton = document.getElementById("qa-close");
    const form = document.getElementById("qa-form");
    const input = document.getElementById("qa-input");
    const messages = document.getElementById("qa-messages");
    const sendButton = form.querySelector(".qa-send");
    const suggestionButtons = Array.from(modal.querySelectorAll("[data-qa-question]"));

    const conversation = [
        createMessage("assistant", "你好，我是 AI 交通问答助手。你可以问我当前路况、最堵区域、某个区县的交通情况，或者让我解释一条绕行推荐。"),
    ];

    let isResponding = false;

    function getHistoryPayload() {
        return conversation
            .filter((item) => item.role === "user" || (item.role === "assistant" && item.type !== "thinking"))
            .slice(-8)
            .map((item) => ({
                role: item.role,
                content: item.content,
            }));
    }

    function renderConversation() {
        messages.innerHTML = conversation.map(renderMessage).join("");
        messages.scrollTop = messages.scrollHeight;
    }

    function open() {
        modal.hidden = false;
        document.body.style.overflow = "hidden";
        window.setTimeout(() => input.focus(), 0);
    }

    function close() {
        modal.hidden = true;
        document.body.style.overflow = "";
        openButton.focus();
    }

    function setRespondingState(flag) {
        isResponding = flag;
        input.disabled = flag;
        sendButton.disabled = flag;
        suggestionButtons.forEach((button) => {
            button.disabled = flag;
        });
    }

    function appendThinkingStep(thinkingMessage, text) {
        const value = String(text || "").trim();
        if (!value) {
            return;
        }
        const steps = thinkingMessage.steps || [];
        if (!steps.length || steps[steps.length - 1] !== value) {
            steps.push(value);
        }
        if (steps.length > 10) {
            steps.splice(0, steps.length - 10);
        }
        thinkingMessage.steps = steps;
    }

    function appendReasoningDelta(thinkingMessage, delta) {
        const text = String(delta || "");
        if (!text) {
            return;
        }

        thinkingMessage.reasoning = `${thinkingMessage.reasoning || ""}${text}`;
        if (thinkingMessage.reasoning.length > 1600) {
            thinkingMessage.reasoning = thinkingMessage.reasoning.slice(-1600);
        }
    }

    async function sendQuestion(question) {
        const content = String(question ?? "").trim();
        if (!content || isResponding) {
            return;
        }

        const historyPayload = getHistoryPayload();

        setRespondingState(true);

        conversation.push(createMessage("user", content));
        renderConversation();

        const thinkingMessage = createMessage("assistant", "", {
            type: "thinking",
            done: false,
            steps: ["正在建立交通问题分析上下文..."],
            reasoning: "",
        });
        const answerMessage = createMessage("assistant", "", {
            type: "answer",
            done: false,
        });

        conversation.push(thinkingMessage);
        conversation.push(answerMessage);
        renderConversation();

        let streamDone = false;

        try {
            await streamAssistantMessage({
                question: content,
                history: historyPayload,
                onEvent(event) {
                    if (!event || typeof event !== "object") {
                        return;
                    }

                    if (event.type === "thinking") {
                        appendThinkingStep(thinkingMessage, event.text);
                    } else if (event.type === "thinking_delta") {
                        appendReasoningDelta(thinkingMessage, event.text);
                    } else if (event.type === "answer_delta") {
                        answerMessage.content += String(event.text || "");
                    } else if (event.type === "done") {
                        streamDone = true;
                        answerMessage.provider = String(event.provider || "");
                        answerMessage.model = String(event.model || "");
                    }

                    renderConversation();
                },
            });

            if (!answerMessage.content.trim()) {
                const context = getContext();
                answerMessage.content = answerQuestion(content, context);
            }
        } catch (error) {
            console.error(error);

            appendThinkingStep(thinkingMessage, "流式通道不可用，已切换标准问答模式。");
            try {
                const context = getContext();
                const response = await sendAssistantMessage({
                    question: content,
                    history: historyPayload,
                });
                answerMessage.content = response.answer || answerQuestion(content, context);
                answerMessage.provider = String(response.provider || "fallback");
                answerMessage.model = String(response.model || "local");
            } catch (innerError) {
                console.error(innerError);
                answerMessage.content = answerQuestion(content, getContext());
                answerMessage.provider = "fallback";
                answerMessage.model = "local";
            }
        } finally {
            thinkingMessage.done = true;
            answerMessage.done = true;

            if (!streamDone && !answerMessage.provider) {
                answerMessage.provider = "fallback";
            }

            setRespondingState(false);
            renderConversation();
        }
    }

    openButton.addEventListener("click", open);
    closeButton.addEventListener("click", close);

    modal.addEventListener("click", (event) => {
        if (event.target instanceof HTMLElement && event.target.dataset.qaClose === "true") {
            close();
        }
    });

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        sendQuestion(input.value).catch((error) => console.error(error));
        input.value = "";
    });

    messages.parentElement?.addEventListener("click", () => {
        if (!isResponding) {
            input.focus();
        }
    });

    suggestionButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const value = button.getAttribute("data-qa-question") ?? button.textContent ?? "";
            sendQuestion(value).catch((error) => console.error(error));
            input.value = "";
            input.focus();
        });
    });

    window.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modal.hidden) {
            close();
        }
    });

    renderConversation();

    return {
        open,
        close,
        sendQuestion,
    };
}