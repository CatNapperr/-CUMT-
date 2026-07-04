from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import DEEPSEEK_API_BASE, DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_SYSTEM_PROMPT, DEEPSEEK_TIMEOUT
from backend.database import get_db
from backend.models import RoadSegment, TrafficHistory
from backend.schemas import TrafficChatRequest, TrafficChatResponse
from backend.simulator.generator import build_current_snapshot
from backend.simulator.insights import DISTRICT_OPTIONS, predict_traffic_alerts, recommend_routes, build_city_district_load

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _iter_text_chunks(text: str, chunk_size: int = 28) -> Iterator[str]:
    value = str(text or "")
    for index in range(0, len(value), chunk_size):
        yield value[index : index + chunk_size]


def _build_thinking_steps(question: str) -> list[str]:
    districts = _detect_districts(question)
    steps = [
        "正在解析问题意图（路况查询/路线推荐/风险预警）...",
        "正在提取关键实体（区县、路段、时段）...",
        "正在读取实时路况、预警和绕行候选...",
    ]

    if len(districts) >= 2:
        steps.append(f"已识别起终点：{districts[0]} -> {districts[1]}，正在对比路线方案...")
    elif len(districts) == 1:
        steps.append(f"已识别区域：{districts[0]}，正在聚合该区路况证据...")
    else:
        steps.append("未识别到明确区县，正在按全局交通态势进行推理...")

    steps.append("正在组织结构化回答（结论、依据、建议）...")
    return steps


def _build_deepseek_messages(question: str, context: str, history: list[dict[str, str]]) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": DEEPSEEK_SYSTEM_PROMPT}]
    if history:
        for item in history[-6:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": str(content)})

    messages.append(
        {
            "role": "user",
            "content": (
                "请基于下面的实时交通数据回答我的问题。\n\n"
                f"实时数据：\n{context}\n\n"
                f"我的问题：{question}\n\n"
                "要求：\n"
                "1. 只基于给定数据回答，不要编造。\n"
                "2. 至少分成 3 个小段输出：结论、依据、建议。\n"
                "3. 如果是路线问题，优先给出最优路线、备选路线和预计耗时。\n"
                "4. 如果是区县或路段问题，请补充当前流量、速度、拥堵、风险等级。\n"
                "5. 用简洁中文回答，允许用项目符号，不要只输出一句话。\n"
            ),
        }
    )
    return messages


def _detect_districts(question: str) -> list[str]:
    return [district for district in DISTRICT_OPTIONS if district in question]


def _detect_road(question: str, roads: list[RoadSegment]) -> RoadSegment | None:
    for road in roads:
        if road.name and road.name in question:
            return road
    return None


def _format_district_summary(current_items: list[dict], district_load: dict[str, float]) -> str:
    ranking = sorted(district_load.items(), key=lambda item: item[1], reverse=True)
    if not ranking:
        return "当前没有可用的区县拥堵汇总。"

    lines = ["区县拥堵均值（从高到低）："]
    for district, value in ranking[:5]:
        lines.append(f"- {district}: {value:.2f}")

    busiest = ranking[0]
    road_count = len(current_items)
    lines.append(f"当前共监测 {road_count} 条路段，拥堵压力最高的是 {busiest[0]}。")
    return "\n".join(lines)


def _format_route_summary(route_options: list[dict]) -> str:
    if not route_options:
        return "当前没有可用的绕行推荐。"

    lines = ["绕行推荐摘要："]
    for index, option in enumerate(route_options[:3], start=1):
        lines.append(
            f"{index}. {option['route_name']}｜预计 {option['estimated_minutes']} 分钟｜风险 {option['risk_score']}｜经过 {', '.join(option['corridors'])}"
        )
    return "\n".join(lines)


def _format_alert_summary(alerts: list[dict]) -> str:
    if not alerts:
        return "当前没有可用的风险预警。"

    lines = ["风险预警摘要："]
    for index, alert in enumerate(alerts[:5], start=1):
        lines.append(
            f"{index}. {alert['road_name']}（{alert['district']}）｜等级 {alert['risk_level']}｜评分 {alert['risk_score']}｜建议 {alert['recommendation']}"
        )
    return "\n".join(lines)


def _build_context(db: Session, question: str, history: list[dict[str, str]] | None = None) -> dict[str, object]:
    current_time = datetime.now()
    roads = db.query(RoadSegment).order_by(RoadSegment.id.asc()).all()
    current_items = [build_current_snapshot(road, current_time) for road in roads]
    recent_history = (
        db.query(TrafficHistory)
        .filter(TrafficHistory.timestamp >= current_time - timedelta(hours=1))
        .order_by(TrafficHistory.road_id.asc(), TrafficHistory.timestamp.asc())
        .all()
    )
    alerts = predict_traffic_alerts(roads, current_items, recent_history, current_time, limit=5)

    origin = None
    destination = None
    districts = _detect_districts(question)
    if len(districts) >= 2:
        origin, destination = districts[0], districts[1]

    route_options = recommend_routes(origin, destination, current_items) if origin and destination else []
    district_load = build_city_district_load(current_items)
    road = _detect_road(question, roads)

    context_lines = [
        f"当前时间：{current_time:%Y-%m-%d %H:%M:%S}",
        f"当前监测路段数：{len(roads)}",
        _format_district_summary(current_items, district_load),
        _format_alert_summary(alerts),
        _format_route_summary(route_options),
    ]

    if road is not None:
        current_item = next((item for item in current_items if int(item["road_id"]) == int(road.id)), None)
        if current_item is not None:
            context_lines.append(
                f"相关路段：{road.name}，所属 {road.type}，当前流量 {current_item['volume']}，速度 {current_item['speed']} km/h，拥堵 {current_item['occupancy']}。"
            )

    if alerts:
        context_lines.append("高风险预警：")
        for alert in alerts[:3]:
            context_lines.append(
                f"- {alert['road_name']}（{alert['district']}）等级 {alert['risk_level']}，评分 {alert['risk_score']}，建议：{alert['recommendation']}"
            )

    if route_options:
        context_lines.append(f"绕行推荐（{origin} -> {destination}）：")
        for option in route_options:
            context_lines.append(
                f"- {option['route_name']}，预计 {option['estimated_minutes']} 分钟，风险 {option['risk_score']}，经过 {', '.join(option['corridors'])}"
            )

    if history:
        context_lines.append("最近对话：")
        for item in history[-6:]:
            context_lines.append(f"- {item['role']}: {item['content']}")

    return {
        "current_time": current_time,
        "context": "\n".join(context_lines),
        "alerts": alerts,
        "routes": route_options,
        "roads": roads,
        "current_items": current_items,
        "road": road,
    }


def _call_deepseek(question: str, context: str, history: list[dict[str, str]]) -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    messages = _build_deepseek_messages(question, context, history)

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }

    request = Request(
        f"{DEEPSEEK_API_BASE.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=DEEPSEEK_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek request failed: {error.code} {detail}") from error
    except URLError as error:
        raise RuntimeError(f"DeepSeek request failed: {error.reason}") from error

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("DeepSeek response did not contain choices")

    message = choices[0].get("message") or {}
    content = str(message.get("content") or "").strip()
    if not content:
        raise RuntimeError("DeepSeek response was empty")

    return content


