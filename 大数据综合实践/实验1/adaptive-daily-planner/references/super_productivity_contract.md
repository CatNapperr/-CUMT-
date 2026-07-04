# Super Productivity Contract

Use this reference whenever the skill writes to or reads from Super Productivity.

## Tools

Use the `super-productivity` MCP tools when available:

- `submit_adaptive_plan`
- `get_adaptive_plan_job`
- `get_adaptive_plan_snapshot`
- `get_projects`
- `create_project`
- `get_tags`
- `create_tag`
- `get_tasks`
- `create_task`
- `update_task`
- `complete_and_archive_task`
- `show_notification`

In Jiuwen/OpenJiuwen, MCP tools may be exposed with namespaced function names
such as `mcp_super-productivity_get_projects`. Always call the exact tool name
shown in the available tools list. Do not call a bare name such as
`get_projects` unless that bare name is actually registered.

Use cron tools for automation when available:

- `cron_list_jobs`
- `cron_create_job`
- `cron_update_job`
- `cron_preview_job`

If a tool is unavailable, explain the missing capability and continue with the closest non-mutating output.

For planning writes, prefer `submit_adaptive_plan`. Do not fall back to calling `create_task` repeatedly for a 7-day plan; repeated tool calls can block the agent. If the batch tool is missing, return the formatted plan draft and state that the batch MCP tool is unavailable.

The default MCP transport can stay as `stdio`. If the user runs the MCP server as a persistent HTTP process, Jiuwen can also mount it with `transport: streamable-http` and `url: http://127.0.0.1:8765/mcp`.

## Project And Tags

Project title:

```text
Adaptive Plan - {goal_short}
```

Create or reuse this project. Prefer reuse if a case-insensitive project title match already exists.

Create or reuse these tags via Super Productivity syntax in task titles:

- `#adaptive-plan` for all tasks managed by this skill.
- `#review` for daily review tasks or reports.
- `#carryover` for unfinished work moved from a previous day.
- `#blocked` for tasks waiting on a dependency or user decision.

## Task Naming

Daily parent task:

```text
[{goal_short}] YYYY-MM-DD 每日计划 @Xdays #adaptive-plan
```

Child task:

```text
[{goal_short}] YYYY-MM-DD {task_action} @Xdays #adaptive-plan
```

Use `@Xdays` relative to the current local date. Today is `@0days`, tomorrow is `@1days`.

Use `time_estimate` in milliseconds when the user provides availability or the plan estimates duration.

## Creation Flow

Initial plan:

1. Build the full plan and convert only the next 7 days into one `adaptive-daily-planner/v1` payload.
2. Call the exact registered `submit_adaptive_plan` tool name, usually `mcp_super-productivity_submit_adaptive_plan`.
3. Call `get_adaptive_plan_job` with the returned `job_id` once near the end of the response.
4. Report queued/running/completed/partial/failed status and any failures. Do not keep polling indefinitely.

Daily review:

1. Read indexed tasks with `get_adaptive_plan_snapshot`.
2. Use `get_tasks(include_done=true)` only if the index is missing, stale, or insufficient.
3. Locate yesterday, today, and the next 7 days by `goal_key`, date, and task keys.
4. Recompute the next 7 days and submit one new `adaptive-daily-planner/v1` payload.
5. Add `#carryover` in moved task titles or notes.
6. Write the report into today's parent notes via the submitted payload.

Manual edit:

1. Locate the affected date and task using `get_adaptive_plan_snapshot`.
2. For a single known task, use `update_task` for title, notes, done state, estimate, or schedule syntax.
3. For any multi-day reschedule, recompute the 7-day window and submit one `adaptive-daily-planner/v1` payload.
4. Create a replacement task only when no existing task should be reused.
5. Update the parent task notes with a change log.

## Batch Plan Payload

Use this payload shape for `submit_adaptive_plan`:

```json
{
  "version": "adaptive-daily-planner/v1",
  "goal_key": "ielts-2026-06",
  "goal_short": "IELTS",
  "timezone": "Asia/Shanghai",
  "window_start": "YYYY-MM-DD",
  "window_days": 7,
  "project": {
    "title": "Adaptive Plan - IELTS",
    "description": "Adaptive daily plan for IELTS",
    "color": "#2196F3"
  },
  "days": [
    {
      "date": "YYYY-MM-DD",
      "key": "day-YYYY-MM-DD",
      "title": "[IELTS] YYYY-MM-DD 每日计划 @Xdays #adaptive-plan",
      "notes": "Daily report and plan notes",
      "tasks": [
        {
          "key": "listening-drill",
          "title": "[IELTS] YYYY-MM-DD listening drill @Xdays #adaptive-plan",
          "action": "listening drill",
          "notes": "Concrete output and review criteria",
          "time_estimate": 1800000
        }
      ]
    }
  ],
  "report": "Human-readable planning report",
  "sources": ["source title or url"],
  "assumptions": ["assumption text"],
  "notification": {"message": "IELTS 7 日滚动计划已提交"}
}
```

Limits:

- `window_days` must be at most 7.
- `days` must contain at most 7 entries.
- Each day must contain at most 5 child tasks.
- Use stable `key` values so the MCP index can update existing tasks instead of creating duplicates.

## Cron Job

Create or update one cron job:

```yaml
name: adaptive-daily-planner daily review
cron_expr: 0 9 * * *
timezone: Asia/Shanghai
targets: web
enabled: true
description: Use $adaptive-daily-planner in daily-review mode. Review yesterday's Super Productivity tasks for all projects and tasks marked #adaptive-plan, carry unfinished work forward, update today's parent task notes, keep a rolling 7-day window, and send a Super Productivity notification.
```

Before creating, call `cron_list_jobs` and reuse a job with the same name. If it exists with a different schedule, use `cron_update_job`.

Run `cron_preview_job` after create or update when possible, and mention the next run time in the report.

## Notes Metadata

Add a compact metadata block near the end of each daily parent notes so future reviews can parse intent.

```markdown
<!-- ADAPTIVE_DAILY_PLANNER
goal_short: ...
goal_project: ...
date: YYYY-MM-DD
window_days: 7
phase: ...
generated_at: ISO-8601
sources: title or url list
END_ADAPTIVE_DAILY_PLANNER -->
```

Do not rely only on metadata. Keep the human-readable report above it.

## No True Delete

The current MCP supports completion/archive, not true deletion.

- For a cancelled task, update the title with `[取消]` and explain why in notes, or mark it complete only when the user explicitly wants it cleared.
- For a moved task, update the title schedule and notes instead of creating a duplicate.
- For a superseded task, mark notes with `Superseded by: {new task title}` and add the replacement task if needed.

## Failure Handling

- If `submit_adaptive_plan` returns a `job_id`, report that the write is queued/running and tell the user they can query job status.
- If `submit_adaptive_plan` fails validation, fix the payload once; if still invalid, show the formatted draft.
- If the batch tool is unavailable, do not use repeated `create_task` calls for a full plan. Return a draft plan and explain the missing capability.
- If a project exists but task lookup fails, do not create a large duplicate batch. Ask the user or produce a draft plan.
- If web research fails, still create tasks only from user-provided facts and record the limitation in notes.
