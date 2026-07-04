---
name: adaptive-daily-planner
description: 根据用户目标、当前水平、期限和可用时间制定滚动每日计划，并通过 Super Productivity MCP 创建、复盘和动态调整任务。用于备考、学习训练、项目推进、每日计划、补计划、改日程、早晨复盘或状态查询。
---

# Adaptive Daily Planner

把一个目标变成可执行的 7 天滚动计划，并在 Super Productivity 中持续维护它。

核心原则：先完成信息采集、网络检索和计划合成，再把结构化计划一次性提交给 MCP。不要在 Agent 循环里逐条调用 `create_task` 创建每日计划。

## Load First

使用本技能前先读取：

- `references/planning_workflow.md`：目标访谈、网络经验贴检索、计划合成和动态调整规则。
- `references/super_productivity_contract.md`：Super Productivity MCP、cron 工具、任务结构、报告 notes 和无真删除处理。

如果用户只要求改某一天的日程，仍然读取 Super Productivity contract，并读取 planning workflow 中的调整规则。

## Operating Modes

### 初次建计划

当用户要求为某个目标做每日计划、备考计划、训练计划、项目推进计划，或明确要求写入 Super Productivity：

1. 收集目标、截止日期、当前水平、目标水平、每天可用时间、固定事务、偏好强度和不可安排时段。
2. 对目标领域做实时网络检索，优先综合经验贴、官方或权威资料、近期可验证建议；无法联网时说明限制。
3. 先形成完整目标路线和未来 7 天详细计划。
4. 把计划整理为 `adaptive-daily-planner/v1` JSON payload，一次性调用 `mcp_super-productivity_submit_adaptive_plan`。
5. 创建或更新每天 09:00 的 cron 复盘任务。
6. 调用 `mcp_super-productivity_get_adaptive_plan_job` 查询写入结果，并向用户报告 job 状态、成功项和失败项。

如果 `submit_adaptive_plan` 不可用，不要退回到逐条 `create_task` 写入；改为返回格式化计划草案和缺失工具说明，避免长时间卡住。

### 每日 09:00 复盘

当 cron description 或用户说“每日复盘、早上检查、动态调整计划”时：

1. 优先调用 `mcp_super-productivity_get_adaptive_plan_snapshot` 读取本技能本地索引中的计划状态。
2. 只有索引缺失或用户明确要求核对 Super Productivity 全量数据时，才调用 `get_tasks(include_done=true)`。
3. 找到昨天、今天和未来 7 天的每日父任务及子任务。
3. 根据完成情况、未完成项、实际耗时和用户新增约束调整今日及未来窗口。
4. 未完成的高价值任务迁移到今天或未来 7 天，不直接删除。
5. 重新生成 `adaptive-daily-planner/v1` payload，并用 `submit_adaptive_plan` 一次性提交调整结果。
6. 在今日父任务 notes 追加规划报告，并发送一条简短 Super Productivity notification。

### 主动修改日程

当用户要求修改某天、某项、某个时间段或某个任务：

1. 读取相关项目和任务，定位日期、父任务和子任务。
2. 优先读取 `get_adaptive_plan_snapshot`，避免全量 `get_tasks` 卡住。
3. 按用户意图重算滚动 7 天窗口，并生成新的批量 payload。
4. 用 `submit_adaptive_plan` 提交更新；如果只是单个已知任务的小改动，才可直接调用 `update_task`。
5. 如果替换任务，保留变更记录；不要因为“取消”就直接删除，除非用户明确要求归档。

### 状态查询

当用户问“进度怎么样、今天该做什么、有没有落后、下周怎么安排”：

1. 优先读取 `get_adaptive_plan_snapshot` 和最近的 `get_adaptive_plan_job`。
2. 只有本地索引不足以回答时才读取 Super Productivity 全量任务状态。
2. 汇总完成率、主要拖延项、今天重点、未来风险和建议。
3. 只在用户要求或需要修正计划时更新任务。

## Defaults

- 时区默认 `Asia/Shanghai`。
- 计划写入窗口默认未来 7 天。
- 定时复盘默认每天 09:00，cron expression 为 `0 9 * * *`。
- 报告优先写入 Super Productivity 父任务 notes，notification 只放摘要。
- 目标领域不限于雅思；雅思只是典型使用场景。
- 写入 MCP 的默认方式是一次性 `submit_adaptive_plan`，而不是多次 `create_task`。

## Safety And Idempotency

- 提交计划前先生成完整 payload，并让 MCP 通过本地索引复用已有项目、日期父任务和子任务。
- 不要在批量工具不可用时自动逐条创建任务；这种降级会让 Agent 再次长时间阻塞。
- 不要伪造用户当前水平。当前水平缺失时先询问；如果用户希望立即开始，则安排诊断任务并标注假设。
- 网络资料只用于综合策略，不复制大段原文；报告中简要列出参考来源标题或链接。
- Super Productivity MCP 当前不支持真删除。取消或迁移任务时使用更新、标记、归档等可恢复方式。
