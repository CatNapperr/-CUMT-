#!/usr/bin/env python3
# MCP Server for Super Productivity Integration

import asyncio
import argparse
import hashlib
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions


class SuperProductivityMCPServer:
    def __init__(self):
        self.server = Server("super-productivity")
        self.setup_directories()
        self.setup_logging()
        self.adaptive_index = self._load_json_file(
            self.adaptive_index_file,
            {"version": 1, "goals": {}},
        )
        self.adaptive_jobs = self._load_json_file(
            self.adaptive_jobs_file,
            {"version": 1, "jobs": {}},
        )
        self._background_tasks: set[asyncio.Task] = set()
        self.setup_tools()
        
    def setup_directories(self):
        if os.name == 'nt':  # Windows
            data_dir = os.environ.get('APPDATA', os.path.expanduser('~/AppData/Roaming'))
        else:  # Linux/Mac
            data_dir = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
        
        self.base_dir = Path(data_dir) / 'super-productivity-mcp'
        self.command_dir = self.base_dir / 'plugin_commands'
        self.response_dir = self.base_dir / 'plugin_responses'
        self.adaptive_index_file = self.base_dir / 'adaptive_daily_planner_index.json'
        self.adaptive_jobs_file = self.base_dir / 'adaptive_daily_planner_jobs.json'
        
        # Create directories
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.command_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"MCP Server using directory: {self.base_dir}")
        logging.info(f"Command directory: {self.command_dir}")
        logging.info(f"Response directory: {self.response_dir}")
        
        
    def setup_logging(self):
        log_file = self.base_dir / 'mcp_server.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stderr)
            ]
        )

    def _load_json_file(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not path.exists():
                return default
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else default
        except Exception as exc:
            logging.warning("Failed to load %s: %s", path, exc)
            return default

    def _write_json_file(self, path: Path, data: Dict[str, Any]) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        try:
            tmp_path.replace(path)
        except PermissionError:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            try:
                tmp_path.unlink()
            except OSError:
                pass

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
        
    def setup_tools(self):
        """Set up MCP tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools"""
            return [
                types.Tool(
                    name="create_task",
                    description="Create a new task in Super Productivity. When users provide natural language with time/date references, convert them to Super Productivity syntax in the title field.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Task title with Super Productivity syntax. Convert natural language time/date references to @syntax using days/weeks/months from TODAY (e.g., 'tomorrow' -> '@1days', 'Friday at 3pm' -> '@fri 3pm', 'next week' -> '@7days', 'push back a week' -> '@14days' if task was already a week out). Use @Xdays, @Yweeks, or @Zmonths where X/Y/Z is the number from today. Add #tags for urgency/priority and +projects as needed."
                            },
                            "notes": {
                                "type": "string",
                                "description": "Task notes/description"
                            },
                            "project_id": {
                                "type": "string",
                                "description": "Project ID to assign task to"
                            },
                            "parent_id": {
                                "type": "string",
                                "description": "Parent task ID for subtasks"
                            }
                        },
                        "required": ["title"]
                    }
                ),
                types.Tool(
                    name="get_tasks",
                    description="Get all tasks from Super Productivity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_done": {
                                "type": "boolean",
                                "description": "Include completed tasks",
                                "default": True
                            }
                        }
                    }
                ),
                types.Tool(
                    name="update_task",
                    description="Update an existing task. When users provide natural language with time/date references, convert them to Super Productivity syntax in the title field.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "Task ID to update"
                            },
                            "title": {
                                "type": "string",
                                "description": "New task title with Super Productivity syntax. Convert natural language time/date references to @syntax using days/weeks/months from TODAY (e.g., 'push back a week' -> '@14days' if task was already a week out, 'move to next Friday' -> '@5days' if next Friday is 5 days from today, 'reschedule for tomorrow' -> '@1days'). Use @Xdays, @Yweeks, or @Zmonths where X/Y/Z is the number from today. Add #tags for urgency/priority and +projects as needed."
                            },
                            "notes": {
                                "type": "string",
                                "description": "New task notes"
                            },
                            "is_done": {
                                "type": "boolean",
                                "description": "Mark task as done/undone"
                            },
                            "time_estimate": {
                                "type": "integer",
                                "description": "Time estimate in milliseconds"
                            },
                            "time_spent": {
                                "type": "integer",
                                "description": "Time spent in milliseconds"
                            }
                        },
                        "required": ["task_id"]
                    }
                ),
                types.Tool(
                    name="complete_and_archive_task",
                    description="Complete a task (mark as done) in Super Productivity - NOTE: True deletion is not supported",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "Task ID to complete"
                            }
                        },
                        "required": ["task_id"]
                    }
                ),
                types.Tool(
                    name="get_projects",
                    description="Get all projects from Super Productivity",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="create_project",
                    description="Create a new project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Project title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Project description"
                            },
                            "color": {
                                "type": "string",
                                "description": "Project color (hex code)"
                            }
                        },
                        "required": ["title"]
                    }
                ),
                types.Tool(
                    name="get_tags",
                    description="Get all tags from Super Productivity",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="create_tag",
                    description="Create a new tag",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Tag title"
                            },
                            "color": {
                                "type": "string",
                                "description": "Tag color (hex code)"
                            }
                        },
                        "required": ["title"]
                    }
                ),
                types.Tool(
                    name="show_notification",
                    description="Show a notification in Super Productivity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Notification message"
                            },
                            "type": {
                                "type": "string",
                                "enum": ["success", "info", "warning", "error"],
                                "description": "Notification type",
                                "default": "info"
                            }
                        },
                        "required": ["message"]
                    }
                ),
                types.Tool(
                    name="submit_adaptive_plan",
                    description="Submit a complete adaptive daily plan as one structured payload. Returns quickly with a background job id instead of creating tasks one by one in the agent loop.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "plan": {
                                "type": "object",
                                "description": "Adaptive plan payload. Use version adaptive-daily-planner/v1."
                            },
                            "dry_run": {
                                "type": "boolean",
                                "description": "Validate and summarize without writing to Super Productivity.",
                                "default": False
                            }
                        },
                        "additionalProperties": True
                    }
                ),
                types.Tool(
                    name="get_adaptive_plan_job",
                    description="Get status for an adaptive daily planner background write job.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job id returned by submit_adaptive_plan."
                            },
                            "limit": {
                                "type": "integer",
                                "description": "When job_id is omitted, return this many recent jobs.",
                                "default": 10
                            }
                        }
                    }
                ),
                types.Tool(
                    name="get_adaptive_plan_snapshot",
                    description="Get locally indexed adaptive daily planner tasks without calling the slow full getTasks endpoint.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "goal_key": {
                                "type": "string",
                                "description": "Goal key such as ielts-2026-06. Omit to list known goals."
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Optional inclusive date filter in YYYY-MM-DD format."
                            },
                            "end_date": {
                                "type": "string",
                                "description": "Optional inclusive date filter in YYYY-MM-DD format."
                            }
                        }
                    }
                ),
                types.Tool(
                    name="debug_directories",
                    description="Debug the communication directories and show their status",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[types.TextContent]:
            """Handle tool calls"""
            try:
                if name == "create_task":
                    result = await self.create_task(arguments)
                elif name == "get_tasks":
                    result = await self.get_tasks(arguments)
                elif name == "update_task":
                    result = await self.update_task(arguments)
                elif name == "complete_and_archive_task":
                    result = await self.complete_and_archive_task(arguments)
                elif name == "get_projects":
                    result = await self.get_projects(arguments)
                elif name == "create_project":
                    result = await self.create_project(arguments)
                elif name == "get_tags":
                    result = await self.get_tags(arguments)
                elif name == "create_tag":
                    result = await self.create_tag(arguments)
                elif name == "show_notification":
                    result = await self.show_notification(arguments)
                elif name == "submit_adaptive_plan":
                    result = await self.submit_adaptive_plan(arguments)
                elif name == "get_adaptive_plan_job":
                    result = await self.get_adaptive_plan_job(arguments)
                elif name == "get_adaptive_plan_snapshot":
                    result = await self.get_adaptive_plan_snapshot(arguments)
                elif name == "debug_directories":
                    result = await self.debug_directories(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                text = json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)
                return [types.TextContent(type="text", text=text)]
                
            except Exception as e:
                logging.error(f"Error in tool {name}: {str(e)}")
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def send_command(self, action: str, timeout_s: Optional[float] = None, poll_interval_s: float = 0.2, **kwargs) -> Dict[str, Any]:
        """Send a command to Super Productivity plugin"""
        command = {
            "action": action,
            "id": f"{action}_{asyncio.get_event_loop().time()}",
            "timestamp": asyncio.get_event_loop().time(),
            **kwargs
        }
        
        # Write command file
        command_file = self.command_dir / f"{command['id']}.json"
        with open(command_file, 'w', encoding='utf-8') as f:
            json.dump(command, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Sent command: {action} -> {command_file}")
        
        # Wait for response (with timeout)
        response_file = self.response_dir / f"{command['id']}_response.json"
        
        timeout_s = float(timeout_s or os.environ.get("SP_MCP_COMMAND_TIMEOUT_S", "45"))
        deadline = asyncio.get_event_loop().time() + timeout_s
        while asyncio.get_event_loop().time() < deadline:
            if response_file.exists():
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response = json.load(f)
                    
                    # Clean up response file
                    response_file.unlink()
                    
                    logging.info(f"Received response for {action}: {response.get('success', 'unknown')}")
                    return response
                    
                except Exception as e:
                    logging.error(f"Error reading response file: {e}")
                    break
                    
            await asyncio.sleep(max(0.05, poll_interval_s))
        
        # One final read handles responses created right on the timeout boundary.
        if response_file.exists():
            try:
                with open(response_file, 'r', encoding='utf-8') as f:
                    response = json.load(f)
                response_file.unlink()
                logging.info(f"Received late response for {action}: {response.get('success', 'unknown')}")
                return response
            except Exception as e:
                logging.error(f"Error reading late response file: {e}")

        # Timeout
        logging.warning(f"Timeout waiting for response to {action} after {timeout_s:.1f}s")
        return {"success": False, "error": f"Timeout waiting for response after {timeout_s:.1f}s"}
    
    def parse_task_syntax(self, title: str) -> tuple:
        """Parse Super Productivity task syntax from title"""
        title_clean = title
        
        # Extract tags from title (format: #tagname)
        tag_matches = re.findall(r'#(\w+)', title_clean)
        title_clean = re.sub(r'\s*#\w+', '', title_clean).strip()
        
        # Extract projects from title (format: +projectname)
        project_matches = re.findall(r'\+(\w+)', title_clean)
        title_clean = re.sub(r'\s*\+\w+', '', title_clean).strip()
        
        # Extract scheduling syntax (format: @fri 4pm, @tomorrow, @2024-01-15, etc.)
        schedule_matches = re.findall(r'@(\w+(?:\s+\d+[ap]m)?)', title_clean, re.IGNORECASE)
        title_clean = re.sub(r'\s*@\w+(?:\s+\d+[ap]m)?', '', title_clean, flags=re.IGNORECASE).strip()
        
        # Extract time estimate/spent syntax (format: 10m/3h, 2h, 30m, etc.)
        time_matches = re.findall(r'(\d+[mh](?:/\d+[mh])?)', title_clean)
        title_clean = re.sub(r'\s*\d+[mh](?:/\d+[mh])?', '', title_clean).strip()
        
        return title_clean, tag_matches, project_matches, schedule_matches, time_matches

    def _slug(self, value: str, fallback: str = "item") -> str:
        value = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip()).strip("-")
        if value:
            return value[:80]
        digest = hashlib.sha1(fallback.encode("utf-8")).hexdigest()[:10]
        return f"{fallback}-{digest}"

    def _extract_result_id(self, response: Dict[str, Any]) -> Optional[str]:
        result = response.get("result")
        if isinstance(result, str) and result:
            return result
        if isinstance(result, dict):
            value = result.get("id") or result.get("taskId") or result.get("projectId")
            return str(value) if value else None
        return None

    def _response_ok(self, response: Dict[str, Any]) -> bool:
        return isinstance(response, dict) and response.get("success") is True

    def _relative_day_syntax(self, date_value: str) -> str:
        try:
            target = datetime.strptime(date_value, "%Y-%m-%d").date()
            today = datetime.now().date()
            delta = (target - today).days
            return f"@{max(delta, 0)}days"
        except Exception:
            return "@0days"

    def _normalize_adaptive_plan(self, args: Dict[str, Any]) -> tuple[Optional[Dict[str, Any]], bool, List[str]]:
        plan = args.get("plan")
        if not isinstance(plan, dict):
            plan = {k: v for k, v in args.items() if k != "dry_run"}
        dry_run = bool(args.get("dry_run") or plan.get("dry_run"))
        errors: List[str] = []

        if plan.get("version") != "adaptive-daily-planner/v1":
            errors.append("version must be adaptive-daily-planner/v1")
        for field in ("goal_key", "goal_short"):
            if not str(plan.get(field, "")).strip():
                errors.append(f"{field} is required")

        days = plan.get("days")
        if not isinstance(days, list):
            errors.append("days must be a list")
            days = []
        if len(days) > 7:
            errors.append("days must contain at most 7 entries")

        try:
            window_days = int(plan.get("window_days") or len(days) or 7)
        except Exception:
            window_days = 7
        if window_days > 7:
            errors.append("window_days must be at most 7")
        plan["window_days"] = max(0, min(window_days, 7))

        if not days and not dry_run:
            errors.append("days must not be empty unless dry_run is true")

        for idx, day in enumerate(days):
            if not isinstance(day, dict):
                errors.append(f"days[{idx}] must be an object")
                continue
            date_value = str(day.get("date") or day.get("day") or "").strip()
            if not date_value:
                errors.append(f"days[{idx}].date is required")
            tasks = day.get("tasks", day.get("subtasks", day.get("children", [])))
            if tasks is None:
                tasks = []
            if not isinstance(tasks, list):
                errors.append(f"days[{idx}].tasks must be a list")
                tasks = []
            if len(tasks) > 5:
                errors.append(f"days[{idx}].tasks must contain at most 5 entries")
            day["date"] = date_value
            day["tasks"] = tasks

        project = plan.get("project")
        if not isinstance(project, dict):
            project = {}
        project.setdefault("title", f"Adaptive Plan - {plan.get('goal_short', 'Goal')}")
        project.setdefault("description", f"Adaptive daily plan for {plan.get('goal_short', 'Goal')}")
        project.setdefault("color", "#2196F3")
        plan["project"] = project
        plan.setdefault("timezone", "Asia/Shanghai")

        return (plan if not errors else None), dry_run, errors

    def _summarize_adaptive_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        days = plan.get("days") if isinstance(plan.get("days"), list) else []
        task_count = sum(len(day.get("tasks", [])) for day in days if isinstance(day, dict))
        return {
            "version": plan.get("version"),
            "goal_key": plan.get("goal_key"),
            "goal_short": plan.get("goal_short"),
            "timezone": plan.get("timezone"),
            "window_days": plan.get("window_days"),
            "day_count": len(days),
            "child_task_count": task_count,
            "project_title": (plan.get("project") or {}).get("title"),
        }

    def _job_record(
        self,
        job_id: str,
        status: str,
        plan: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        now = self._utc_now()
        current = self.adaptive_jobs.setdefault("jobs", {}).get(job_id, {})
        record = {
            **current,
            "job_id": job_id,
            "status": status,
            "updated_at": now,
            **extra,
        }
        if "created_at" not in record:
            record["created_at"] = now
        if plan:
            record.setdefault("goal_key", plan.get("goal_key"))
            record.setdefault("plan_summary", self._summarize_adaptive_plan(plan))
        self.adaptive_jobs.setdefault("jobs", {})[job_id] = record
        self._write_json_file(self.adaptive_jobs_file, self.adaptive_jobs)
        return record

    def _goal_index(self, goal_key: str, plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        goals = self.adaptive_index.setdefault("goals", {})
        goal = goals.setdefault(goal_key, {"days": {}})
        if plan:
            goal["goal_short"] = plan.get("goal_short")
            goal["timezone"] = plan.get("timezone")
            goal["project_title"] = (plan.get("project") or {}).get("title")
        goal.setdefault("days", {})
        return goal

    async def submit_adaptive_plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Submit an adaptive plan and write it in a background job."""
        plan, dry_run, errors = self._normalize_adaptive_plan(args or {})
        if errors:
            return {"success": False, "errors": errors}

        assert plan is not None
        job_id = f"adp_{uuid.uuid4().hex[:12]}"
        summary = self._summarize_adaptive_plan(plan)
        if dry_run:
            self._job_record(job_id, "dry_run", plan, dry_run=True, progress={"total": 0, "done": 0})
            return {"success": True, "job_id": job_id, "status": "dry_run", "plan_summary": summary}

        self._job_record(
            job_id,
            "queued",
            plan,
            progress={"total": summary["day_count"] + summary["child_task_count"], "done": 0},
            successes=[],
            failures=[],
        )
        task = asyncio.create_task(self._run_adaptive_plan_job(job_id, plan))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return {
            "success": True,
            "job_id": job_id,
            "status": "queued",
            "plan_summary": summary,
            "message": "Adaptive plan write job queued. Use get_adaptive_plan_job to check progress.",
        }

    async def _run_adaptive_plan_job(self, job_id: str, plan: Dict[str, Any]) -> None:
        successes: List[Dict[str, Any]] = []
        failures: List[Dict[str, Any]] = []
        progress = self.adaptive_jobs.get("jobs", {}).get(job_id, {}).get("progress", {"total": 0, "done": 0})
        self._job_record(job_id, "running", plan, progress=progress, successes=successes, failures=failures)

        try:
            goal_key = str(plan["goal_key"])
            goal = self._goal_index(goal_key, plan)
            project_id = goal.get("project_id")
            if not project_id:
                project_id = await self._resolve_or_create_project(plan, failures)
                if project_id:
                    goal["project_id"] = project_id
                    self._write_json_file(self.adaptive_index_file, self.adaptive_index)

            for day in plan.get("days", []):
                await self._write_adaptive_day(plan, day, project_id, successes, failures, progress)
                self._job_record(
                    job_id,
                    "running",
                    plan,
                    progress=progress,
                    successes=successes[-20:],
                    failures=failures[-20:],
                )

            notification = plan.get("notification") if isinstance(plan.get("notification"), dict) else {}
            message = str(notification.get("message") or "").strip()
            if message:
                response = await self.show_notification({"message": message})
                if self._response_ok(response):
                    successes.append({"action": "show_notification", "message": message})
                else:
                    failures.append({"action": "show_notification", "error": response.get("error", str(response))})

            status = "completed" if not failures else ("partial" if successes else "failed")
            self._job_record(
                job_id,
                status,
                plan,
                progress=progress,
                successes=successes,
                failures=failures,
            )
        except Exception as exc:
            logging.exception("Adaptive plan job failed: %s", job_id)
            failures.append({"action": "job", "error": str(exc)})
            self._job_record(job_id, "failed", plan, progress=progress, successes=successes, failures=failures)

    async def _resolve_or_create_project(self, plan: Dict[str, Any], failures: List[Dict[str, Any]]) -> Optional[str]:
        project = plan.get("project") or {}
        title = str(project.get("title") or f"Adaptive Plan - {plan.get('goal_short', 'Goal')}")
        response = await self.get_projects({})
        if self._response_ok(response):
            for item in response.get("result") or []:
                if isinstance(item, dict) and str(item.get("title", "")).lower() == title.lower():
                    return str(item.get("id")) if item.get("id") else None

        response = await self.create_project(project)
        if self._response_ok(response):
            project_id = self._extract_result_id(response)
            if project_id:
                return project_id
        failures.append({"action": "create_project", "title": title, "error": response.get("error", str(response))})
        return None

    def _task_payload(
        self,
        title: str,
        notes: str = "",
        time_estimate: int = 0,
        project_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "title": title,
            "notes": notes or "",
            "time_estimate": int(time_estimate or 0),
            "project_id": project_id,
            "parent_id": parent_id,
        }

    def _day_notes(self, plan: Dict[str, Any], day: Dict[str, Any]) -> str:
        pieces = []
        for value in (day.get("notes"), day.get("report"), plan.get("report")):
            if isinstance(value, str) and value.strip() and value.strip() not in pieces:
                pieces.append(value.strip())
        sources = plan.get("sources")
        if isinstance(sources, list) and sources:
            pieces.append("Sources: " + "; ".join(str(item) for item in sources[:8]))
        pieces.append(
            "\n".join(
                [
                    "<!-- ADAPTIVE_DAILY_PLANNER",
                    f"goal_short: {plan.get('goal_short', '')}",
                    f"goal_project: {(plan.get('project') or {}).get('title', '')}",
                    f"goal_key: {plan.get('goal_key', '')}",
                    f"date: {day.get('date', '')}",
                    f"window_days: {plan.get('window_days', 7)}",
                    f"generated_at: {self._utc_now()}",
                    "END_ADAPTIVE_DAILY_PLANNER -->",
                ]
            )
        )
        return "\n\n".join(pieces)

    async def _write_adaptive_day(
        self,
        plan: Dict[str, Any],
        day: Dict[str, Any],
        project_id: Optional[str],
        successes: List[Dict[str, Any]],
        failures: List[Dict[str, Any]],
        progress: Dict[str, Any],
    ) -> None:
        goal_key = str(plan["goal_key"])
        goal_short = str(plan["goal_short"])
        date_value = str(day["date"])
        rel = self._relative_day_syntax(date_value)
        goal = self._goal_index(goal_key, plan)
        day_index = goal.setdefault("days", {}).setdefault(date_value, {"tasks": {}})
        day_index.setdefault("tasks", {})

        parent = day.get("parent") if isinstance(day.get("parent"), dict) else {}
        parent_title = str(parent.get("title") or day.get("title") or f"[{goal_short}] {date_value} 每日计划 {rel} #adaptive-plan")
        parent_key = str(parent.get("key") or day.get("key") or "parent")
        parent_payload = self._task_payload(
            parent_title,
            self._day_notes(plan, day),
            int(parent.get("time_estimate") or day.get("time_estimate") or 0),
            project_id,
            None,
        )
        parent_id = await self._upsert_task(day_index.get("parent"), parent_payload, successes, failures, "parent", parent_key)
        if parent_id:
            day_index["parent"] = parent_id

        for idx, child in enumerate(day.get("tasks", [])):
            if not isinstance(child, dict):
                continue
            action = str(child.get("action") or child.get("task_action") or child.get("title") or f"task-{idx + 1}")
            title = str(child.get("title") or f"[{goal_short}] {date_value} {action} {rel} #adaptive-plan")
            task_key = str(child.get("key") or self._slug(f"{date_value}-{idx + 1}-{action}", f"task-{idx + 1}"))
            payload = self._task_payload(
                title,
                str(child.get("notes") or ""),
                int(child.get("time_estimate") or child.get("estimate_ms") or 0),
                project_id,
                parent_id,
            )
            existing_id = day_index["tasks"].get(task_key)
            task_id = await self._upsert_task(existing_id, payload, successes, failures, "child", task_key)
            if task_id:
                day_index["tasks"][task_key] = task_id

        progress["done"] = min(int(progress.get("done", 0)) + 1 + len(day.get("tasks", [])), int(progress.get("total", 0) or 0))
        goal["updated_at"] = self._utc_now()
        self._write_json_file(self.adaptive_index_file, self.adaptive_index)

    async def _upsert_task(
        self,
        existing_id: Optional[str],
        payload: Dict[str, Any],
        successes: List[Dict[str, Any]],
        failures: List[Dict[str, Any]],
        kind: str,
        key: str,
    ) -> Optional[str]:
        if existing_id:
            response = await self.update_task({
                "task_id": existing_id,
                "title": payload["title"],
                "notes": payload["notes"],
                "time_estimate": payload["time_estimate"],
            })
            if self._response_ok(response):
                successes.append({"action": "update_task", "kind": kind, "key": key, "task_id": existing_id})
                return existing_id
            failures.append({"action": "update_task", "kind": kind, "key": key, "task_id": existing_id, "error": response.get("error", str(response))})

        response = await self.create_task(payload)
        if self._response_ok(response):
            task_id = self._extract_result_id(response)
            successes.append({"action": "create_task", "kind": kind, "key": key, "task_id": task_id})
            return task_id
        failures.append({"action": "create_task", "kind": kind, "key": key, "error": response.get("error", str(response))})
        return None

    async def get_adaptive_plan_job(self, args: Dict[str, Any]) -> Dict[str, Any]:
        jobs = self._load_json_file(self.adaptive_jobs_file, self.adaptive_jobs)
        self.adaptive_jobs = jobs
        job_id = str((args or {}).get("job_id") or "").strip()
        if job_id:
            job = jobs.get("jobs", {}).get(job_id)
            if not job:
                return {"success": True, "found": False, "job_id": job_id}
            return {"success": True, "found": True, "job": job}

        try:
            limit = int((args or {}).get("limit") or 10)
        except Exception:
            limit = 10
        items = list(jobs.get("jobs", {}).values())
        items.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return {"success": True, "jobs": items[: max(1, min(limit, 50))]}

    async def get_adaptive_plan_snapshot(self, args: Dict[str, Any]) -> Dict[str, Any]:
        index = self._load_json_file(self.adaptive_index_file, self.adaptive_index)
        self.adaptive_index = index
        goal_key = str((args or {}).get("goal_key") or "").strip()
        start_date = str((args or {}).get("start_date") or "")
        end_date = str((args or {}).get("end_date") or "")
        goals = index.get("goals", {})

        if not goal_key:
            return {
                "success": True,
                "source": "adaptive_daily_planner_index",
                "goals": [
                    {
                        "goal_key": key,
                        "goal_short": value.get("goal_short"),
                        "project_id": value.get("project_id"),
                        "project_title": value.get("project_title"),
                        "day_count": len(value.get("days", {})),
                        "updated_at": value.get("updated_at"),
                    }
                    for key, value in goals.items()
                    if isinstance(value, dict)
                ],
            }

        goal = goals.get(goal_key)
        if not isinstance(goal, dict):
            return {"success": True, "found": False, "goal_key": goal_key, "source": "adaptive_daily_planner_index"}

        days = {}
        for date_key, value in (goal.get("days") or {}).items():
            if start_date and date_key < start_date:
                continue
            if end_date and date_key > end_date:
                continue
            days[date_key] = value
        return {
            "success": True,
            "found": True,
            "source": "adaptive_daily_planner_index",
            "goal": {**goal, "days": days},
        }
    
    async def create_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task"""
        title = args.get("title", "")
        
        # Create the task data - Claude should have already converted natural language to SP syntax
        task_data = {
            "title": title,  # Use title as provided by Claude (should already have @syntax)
            "notes": args.get("notes", ""),
            "timeEstimate": args.get("time_estimate", 0),
            "projectId": args.get("project_id"),
            "parentId": args.get("parent_id"),
            "tagIds": []
        }
        
        return await self.send_command(
            "addTask",
            timeout_s=float(os.environ.get("SP_MCP_CREATE_TASK_TIMEOUT_S", "90")),
            data=task_data,
        )
    
    async def get_tasks(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get all tasks"""
        response = await self.send_command("getTasks", timeout_s=float(os.environ.get("SP_MCP_GET_TASKS_TIMEOUT_S", "120")))
        if response.get("success") and args.get("include_done") is False:
            tasks = response.get("result")
            if isinstance(tasks, list):
                response["result"] = [task for task in tasks if not task.get("isDone")]
        return response
    
    async def update_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update a task"""
        task_id = args.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required"}
        
        updates = {}
        
        # Handle title - Claude should have already converted natural language to SP syntax
        if "title" in args:
            updates["title"] = args["title"]
        
        if "notes" in args:
            updates["notes"] = args["notes"]
        if "is_done" in args:
            updates["isDone"] = args["is_done"]
            if args["is_done"]:
                updates["doneOn"] = asyncio.get_event_loop().time() * 1000
            else:
                updates["doneOn"] = None
        if "time_estimate" in args:
            updates["timeEstimate"] = args["time_estimate"]
        if "time_spent" in args:
            updates["timeSpent"] = args["time_spent"]
        
        return await self.send_command("updateTask", taskId=task_id, data=updates)
    
    async def complete_and_archive_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Complete a task (mark as done) - true deletion is not supported"""
        task_id = args.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required"}
        
        # Mark task as done instead of deleting
        return await self.send_command("setTaskDone", taskId=task_id)
    
    async def get_projects(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get all projects"""
        return await self.send_command("getAllProjects")
    
    async def create_project(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project"""
        project_data = {
            "title": args.get("title", ""),
            "description": args.get("description", ""),
            "color": args.get("color", "#2196F3")
        }
        
        return await self.send_command("addProject", data=project_data)
    
    async def get_tags(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get all tags"""
        return await self.send_command("getAllTags")
    
    async def create_tag(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new tag"""
        tag_data = {
            "title": args.get("title", ""),
            "color": args.get("color", "#FF9800")
        }
        
        return await self.send_command("addTag", data=tag_data)
    
    async def show_notification(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Show a notification"""
        return await self.send_command("showSnack", message=args.get("message", ""))
    
    async def debug_directories(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "base_directory": str(self.base_dir),
            "command_directory": str(self.command_dir),
            "response_directory": str(self.response_dir),
            "directories_exist": {
                "base": self.base_dir.exists(),
                "commands": self.command_dir.exists(),
                "responses": self.response_dir.exists()
            }
        }
    
    def _initialization_options(self) -> InitializationOptions:
        return InitializationOptions(
            server_name="super-productivity",
            server_version="1.1.0",
            capabilities=self.server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )

    async def run_stdio(self):
        """Run the MCP server over stdio."""
        logging.info("Starting Super Productivity MCP Server over stdio...")
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self._initialization_options())

    async def run_streamable_http(self, host: str = "127.0.0.1", port: int = 8765, path: str = "/mcp"):
        """Run the MCP server over Streamable HTTP."""
        import uvicorn
        from mcp.server.fastmcp.server import StreamableHTTPASGIApp
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.applications import Starlette
        from starlette.routing import Route

        if not path.startswith("/"):
            path = "/" + path

        logging.info("Starting Super Productivity MCP Server over streamable-http at http://%s:%s%s", host, port, path)
        session_manager = StreamableHTTPSessionManager(app=self.server)
        streamable_http_app = StreamableHTTPASGIApp(session_manager)
        starlette_app = Starlette(
            routes=[Route(path, endpoint=streamable_http_app)],
            lifespan=lambda app: session_manager.run(),
        )
        config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
        await uvicorn.Server(config).serve()

    async def run(
        self,
        transport: str = "stdio",
        host: str = "127.0.0.1",
        port: int = 8765,
        path: str = "/mcp",
    ):
        """Run the MCP server."""
        transport = (transport or "stdio").strip().lower()
        if transport == "stdio":
            await self.run_stdio()
        elif transport in {"streamable-http", "streamable_http"}:
            await self.run_streamable_http(host=host, port=port, path=path)
        else:
            raise ValueError("transport must be stdio or streamable-http")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Super Productivity MCP server")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default=os.environ.get("SP_MCP_TRANSPORT", "stdio"))
    parser.add_argument("--host", default=os.environ.get("SP_MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("SP_MCP_PORT", "8765")))
    parser.add_argument("--path", default=os.environ.get("SP_MCP_PATH", "/mcp"))
    args = parser.parse_args()

    server = SuperProductivityMCPServer()
    await server.run(transport=args.transport, host=args.host, port=args.port, path=args.path)


if __name__ == "__main__":
    asyncio.run(main())
