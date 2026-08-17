"""Server management agent — SSH-based Linux server operations.

Extends BaseAgent (Phase 1 extraction from ShannonAgent).
Contains everything unique to server management:
  - 5-stage pipeline (intent → plan → validate → execute → self-heal)
  - SSH command security validation
  - Server-specific system prompts
  - ReAct action type mappings
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from aios.base_agent import BaseAgent
from aios.models import BaseAgentConfig
from aios.security import assess_risk
from aios.tools import get_tool_registry
from app.models import AgentConfig, AgentOutput, CommandItem
from app.prompts import build_system_prompt

logger = logging.getLogger(__name__)

# ReAct types live in app.models (unchanged for Phase 1)
from app.models import (
    ReActAction,
    ReActCommand,
    ReActDone,
    ReActAsk,
    ReActDelegate,
)


class ServerAgent(BaseAgent):
    """Agent that manages Linux servers via SSH.

    Implements the 5-stage pipeline:
      1. intent_analyze  — classify user intent
      2. plan_generate   — produce command plan
      3. plan_validate   — security review (static)
      4. execute         — handled by chat.py ReAct loop
      5. self_heal       — retry with fixes

    This is the primary Agent type in Shannon OS.
    """

    def __init__(self, config: AgentConfig):
        # Convert legacy AgentConfig to AIOS BaseAgentConfig
        aios_cfg = BaseAgentConfig(
            agent_id=f"server_{id(self)}",
            display_name="Shannon Server Agent",
            api_base=config.api_base,
            api_key=config.api_key,
            model=config.model,
            timeout_sec=config.timeout_sec,
            max_context_messages=config.max_context_messages,
        )
        super().__init__(aios_cfg)
        # Keep legacy config reference for any code that expects AgentConfig
        self._legacy_config = config
        # Capability tags for Dispatcher routing
        self._capability_tags = ["ssh", "shell", "server", "deployment", "monitoring"]

    # ── AgentHandle identity ──

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    @property
    def display_name(self) -> str:
        return "Shannon Server Agent"

    # ── Abstract method implementations ──

    def _build_system_prompt(
        self,
        mode: str = "agent",
        host_context: dict | None = None,
        stage: str = "plan",
        metrics_text: str = "",
        hosts_context: list[dict] | None = None,
        available_tools_text: str = "",
        memory_text: str = "",
    ) -> str:
        """Build server-specific system prompt.

        Delegates to app.prompts.build_system_prompt (unchanged).
        """
        return build_system_prompt(
            mode, host_context or {}, stage,
            metrics_text, hosts_context or [], available_tools_text, memory_text,
        )

    def _get_tools(self) -> list[dict[str, Any]]:
        """Return the server agent's tool set from the ToolRegistry."""
        return get_tool_registry().get_for_agent("server")

    def _tool_call_to_action(self, name: str, args: dict[str, Any]) -> Any:
        """Convert a tool-call result to a ReAct action.

        Exact copy of the original _tool_result_to_action from app/agent.py.
        """
        if name == "execute_command":
            return ReActCommand(
                command=args.get("command", ""),
                purpose=args.get("purpose", ""),
                reasoning=args.get("reasoning", ""),
                risk_level=args.get("risk_level", "LOW"),
            )
        elif name == "task_done":
            return ReActDone(message=args.get("message", ""))
        elif name == "ask_user":
            return ReActAsk(
                message=args.get("message", ""),
                reasoning=args.get("reasoning", ""),
            )
        elif name == "delegate_task":
            return ReActDelegate(
                target_agent=args.get("target_agent", "claude_code"),
                reason=args.get("reason", ""),
                risk_level=args.get("risk_level", "LOW"),
                context_for_delegate=args.get("context_for_delegate", ""),
                work_dir=args.get("work_dir"),
            )
        elif name == "delegate_to_agent":
            # AIOS internal IPC: delegate to another AIOS Agent
            return ReActDelegate(
                target_agent=args.get("agent_id", ""),
                reason=args.get("reason", ""),
                risk_level="LOW",
                context_for_delegate=args.get("task", ""),
            )
        return None

    def _dict_to_action(self, data: dict[str, Any]) -> Any:
        """Convert a JSON dict to a ReAct action (non-tool-call fallback)."""
        try:
            action_type = data.get("action")
            # Handle None/missing action gracefully (LLM sometimes omits it)
            if not action_type:
                if data.get("command"):
                    return ReActCommand(**{k: v for k, v in data.items() if k != "action"})
                return ReActDone(message=data.get("message") or str(data))
            clean = {k: v for k, v in data.items() if k != "action"}
            if action_type in ("run", "execute_command"):
                return ReActCommand(**clean)
            elif action_type in ("done", "task_done"):
                return ReActDone(message=data.get("message", ""))
            elif action_type in ("ask", "ask_user"):
                return ReActAsk(message=data.get("message", ""), reasoning=data.get("reasoning", ""))
            elif action_type in ("delegate", "delegate_task", "delegate_to_agent"):
                return ReActDelegate(**clean)
            raise ValueError(f"Unknown action: {action_type}")
        except (ValidationError, TypeError) as e:
            logger.warning("_dict_to_action parse failed: %s, data=%.200s", e, str(data))
            return ReActDone(message=str(data.get("message") or data.get("reply_message") or str(data)))

    def _validate_action(self, action: Any) -> Any:
        """ServerAgent uses stage3_plan_validate instead (called by chat.py)."""
        return action

    def _build_fallback_done_action(self, raw: str) -> Any:
        return ReActDone(message=raw.strip() or "任务已完成")

    # ── Override: _request_first_action with chat.py-compatible signature ──

    async def _request_first_action(
        self,
        user_prompt: str,
        host_context: dict,
        mode: str,
        metrics_text: str = "",
        hosts_context: list[dict] | None = None,
        available_tools_text: str = "",
    ) -> ReActAction | None:
        """Override with the exact signature chat.py expects.

        Builds the server-specific system prompt, then delegates to
        the generic BaseAgent._request_first_action.
        """
        system_prompt = self._build_system_prompt(
            mode, host_context, stage="react",
            metrics_text=metrics_text,
            hosts_context=hosts_context,
            available_tools_text=available_tools_text,
        )
        return await super()._request_first_action(
            user_prompt, system_prompt=system_prompt,
        )

    # ── Stage 1: Intent analysis ──

    async def stage1_intent_analyze(
        self, user_prompt: str, host_context: dict, mode: str,
    ) -> AgentOutput:
        """Classify user intent (legacy two-stage pipeline, kept for compat)."""
        system_prompt = self._build_system_prompt(mode, host_context, stage="intent")
        return await self._request_json(system_prompt, user_prompt, model=AgentOutput)

    # ── Stage 2: Plan generation ──

    async def stage2_plan_generate(
        self, user_prompt: str, host_context: dict, mode: str,
        metrics_text: str = "", hosts_context: list[dict] | None = None,
    ) -> AgentOutput:
        """Generate a command execution plan."""
        system_prompt = self._build_system_prompt(
            mode, host_context, stage="plan",
            metrics_text=metrics_text, hosts_context=hosts_context,
        )
        return await self._request_json(system_prompt, user_prompt, model=AgentOutput)

    # ── Stage 3: Plan validation (server-specific security) ──

    @staticmethod
    def stage3_plan_validate(output: AgentOutput) -> AgentOutput:
        """Validate and fix a command plan.

        - Risk-level normalization
        - Multi-line command cleanup
        - Hard-block pattern check
        - Fallback reply for empty plans

        Exact copy of the original ShannonAgent.stage3_plan_validate.
        """
        fixed = output.model_copy()
        fixed.risk_level = "HIGH" if fixed.risk_level.upper() == "HIGH" else "LOW"
        filtered: list[CommandItem] = []
        for item in fixed.commands_plan:
            cmd = item.command.strip()
            if not cmd:
                continue
            if any(t in cmd for t in ["\n", "\r"]):
                cmd = cmd.splitlines()[0].strip()
            filtered.append(CommandItem(command=cmd, purpose=item.purpose))
        fixed.commands_plan = filtered
        # Re-assess risk for each command
        final_risk = "LOW"
        risk_reasons: list[str] = []
        for item in fixed.commands_plan:
            risk_level, reason = assess_risk(item.command.strip())
            if risk_level == "HIGH":
                final_risk = "HIGH"
                risk_reasons.append(reason)
        fixed.risk_level = final_risk
        if risk_reasons:
            fixed.reasoning = fixed.reasoning or "; ".join(risk_reasons)
        if not fixed.commands_plan and "chat" not in fixed.intent.lower():
            fixed.reply_message = fixed.reply_message or "当前需求更适合人工确认。"
        return fixed

    # ── Stage 5: Self-heal ──

    async def stage5_self_heal(
        self, failed_command: str, stderr: str, exit_code: int,
        host_context: dict, mode: str, attempt: int,
    ) -> AgentOutput:
        """Generate a repair plan after a command failure."""
        prompt = (
            "上一步命令执行失败，请返回修复后的 JSON。"
            f"\n失败命令: {failed_command}"
            f"\n退出码: {exit_code}"
            f"\nstderr: {stderr[:2000]}"
            f"\n当前重试轮次: {attempt}"
        )
        system_prompt = self._build_system_prompt(mode, host_context, stage="heal")
        return await self._request_json(system_prompt, prompt, model=AgentOutput)