def _iter_deepseek_stream(question: str, context: str, history: list[dict[str, str]]) -> Iterator[dict[str, str]]:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": _build_deepseek_messages(question, context, history),
        "temperature": 0.2,
        "stream": True,
    }

    request = Request(
        f"{DEEPSEEK_API_BASE.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=DEEPSEEK_TIMEOUT) as response:
            for raw in response:
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line or not line.startswith("data:"):
                    continue

                data_text = line[len("data:") :].strip()
                if data_text == "[DONE]":
                    break

                try:
                    payload = json.loads(data_text)
                except json.JSONDecodeError:
                    continue

                choices = payload.get("choices") or []
                if not choices:
                    continue

                delta = choices[0].get("delta") or {}
                reasoning = str(delta.get("reasoning_content") or "")
                answer_delta = str(delta.get("content") or "")

                if reasoning:
                    yield {"type": "thinking_delta", "text": reasoning}
                if answer_delta:
                    yield {"type": "answer_delta", "text": answer_delta}
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek stream failed: {error.code} {detail}") from error
    except URLError as error:
        raise RuntimeError(f"DeepSeek stream failed: {error.reason}") from error


def _fallback_answer(question: str, context: dict[str, object]) -> str:
    road = context.get("road")
    alerts = context.get("alerts") or []
    routes = context.get("routes") or []
    current_items = context.get("current_items") or []
    current_time = context.get("current_time")
    current_time_text = current_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(current_time, datetime) else "未知时间"

    district_load = build_city_district_load(current_items)
    district_ranking = sorted(district_load.items(), key=lambda item: item[1], reverse=True)
    top_district_lines = [f"- {district}: {value:.2f}" for district, value in district_ranking[:3]]
    top_district_text = "\n".join(top_district_lines) if top_district_lines else "- 暂无"

    road_detail = ""
    if road is not None:
        road_name = getattr(road, "name", "未知路段")
        current_item = next((item for item in current_items if int(item["road_id"]) == int(road.id)), None)
        if current_item is not None:
            road_detail = (
                f"\n- 路段：{road_name}\n"
                f"- 当前流量：{current_item['volume']}\n"
                f"- 当前速度：{current_item['speed']} km/h\n"
                f"- 拥堵指数：{current_item['occupancy']}"
            )

    route_block = ""
    if routes:
        top = routes[0]
        route_block = (
            f"\n- 推荐路线：{top['route_name']}\n"
            f"- 预计耗时：{top['estimated_minutes']} 分钟\n"
            f"- 风险分数：{top['risk_score']}\n"
            f"- 经过线路：{', '.join(top['corridors'])}"
        )

    alert_block = ""
    if alerts:
        top = alerts[0]
        alert_block = (
            f"\n- 预警路段：{top['road_name']}\n"
            f"- 风险等级：{top['risk_level']}\n"
            f"- 风险分数：{top['risk_score']}\n"
            f"- 建议：{top['recommendation']}"
        )

    return (
        f"回答时间：{current_time_text}\n"
        f"问题：{question}\n\n"
        f"结论：当前系统已读取到实时交通数据，但未能触发大模型回答，以下是结构化兜底结果。\n\n"
        f"区域概况：\n当前拥堵较高的前三个区域：\n{top_district_text}\n\n"
        f"路段信息：{road_detail if road_detail else '- 未命中具体路段'}\n\n"
        f"预警信息：{alert_block if alert_block else '- 当前没有更高优先级预警'}\n\n"
        f"绕行建议：{route_block if route_block else '- 当前没有可用绕行路径'}\n\n"
        f"建议：如果你问的是某个区县或路段，请直接带上名称，例如“新沂市现在怎么样”或“徐贾快速路现在如何”。"
    )


@router.post("/chat", response_model=TrafficChatResponse)
def chat(request: TrafficChatRequest, db: Session = Depends(get_db)):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    history = [item.model_dump() for item in request.history]
    context = _build_context(db, question, history)

    provider = "deepseek"
    try:
        answer = _call_deepseek(question, str(context["context"]), history)
    except Exception:
        provider = "fallback"
        answer = _fallback_answer(question, context)

    return {
        "generated_at": context["current_time"],
        "provider": provider,
        "model": DEEPSEEK_MODEL if provider == "deepseek" else "local-fallback",
        "answer": answer,
    }


@router.post("/chat/stream")
def chat_stream(request: TrafficChatRequest, db: Session = Depends(get_db)):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    history = [item.model_dump() for item in request.history]
    context = _build_context(db, question, history)

    def event_stream() -> Iterator[str]:
        for step in _build_thinking_steps(question):
            yield _sse_event({"type": "thinking", "text": step})

        provider = "deepseek"
        model = DEEPSEEK_MODEL
        answer_parts: list[str] = []

        try:
            for event in _iter_deepseek_stream(question, str(context["context"]), history):
                if event.get("type") == "thinking_delta":
                    yield _sse_event({"type": "thinking_delta", "text": event.get("text", "")})
                elif event.get("type") == "answer_delta":
                    delta = event.get("text", "")
                    answer_parts.append(delta)
                    yield _sse_event({"type": "answer_delta", "text": delta})
        except Exception:
            provider = "fallback"
            model = "local-fallback"
            yield _sse_event({"type": "thinking", "text": "大模型流式通道暂不可用，已切换本地应急推理。"})
            fallback = _fallback_answer(question, context)
            for chunk in _iter_text_chunks(fallback):
                answer_parts.append(chunk)
                yield _sse_event({"type": "answer_delta", "text": chunk})

        if not "".join(answer_parts).strip():
            provider = "fallback"
            model = "local-fallback"
            yield _sse_event({"type": "thinking", "text": "模型未返回有效内容，切换本地应急答案。"})
            fallback = _fallback_answer(question, context)
            for chunk in _iter_text_chunks(fallback):
                answer_parts.append(chunk)
                yield _sse_event({"type": "answer_delta", "text": chunk})

        yield _sse_event(
            {
                "type": "done",
                "provider": provider,
                "model": model,
                "generated_at": context["current_time"].isoformat(),
            }
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )