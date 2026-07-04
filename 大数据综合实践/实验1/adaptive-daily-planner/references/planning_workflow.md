# Planning Workflow

Use this reference to turn a user goal into a practical rolling plan. Keep the plan grounded in the user's current level, real constraints, and current web evidence.

## 1. Intake

Collect only missing high-impact details. Prefer concise questions over a long interview.

Required fields:

- Goal: what the user wants to achieve.
- Deadline: exact date or target window.
- Current level: score, baseline, recent result, portfolio state, or self-assessment.
- Target level: desired score, output, milestone, or completion state.
- Availability: daily/weekly time budget and fixed unavailable times.
- Constraints: work, school, health, commute, money, materials, tools, exam date, project dependencies.
- Preferences: intensity, rest days, task granularity, preferred study or work time.

If current level is unknown, ask for it. If the user wants to start anyway, schedule a diagnostic task on day 1 and label assumptions in notes.

For IELTS-like goals, collect current and target bands for listening, reading, writing, and speaking when available. Also ask for test date, daily study time, weak sections, and whether the user can do mock tests.

## 2. Web Research

Search at runtime because advice, resources, exam patterns, and user-shared experience posts change over time.

Recommended search pattern:

- English broad query: goal + "study plan" or "preparation plan" + target level + time window.
- Chinese experience query when relevant: goal + "经验贴" + target score or deadline.
- Official or authoritative query: goal + "official guide" or "scoring criteria".
- Bottleneck query: weakest skill + "improve" + goal.

Use 3-5 sources when available. Blend:

- Official or authoritative rules and scoring criteria.
- Recent detailed experience posts with concrete schedules.
- Practical resource recommendations with clear tradeoffs.

Do not copy long passages. Extract patterns: workload, sequencing, common mistakes, useful drills, review cadence, and mock-test frequency. Record source titles or URLs briefly in the report.

If web search is unavailable, say so in the report and proceed from the user's facts plus general planning principles.

## 3. Plan Synthesis

Build the full route mentally, but write only the next 7 days into Super Productivity.

After synthesis, separate planning from writing:

- First produce the complete 7-day plan and report in memory.
- Then convert it to the `adaptive-daily-planner/v1` payload described in `super_productivity_contract.md`.
- Submit the payload once with `submit_adaptive_plan`; do not create each task with separate MCP calls.

Use this structure:

- Milestones: divide deadline into phases such as diagnose, foundation, targeted practice, simulation, polish.
- Daily plan: one focused priority, 2-5 executable tasks, one review loop.
- Weekly rhythm: at least one review or mock checkpoint when the goal benefits from measurement.
- Buffer: reserve space for carryover and life disruptions.

Workload rules:

- Stay within the user's stated daily availability.
- Keep total estimated time under 85 percent of available time unless the user asks for sprint intensity.
- Prefer consistency over heroic days.
- For a missed day, reduce or redistribute before adding pressure.
- Put the highest-value task first in the day.

Task design rules:

- Use action verbs and measurable outputs.
- Avoid vague tasks like "study reading"; write "finish one timed reading passage and log 3 error patterns".
- Include review tasks, not only input tasks.
- Convert lessons learned into tomorrow's plan.

## 4. Daily Review Adjustment

At daily review time:

1. Read the local adaptive plan snapshot before trying a full task fetch.
2. Classify each child task as done, unfinished, blocked, cancelled, or superseded.
3. Compare estimated time and time spent when available.
4. Identify why work slipped: over-scheduling, unexpected event, unclear task, too hard, low priority, or blocked dependency.
5. Move only the tasks that still matter.
6. Rebalance today's plan and future 7-day window.
7. Submit the adjusted 7-day window as one batch payload.

Carryover rules:

- Carry over high-value unfinished work once.
- If a task is missed twice, split it smaller or replace the strategy.
- If the user repeatedly misses a category, reduce volume and add an easier entry task.
- If the user over-completes two days in a row, increase challenge slightly.
- Keep at least one visible win in today's plan after a missed day.

## 5. Manual Changes

When the user changes a day:

- Treat explicit user constraints as authoritative.
- Move lower-priority tasks before moving core milestones.
- Preserve the reason for the change in notes.
- Recompute the next 7 days, not only the edited task.
- Prefer one batch payload for multi-day changes. Use direct `update_task` only for a single known task.
- If the requested change threatens the deadline, report the tradeoff plainly and propose a mitigation.

## 6. Report Template

Write reports in the daily parent task notes.

```markdown
## Adaptive Planning Report - YYYY-MM-DD

### Summary
- Goal:
- Current phase:
- Today focus:

### Yesterday Review
- Completed:
- Carried forward:
- Blocked or cancelled:
- Adjustment reason:

### Today Plan
- Priority 1:
- Supporting tasks:
- Estimated total:

### Rolling 7-Day Changes
- Added:
- Moved:
- Reduced:

### Evidence Used
- User facts:
- Web sources:
- Assumptions:

### Next Check
- Daily review: 09:00 Asia/Shanghai
```
