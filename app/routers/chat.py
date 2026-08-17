from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent import ShannonAgent
from app.batch_executor import BatchExecutor
from app.delegate.base import DelegationContext
from app.delegate.claude_code import ClaudeCodeSubAgent
from app.delegate.context_builder import build_conversation_summary, probe_remote_environment
from app.delegate.executor import (
    detect_available_agents,
    get_active_delegation,
    run_delegation,
    cancel_delegation,
    check_claude_installed,
)
from app.delegate.install import ensure_claude_code_available
from app.delegate.reviewer import review_delegation_result
from app.delegate.tool_detector import detect_available_tools, format_tools_for_prompt
from app.models import AgentConfig, AgentOutput, MultiHostPayload, ReActCommand, ReActDelegate, ReActDone, ReActAsk
from app.llm_client import extract_json, try_tool_call
from app.prompts import build_system_prompt
from app.database import (
    append_audit_record,
    append_chat_message,
    append_operation_log,
    append_user_action,
    clear_chat_messages,
    create_conversation,
    get_conversation,
    get_host_context,
    get_hosts_env_info,
    get_latest_metrics_for_host,
    list_chat_messages,
    list_conversation_messages,
    list_conversations,
    update_conversation_title,
    delete_conversation,
    upsert_host_context,
)
from app.events import event_store
from app.executor import ExecContext, ExecutorRouter, TargetHost
from app.settings import get_default_settings, load_runtime_settings

logger = logging.getLogger(__name__)

# 远程工具探测缓存：{host: tools_text}
_tools_cache: dict[str, tuple[str, float]] = {}
_TOOLS_CACHE_TTL_SEC = 300  # 5 分钟后过期

async def _get_cached_tools(executor, host: str) -> str:
    """获取缓存的远程工具列表，缓存未命中或过期时重新探测"""
    import time
    cached = _tools_cache.get(host)
    if cached:
        text, ts = cached
        if time.time() - ts < _TOOLS_CACHE_TTL_SEC:
            return text
    try:
        tools = await detect_available_tools(executor)
        text = format_tools_for_prompt(tools)
        _tools_cache[host] = (text, time.time())
        return text
    except Exception:
        return ""

router = APIRouter(prefix="/api", tags=["chat"])


class HostPayload(BaseModel):
    id: int | None = None
    name: str = "Target Host"
    host: str = "localhost"
    port: int | None = None
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    use_local: bool = False


class ChatRequest(BaseModel):
    prompt: str
    mode: str = Field(default="chat")
    host: HostPayload
    conversation_id: int | None = None
    hosts: list[MultiHostPayload] = Field(default_factory=list)
    react_enabled: bool = True


class ConfirmRequest(BaseModel):
    task_id: str
    force_execute: bool
    operator_name: str | None = None


async def _create_agent() -> ShannonAgent:
    settings = await load_runtime_settings()
    config = AgentConfig(
        api_base=settings.get("api_base", "https://api.deepseek.com"),
        api_key=settings.get("api_key", ""),
        model=settings.get("api_model", "deepseek-chat"),
        timeout_sec=90,
    )
    return ShannonAgent(config)


# ---- ReAct 循环辅助函数 ----

async def _build_metrics_text(host_id: int | None) -> str:
    """构建系统运行状态文本，注入到 agent 提示词"""
    if not host_id:
        return ""
    try:
        metrics = await get_latest_metrics_for_host(host_id)
        if metrics:
            cpu = metrics.get("cpu_usage")
            mem = metrics.get("memory_usage")
            disk = metrics.get("disk_max_usage")
            time_at = metrics.get("collected_at", "")
            parts = [f"当前系统运行状态 (采集时间: {time_at}):"]
            if cpu is not None:
                parts.append(f"  - CPU 使用率: {cpu:.1f}%")
            if mem is not None:
                parts.append(f"  - 内存使用率: {mem:.1f}%")
            if disk is not None:
                parts.append(f"  - 磁盘最高使用率: {disk:.1f}%")
            parts.append("请在做决策时参考以上系统运行状态信息。")
            return "\n".join(parts)
    except Exception:
        pass
    return ""


async def _parse_first_action(
    agent: ShannonAgent, raw_output: str, payload: ChatRequest, host_context: dict | None, metrics_text: str = "", hosts_env_info: list[dict] | None = None, effective_prompt: str = ""
) -> ReActCommand | ReActDone | ReActAsk:
    """从流式响应中解析首个 ReAct 动作"""
    prompt = effective_prompt or payload.prompt
    data = extract_json(raw_output)
    if not data:
        # fallback: 非流式重试
        plan = await agent.stage2_plan_generate(prompt, host_context or {}, payload.mode, metrics_text, hosts_env_info)
        if plan.commands_plan:
            first = plan.commands_plan[0]
            return ReActCommand(command=first.command, purpose=first.purpose, reasoning=plan.reasoning)
        return ReActDone(message=plan.reply_message or raw_output)
    try:
        action_type = data.get("action")
        clean = {k: v for k, v in data.items() if k != "action"}
        if action_type in ("run", "execute_command"):
            return ReActCommand(**clean)
        elif action_type in ("done", "task_done"):
            return ReActDone(message=data.get("message", ""))
        elif action_type in ("ask", "ask_user"):
            return ReActAsk(message=data.get("message", ""), reasoning=data.get("reasoning", ""))
        elif action_type in ("delegate", "delegate_task"):
            return ReActDelegate(**clean)
        # 兼容旧格式：有 commands_plan 则取第一条
        commands = data.get("commands_plan", [])
        if commands:
            return ReActCommand(command=commands[0]["command"], purpose=commands[0].get("purpose", ""),
                                reasoning=data.get("reasoning", ""))
        return ReActDone(message=data.get("reply_message") or data.get("message") or raw_output)
    except Exception:
        # Final safety net: any parse failure → treat as done with raw output
        return ReActDone(message=raw_output)


async def _fallback_first_action(
    agent: ShannonAgent, payload: ChatRequest, host_context: dict | None, metrics_text: str = "", hosts_env_info: list[dict] | None = None, effective_prompt: str = ""
) -> ReActCommand | ReActDone | ReActAsk:
    """完全 fallback：非流式生成第一个动作"""
    prompt = effective_prompt or payload.prompt
    plan = await agent.stage2_plan_generate(prompt, host_context or {}, payload.mode, metrics_text, hosts_env_info)
    plan = agent.stage3_plan_validate(plan)
    if plan.commands_plan:
        first = plan.commands_plan[0]
        return ReActCommand(command=first.command, purpose=first.purpose, reasoning=plan.reasoning)
    return ReActDone(message=plan.reply_message or "已处理完成")


def _estimate_risk(action: ReActCommand | ReActDone | ReActAsk) -> str:
    """LLM 标注为主，硬阻断兜底"""
    from aios.security import is_blocked
    if isinstance(action, ReActCommand):
        # LLM 自己标注的 risk_level 优先
        llm_risk = getattr(action, "risk_level", "LOW") or "LOW"
        if llm_risk.upper() == "HIGH":
            return "HIGH"
        # 硬阻断兜底：LLM 标 LOW 但命中阻断清单 → HIGH
        blocked, _ = is_blocked(action.command)
        if blocked:
            return "HIGH"
        return "LOW"
    return "LOW"


# 存储待确认的任务
pending_confirmations: Dict[str, Any] = {}
pending_events: Dict[str, asyncio.Event] = {}


@router.post("/chat")
async def api_chat(payload: ChatRequest) -> Dict[str, Any]:
    runtime_cfg = await load_runtime_settings()
    host_data = payload.host.model_dump()
    host_id = host_data.pop("id", None)
    if not host_data.get("port"):
        host_data["port"] = runtime_cfg["default_ssh_port"]
    targets: list = []
    if payload.hosts:
        for h in payload.hosts:
            hd = h.model_dump()
            hid = hd.pop("id", None)
            t = TargetHost(host_id=hid, **hd)
            # 从 DB 补充缺失的密码
            if hid and (not t.password or t.password == "***"):
                ctx = await get_host_context(hid, decrypt_pwd=True)
                if ctx and ctx.get("last_pwd"):
                    t.password = ctx["last_pwd"]
            targets.append(t)
    else:
        targets = [TargetHost(host_id=host_id, **host_data)]
    target = targets[0]  # 默认第一个目标，保持现有变量可用

    if not target.host or not target.host.strip():
        raise HTTPException(status_code=400, detail="请填写服务器地址")
    if not target.username or not target.username.strip():
        raise HTTPException(status_code=400, detail="请填写SSH用户名")

    # 验证所有目标服务器都有密码或私钥
    for t in targets:
        has_password = bool(t.password and t.password.strip())
        has_key = bool(t.private_key and t.private_key.strip())
        if not has_password and not has_key:
            raise HTTPException(status_code=400, detail=f"请填写 {t.name} ({t.host}) 的SSH密码或私钥后再执行。")

    task_id = str(uuid.uuid4())
    host_context = await get_host_context(target.host_id) if target.host_id else None

    # 为所有目标服务器补充 *** 掩码密码和保存主机信息
    for t in targets:
        ctx = await get_host_context(t.host_id, decrypt_pwd=True) if t.host_id else None
        if t.password == "***" and ctx:
            real_pwd = ctx.get("last_pwd")
            if real_pwd and real_pwd != "***":
                t.password = real_pwd
        if t.host_id and ctx:
            raw_pwd = t.password.strip() if t.password else ""
            if raw_pwd and raw_pwd != "***":
                await upsert_host_context(
                    name=ctx["name"],
                    host=ctx["host"],
                    port=ctx["port"],
                    username=ctx["username"],
                    last_pwd=raw_pwd,
                )
        elif not t.host_id:
            t.host_id = await upsert_host_context(
                name=t.name,
                host=t.host,
                port=t.port,
                username=t.username,
                last_pwd=t.password.strip() if t.password else None,
            )

    # 会话管理
    conversation_id = payload.conversation_id
    if conversation_id:
        conv = await get_conversation(conversation_id)
        if not conv or conv["host_id"] != target.host_id:
            conversation_id = None  # 会话无效，自动新建
    if not conversation_id and target.host_id:
        conversation_id = await create_conversation(target.host_id)

    # 保存用户消息
    if target.host_id:
        msg_id = await append_chat_message(
            target.host_id, "user", payload.prompt, conversation_id=conversation_id
        )
        # 自动生成标题：首次消息取前 30 字
        if conversation_id:
            conv_msg_count = len(await list_conversation_messages(conversation_id))
            if conv_msg_count <= 1:
                title = (payload.prompt.strip()[:30] + "...") if len(payload.prompt.strip()) > 30 else payload.prompt.strip()
                title = title or "新对话"
                await update_conversation_title(conversation_id, title)

    task = asyncio.create_task(
        _handle_chat_task(task_id, payload, targets, host_context, conversation_id)
    )
    task.add_done_callback(
        lambda t: asyncio.ensure_future(
            _on_task_crash(task_id, t)
        ) if t.exception() else None
    )
    return {"task_id": task_id, "status": "accepted", "conversation_id": conversation_id}


async def _on_task_crash(task_id: str, t: asyncio.Task) -> None:
    """当 _handle_chat_task 内部未捕获异常时，通知前端关闭 SSE。"""
    exc = t.exception()
    logger.error("Chat task %s crashed: %s", task_id, exc, exc_info=exc)
    try:
        await event_store.emit(task_id, {
            "type": "error",
            "message": f"处理请求时发生内部错误: {str(exc)[:200]}",
        })
    except Exception:
        pass


async def _handle_chat_task(
    task_id: str,
    payload: ChatRequest,
    targets: list,
    host_context: Dict[str, Any] | None,
    conversation_id: int | None = None,
):
    target = targets[0] if targets else None
    try:
        current_agent = await _create_agent()

        hosts_env_info = []
        if len(targets) > 1:
            host_ids = [t.host_id for t in targets if t.host_id]
            if host_ids:
                hosts_env_info = await get_hosts_env_info(host_ids)

        # 加载历史消息到 ConversationManager
        # 注意：用户消息已由 api_chat 存入 DB，历史中已包含
        if conversation_id:
            history = await list_conversation_messages(conversation_id)
            for msg in history:
                if msg["role"] == "user":
                    current_agent.conversation.add_user_message(msg["content"])
                elif msg["role"] == "assistant":
                    current_agent.conversation.add_assistant_message(msg["content"])

            # 自动上下文续接：如果对话有历史消息，自动注入提示
            if len(history) >= 4:
                last_msgs = [m for m in history[-6:] if m["role"] in ("user", "assistant")]
                preview = "; ".join(
                    m["content"][:60] for m in last_msgs[-4:]
                )
                context_hint = (
                    f"[系统提示] 你正在继续一个已有 {len(history)} 条消息的对话。"
                    f"最近讨论概要: {preview}"
                    f"\n请基于对话历史继续协助用户，无需重复询问已讨论过的内容。"
                )
                current_agent.conversation.add_user_message(context_hint)
                logger.info("Auto context injected for conversation %s (%d messages)", conversation_id, len(history))

        # 委托冲突检查：如果当前有委托正在执行，通知前端
        active_del = get_active_delegation(target.host_id, conversation_id)
        if active_del and payload.mode in ("agent", "auto"):
            await event_store.emit(task_id, {
                "type": "delegation_conflict",
                "existing_task_id": active_del.task_id,
                "message": "有一个委托任务正在执行中。",
            })
            # 将新任务加入排队，前端让用户选择
            active_del.queued_messages.append({
                "task_id": task_id,
                "payload": payload.model_dump(),
                "targets": [t.__dict__ for t in targets],
                "host_context": host_context,
                "conversation_id": conversation_id,
            })
            # 不发 done 事件，保持 SSE 连接存活，等待冲突解决
            # 冲突解决后（cancel_and_new），后端用同一 task_id 重新生成消息
            return

        await event_store.emit(task_id, {"type": "status", "message": "正在分析意图..."})

        effective_prompt: str = payload.prompt
        # AIOS mode: fall through to existing ReAct loop (ServerAgent).
        # Dispatcher/CodeAgent infrastructure preserved in aios/ for future use.

        # 获取用户记忆，注入到 system prompt（关键词 + 重要度匹配）
        memory_text = ""
        try:
            from aios.memory import memory_manager
            always = await memory_manager.get_always()
            relevant = await memory_manager.search(effective_prompt, top_k=10)
            # Merge: always entries first, then relevant (deduplicated)
            seen_ids = set()
            merged = []
            for e in always:
                if e.get("id") not in seen_ids:
                    merged.append(e)
                    seen_ids.add(e.get("id"))
            for e in relevant:
                if e.get("id") not in seen_ids:
                    merged.append(e)
                    seen_ids.add(e.get("id"))
            memory_text = memory_manager.format_for_prompt(merged)
        except Exception as exc:
            logger.warning("Failed to load memory: %s", exc)

        # 获取最新系统运行状态，注入到 agent 提示词中
        metrics_text = await _build_metrics_text(target.host_id)

        # 构建系统提示词
        if payload.mode == "chat":
            # 纯聊天模式：直接流式回复，不解析 JSON/命令
            system_prompt = current_agent._build_system_prompt(
                "chat", host_context or {}, stage="chat", metrics_text=metrics_text, hosts_context=hosts_env_info, memory_text=memory_text
            )
            current_agent.conversation.set_system_prompt(system_prompt)

            full_response: list[str] = []
            async for chunk in current_agent.stream_reply(payload.prompt):
                full_response.append(chunk)
                await event_store.emit(task_id, {
                    "type": "raw_content", "stage": "chat",
                    "content": chunk,
                })

            reply = "".join(full_response)
            await event_store.emit(task_id, {"type": "done", "message": reply})
            if target.host_id:
                await append_chat_message(
                    target.host_id, "assistant", reply, conversation_id=conversation_id,
                )
            await append_operation_log(
                host_id=target.host_id, mode="chat", intent="chat",
                commands_plan=None, risk_level=None, status="chat_only", task_id=task_id,
            )
            return

        # 委托由 LLM 通过 delegate_task 工具自主决策（ADR-0005）

        # 探测远程服务器可用 CLI 工具（首次探测后缓存）
        available_tools_text = ""
        if payload.mode != "chat":
            from app.executor import ExecutorRouter as _ExecutorRouter
            _probe_executor = _ExecutorRouter.create_executor(target)
            available_tools_text = await _get_cached_tools(_probe_executor, target.host)

        # agent / auto 模式：意图分析与计划生成
        system_prompt = current_agent._build_system_prompt(
            payload.mode, host_context or {}, stage="plan", metrics_text=metrics_text, hosts_context=hosts_env_info, available_tools_text=available_tools_text, memory_text=memory_text
        )
        current_agent.conversation.set_system_prompt(system_prompt)

        full_response: list[str] = []
        thinking = ""
        last_raw = ""
        raw_output = ""  # 初始化，避免 tool calling 成功时 NameError

        # 优先尝试 tool calling 获取结构化输出
        first_action = await current_agent._request_first_action(
            effective_prompt, host_context or {}, payload.mode, metrics_text, hosts_env_info, available_tools_text
        )

        if first_action is None:
            # tool calling 失败，回退到流式 + JSON 解析
            async for chunk in current_agent.stream_reply(
                effective_prompt
            ):
                full_response.append(chunk)
                current_thinking = current_agent.extract_think(
                    "".join(full_response)
                )
                raw_content = "".join(full_response)
                if current_thinking and current_thinking != thinking:
                    thinking = current_thinking
                    await event_store.emit(
                        task_id,
                        {"type": "thinking", "stage": "plan", "content": thinking},
                    )
                elif raw_content != last_raw and len(raw_content) > len(last_raw):
                    await event_store.emit(
                        task_id,
                        {
                            "type": "raw_content",
                            "stage": "plan",
                            "content": raw_content[-500:],
                        },
                    )
                    last_raw = raw_content

            raw_output = "".join(full_response)

            # 尝试从流式响应中解析 ReAct 动作
            first_action = await _parse_first_action(current_agent, raw_output, payload, host_context, metrics_text, hosts_env_info, effective_prompt)
            if first_action is None:
                first_action = await _fallback_first_action(current_agent, payload, host_context, metrics_text, hosts_env_info, effective_prompt)
        else:
            # tool calling 成功，将结构化内容发送给前端
            action_json = json.dumps(first_action.model_dump(), ensure_ascii=False)
            await event_store.emit(task_id, {
                "type": "raw_content", "stage": "plan",
                "content": action_json,
            })
            full_response = [action_json]

        # agent 模式：action 为 done 则纯回复
        if first_action.action == "done":
            reply = first_action.message or raw_output
            await event_store.emit(task_id, {"type": "done", "message": reply})
            if target.host_id:
                await append_chat_message(
                    target.host_id, "assistant", reply, conversation_id=conversation_id,
                )
            await append_operation_log(
                host_id=target.host_id, mode=payload.mode, intent="chat",
                commands_plan=None, risk_level=None, status="chat_only", task_id=task_id,
            )
            await _summarize_memory(current_agent, conversation_id, target.host_id)
            return

        # 委托处理：LLM 决定委托任务给子智能体
        if isinstance(first_action, ReActDelegate):
            await _handle_delegation_flow(
                task_id, first_action, target, targets, host_context,
                payload, current_agent, conversation_id,
            )
            return

        # agent / auto 模式：根据风险等级决定是否等待用户确认
        # agent 模式：风险正常判定，但无论 HIGH/LOW 都需要用户确认
        # auto 模式：LOW 自动执行，HIGH 等待确认
        if payload.mode in ("agent", "auto"):
            assessed_risk = _estimate_risk(first_action)
            need_confirm = (payload.mode == "agent") or (assessed_risk == "HIGH")
            reason = first_action.reasoning or "请确认执行以下操作"
            action_display = first_action.model_dump()
            await event_store.emit(task_id, {
                "type": "plan",
                "intent": "executing_task",
                "risk_level": assessed_risk,
                "reasoning": first_action.reasoning,
                "reply_message": first_action.message if hasattr(first_action, "message") else "",
                "commands_plan": [{"command": action_display.get("command", ""), "purpose": action_display.get("purpose", "")}],
            })
            if need_confirm:
                wait_event = asyncio.Event()
                pending_events[task_id] = wait_event
                pending_confirmations[task_id] = {
                    "target": target, "host_id": target.host_id,
                    "host_context": host_context, "mode": payload.mode,
                    "wait_event": wait_event, "risk_level": assessed_risk,
                }
                await append_audit_record(
                    host_id=target.host_id, task_id=task_id, reason=reason,
                    risk_level=assessed_risk, approved=False, operator_name=None,
                )
                await event_store.emit(task_id, {"type": "risk_hold", "reason": reason, "task_id": task_id,
                                                  "risk_level": assessed_risk,
                                                  "commands_plan": [{"command": action_display.get("command", ""), "purpose": action_display.get("purpose", "")}]})
                try:
                    await asyncio.wait_for(wait_event.wait(), timeout=600)
                except asyncio.TimeoutError:
                    pending_confirmations.pop(task_id, None)
                    pending_events.pop(task_id, None)
                    current_agent.conversation.add_assistant_message("[已取消 — 确认超时]")
                    await event_store.emit(task_id, {"type": "done", "message": "确认超时，已自动取消。"})
                    return
                pending = pending_confirmations.pop(task_id, None)
                pending_events.pop(task_id, None)
                if not pending or not pending.get("confirmed"):
                    current_agent.conversation.add_assistant_message("[已取消 — 用户拒绝执行]")
                    await event_store.emit(task_id, {"type": "done", "message": "已取消执行。"})
                    return
            else:
                # auto 模式 + 低风险：自动执行，无需用户确认
                await append_audit_record(
                    host_id=target.host_id, task_id=task_id, reason=reason,
                    risk_level=assessed_risk, approved=True, operator_name="auto",
                )

        # 切换为 ReAct 系统提示词
        react_prompt = current_agent._build_system_prompt(
            payload.mode, host_context or {}, stage="react", metrics_text=metrics_text, hosts_context=hosts_env_info, available_tools_text=available_tools_text, memory_text=memory_text
        )
        current_agent.conversation.set_system_prompt(react_prompt)

        # ReAct 循环执行
        await event_store.emit(task_id, {"type": "status", "message": "正在执行命令..."})

        # 将首次 action 加入 conversation（流式响应中已含，这里再标注）
        current_agent.conversation.add_assistant_message(
            json.dumps(first_action.model_dump(), ensure_ascii=False)
        )

        is_multi_target = len(targets) > 1
        if is_multi_target:
            batch_executor = BatchExecutor(targets)
        executor = ExecutorRouter.create_executor(target) if not is_multi_target else None
        max_iterations = 40
        iteration = 0
        accumulated_stdout = []
        accumulated_stderr = []
        final_reply = first_action.message if hasattr(first_action, "message") else ""

        # ReAct 关闭模式：直接使用 BatchExecutor 一次性执行命令计划，不走 LLM 循环推理
        if payload.mode in ("agent", "auto") and not payload.react_enabled:
            if isinstance(first_action, ReActCommand) and first_action.command:
                # 一次性执行所有命令
                all_results: dict[str, list] = {}
                # 如果是 ReActCommand，把当前命令作为计划执行
                if is_multi_target:
                    await event_store.emit(task_id, {"type": "command_start", "command": first_action.command,
                                                      "purpose": first_action.purpose, "reasoning": first_action.reasoning})
                    is_download = any(kw in first_action.command for kw in ["wget", "curl", "git clone", "tar"])
                    timeout = 300 if is_download else 60
                    ctx = ExecContext(timeout_sec=timeout)
                    results = await batch_executor.run_command(first_action.command, ctx)
                    for hid, r in results.items():
                        host = next((t for t in targets if t.host_id == hid), None)
                        hname = host.name if host else f"Host-{hid}"
                        await event_store.emit(task_id, {"type": "command_result", "command": first_action.command,
                                                          "host_id": hid, "host_name": hname,
                                                          "stdout": r.stdout, "stderr": r.stderr, "returncode": r.returncode})
                        all_results.setdefault(str(hid), []).append({
                            "host_name": hname,
                            "stdout": r.stdout or "", "stderr": r.stderr or "", "returncode": r.returncode,
                        })
                else:
                    await event_store.emit(task_id, {"type": "command_start", "command": first_action.command,
                                                      "purpose": first_action.purpose, "reasoning": first_action.reasoning})
                    is_download = any(kw in first_action.command for kw in ["wget", "curl", "git clone", "tar"])
                    timeout = 300 if is_download else 60
                    result = await executor.run(first_action.command, ExecContext(timeout_sec=timeout))
                    await event_store.emit(task_id, {"type": "command_result", "command": first_action.command,
                                                      "host_id": target.host_id, "host_name": target.name,
                                                      "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode})
                final_msg = "命令已执行完成。"
                await event_store.emit(task_id, {"type": "done", "message": final_msg})
            else:
                await event_store.emit(task_id, {"type": "done", "message": first_action.message if hasattr(first_action, "message") else "已生成计划。"})
            return

        # 累积整个 ReAct 过程的 blocks，结束后一次性保存（避免每条消息一个气泡）
        accumulated_react_blocks: list[dict] = []

        while iteration < max_iterations:
            iteration += 1
            await event_store.emit(task_id, {"type": "iteration_start", "iteration": iteration, "max_iterations": max_iterations})

            if isinstance(first_action, ReActCommand) and first_action.command:
                cmd = first_action.command
                # 累积 react block（延后到循环结束一次性保存）
                accumulated_react_blocks.append({
                    "type": "react", "action": "run", "command": cmd,
                    "purpose": first_action.purpose, "reasoning": first_action.reasoning,
                })

                await event_store.emit(task_id, {"type": "command_start", "command": cmd, "purpose": first_action.purpose,
                                                  "reasoning": first_action.reasoning})

                # 执行命令
                is_download = any(kw in cmd for kw in ["wget", "curl", "git clone", "tar"])
                timeout = 300 if is_download else 60

                try:
                    if is_multi_target:
                        # 多服务器：使用 BatchExecutor 并行执行
                        ctx = ExecContext(timeout_sec=timeout)
                        batch_results = await batch_executor.run_command(cmd, ctx)
                        for hid, r in batch_results.items():
                            host = next((t for t in targets if t.host_id == hid), None)
                            hname = host.name if host else f"Host-{hid}"
                            await event_store.emit(task_id, {"type": "command_result", "command": cmd,
                                                              "host_id": hid, "host_name": hname,
                                                              "stdout": r.stdout, "stderr": r.stderr, "returncode": r.returncode})
                            accumulated_stdout.append(f"[{hname}] {r.stdout or ''}")
                            if r.stderr:
                                accumulated_stderr.append(f"[{hname}] {r.stderr}")
                        # 将聚合结果反馈给 LLM
                        combined = "\n".join(
                            f"[{next((t.name for t in targets if t.host_id == hid), hid)}]\n{r.stdout or '(空)'}"
                            for hid, r in batch_results.items()
                        )
                        current_agent.conversation.add_tool_result(
                            cmd, 0 if all(r.returncode == 0 for r in batch_results.values()) else 1,
                            combined, ""
                        )
                    else:
                        # 构建流式输出回调，实时推送命令输出
                        async def _stream_line(line: str, is_stderr: bool):
                            clean = line.rstrip("\n")
                            if clean.strip():
                                await event_store.emit(task_id, {
                                    "type": "command_output",
                                    "command": cmd,
                                    "line": clean,
                                    "is_stderr": is_stderr,
                                })

                        result = await executor.run(
                            cmd, ExecContext(timeout_sec=timeout, on_output=_stream_line)
                        )
                        await event_store.emit(task_id, {"type": "command_result", "command": cmd,
                                                          "host_id": target.host_id, "host_name": target.name,
                                                          "stdout": result.stdout, "stderr": result.stderr,
                                                          "returncode": result.returncode})
                        accumulated_stdout.append(result.stdout or "")
                        accumulated_stderr.append(result.stderr or "")

                        # 累积 command result block（延后一次性保存）
                        accumulated_react_blocks.append({
                            "type": "command",
                            "state": "done" if result.returncode == 0 else "error",
                            "command": cmd,
                            "output": (result.stdout or result.stderr or "")[:2000],
                            "exitCode": result.returncode,
                        })

                        # 将执行结果反馈给 LLM
                        current_agent.conversation.add_tool_result(cmd, result.returncode, result.stdout, result.stderr)

                except Exception as exc:
                    error_msg = str(exc)
                    accumulated_stderr.append(error_msg)
                    await event_store.emit(task_id, {"type": "command_result", "command": cmd,
                                                      "stdout": None, "stderr": error_msg, "returncode": -1})
                    if not is_multi_target and target.host_id:
                        accumulated_react_blocks.append({
                            "type": "command",
                            "state": "error", "command": cmd,
                            "output": error_msg[:2000], "exitCode": -1,
                        })
                    current_agent.conversation.add_tool_result(cmd, -1, "", error_msg)

            elif isinstance(first_action, ReActDelegate):
                await _handle_delegation_flow(
                    task_id, first_action, target, targets, host_context,
                    payload, current_agent, conversation_id,
                )
                # 委托流程内部已发 done 并保存消息，直接返回避免循环后重复发送
                return

            elif isinstance(first_action, ReActDone):
                final_reply = first_action.message
                # 不在这里发 react_done（前端会提前关闭 SSE）
                # 保存最终回复（无论有无 blocks）
                if target.host_id:
                    meta = {"blocks": accumulated_react_blocks} if accumulated_react_blocks else None
                    await append_chat_message(
                        target.host_id, "assistant", final_reply, meta=meta,
                        conversation_id=conversation_id,
                    )
                break

            elif isinstance(first_action, ReActAsk):
                final_reply = first_action.message
                await event_store.emit(task_id, {"type": "react_ask", "message": final_reply, "reasoning": first_action.reasoning})
                if target.host_id:
                    meta = {"blocks": accumulated_react_blocks} if accumulated_react_blocks else None
                    await append_chat_message(
                        target.host_id, "user", final_reply, meta=meta,
                        conversation_id=conversation_id,
                    )
                break

            # 刷新系统运行状态并重建 system prompt
            fresh_metrics = await _build_metrics_text(target.host_id)
            if fresh_metrics != metrics_text:
                react_prompt = current_agent._build_system_prompt(
                    payload.mode, host_context or {}, stage="react", metrics_text=fresh_metrics, hosts_context=hosts_env_info, available_tools_text=available_tools_text, memory_text=memory_text
                )
                current_agent.conversation.set_system_prompt(react_prompt)
                metrics_text = fresh_metrics

            # 调用 LLM 获取下一步动作
            try:
                first_action = await current_agent._request_react_action()
            except Exception as exc:
                final_reply = f"LLM 调用失败: {exc}"
                await event_store.emit(task_id, {"type": "error", "message": final_reply})
                break

            # 每轮迭代风险检查（首轮已在循环外查过，但 ReAct 重新生成 action 后需复查）
            if isinstance(first_action, ReActCommand) and first_action.command:
                assessed_risk = _estimate_risk(first_action)
                if payload.mode == "agent" or assessed_risk == "HIGH":
                    reason = first_action.reasoning or "请确认执行以下命令"
                    await event_store.emit(task_id, {"type": "risk_hold", "reason": reason, "task_id": task_id,
                                                      "risk_level": assessed_risk,
                                                      "commands_plan": [{"command": first_action.command, "purpose": first_action.purpose}]})
                    wait_event = asyncio.Event()
                    pending_events[task_id] = wait_event
                    pending_confirmations[task_id] = {
                        "target": target, "host_id": target.host_id,
                        "host_context": host_context, "mode": payload.mode,
                        "wait_event": wait_event, "risk_level": assessed_risk,
                    }
                    try:
                        await asyncio.wait_for(wait_event.wait(), timeout=600)
                    except asyncio.TimeoutError:
                        pending_confirmations.pop(task_id, None)
                        pending_events.pop(task_id, None)
                        current_agent.conversation.add_assistant_message("[已取消 — 确认超时]")
                        final_reply = "确认超时，已自动取消。"
                        await event_store.emit(task_id, {"type": "done", "message": final_reply})
                        break
                    pending = pending_confirmations.pop(task_id, None)
                    pending_events.pop(task_id, None)
                    if not pending or not pending.get("confirmed"):
                        current_agent.conversation.add_assistant_message("[已取消 — 用户拒绝执行]")
                        final_reply = "已取消执行。"
                        await event_store.emit(task_id, {"type": "done", "message": final_reply})
                        break

        else:
            final_reply = f"已达到最大迭代次数 ({max_iterations})，执行终止。"
            await event_store.emit(task_id, {"type": "done", "message": final_reply})
            await _summarize_memory(current_agent, conversation_id, target.host_id)

        # 所有迭代完成，记录操作日志
        await append_operation_log(
            host_id=target.host_id, mode=payload.mode, intent="react_execution",
            commands_plan=None, risk_level=None, status="completed",
            stdout="\n".join(filter(None, accumulated_stdout)),
            stderr="\n".join(filter(None, accumulated_stderr)),
            task_id=task_id,
        )

        # done 事件 — 始终发送，确保前端正常结束 SSE 流
        await event_store.emit(task_id, {"type": "done", "message": final_reply})
        # 保存消息（ReActDone/ReActAsk 在循环内已保存，此处处理其他终止场景）
        if not isinstance(first_action, (ReActDone, ReActAsk)):
            if target.host_id:
                meta = {"blocks": accumulated_react_blocks} if accumulated_react_blocks else None
                await append_chat_message(
                    target.host_id, "assistant", final_reply or "执行完成",
                    meta=meta, conversation_id=conversation_id,
                )

        # 总结记忆（在 done 事件之后执行，不阻塞用户响应）
        await _summarize_memory(current_agent, conversation_id, target.host_id)
    except Exception as exc:
        import traceback

        error_msg = f"{type(exc).__name__}: {str(exc) or '未知错误'}"
        logger.error(
            "[_handle_chat_task] 错误: %s\n%s", error_msg, traceback.format_exc()
        )
        await event_store.emit(task_id, {"type": "error", "message": error_msg})
        if target and target.host_id:
            await append_chat_message(
                target.host_id, "assistant", f"错误: {error_msg}", conversation_id=conversation_id,
            )


async def _handle_delegation_flow(
    task_id: str,
    action: ReActDelegate,
    target,
    targets: list,
    host_context: dict | None,
    payload,
    current_agent,
    conversation_id: int | None = None,
):
    """处理委托流程：确认 → 执行 → 审核 → 融入对话"""
    import time as time_module

    # 1. 风险判断
    risk_level = action.risk_level.upper()

    # HIGH 风险 → 等待用户确认（预判器 + LLM 共同决策后，由用户最终确认）
    if risk_level == "HIGH":
        await event_store.emit(task_id, {
            "type": "delegate_confirm_required",
            "agent": action.target_agent,
            "reason": action.reason,
            "risk_level": risk_level,
            "task": action.context_for_delegate,
        })
        wait_event = asyncio.Event()
        pending_events[task_id] = wait_event
        pending_confirmations[task_id] = {
            "target": target, "host_id": target.host_id,
            "host_context": host_context, "mode": payload.mode,
            "wait_event": wait_event, "risk_level": risk_level,
            "is_delegation": True,
        }
        await append_audit_record(
            host_id=target.host_id, task_id=task_id, reason=action.reason,
            risk_level=risk_level, approved=False, operator_name=None,
        )
        try:
            await asyncio.wait_for(wait_event.wait(), timeout=600)
        except asyncio.TimeoutError:
            pending_confirmations.pop(task_id, None)
            pending_events.pop(task_id, None)
            await event_store.emit(task_id, {
                "type": "done",
                "message": "委托确认超时，已自动取消。退回 Agent 模式处理。",
            })
            await _fallback_to_agent(task_id, target, host_context, payload, current_agent, conversation_id)
            return
        pending = pending_confirmations.pop(task_id, None)
        pending_events.pop(task_id, None)
        if not pending or not pending.get("confirmed"):
            await event_store.emit(task_id, {
                "type": "delegate_fallback",
                "message": "用户拒绝委托，退回 Agent 模式。",
            })
            await _fallback_to_agent(task_id, target, host_context, payload, current_agent, conversation_id)
            return
    else:
        await append_audit_record(
            host_id=target.host_id, task_id=task_id, reason=action.reason,
            risk_level=risk_level, approved=True, operator_name="auto",
        )

    # 2. 创建 SSH executor
    from app.executor import ExecutorRouter
    executor = ExecutorRouter.create_executor(target)

    # 3. 检查 Claude Code 是否安装
    claude_ok = await check_claude_installed(executor)
    if not claude_ok:
        await event_store.emit(task_id, {
            "type": "delegate_install_required",
            "host_name": target.name,
            "message": f"目标服务器 {target.name} 上未安装 Claude Code CLI，是否自动安装？",
        })
        wait_event = asyncio.Event()
        pending_events[f"install_{task_id}"] = wait_event
        pending_confirmations[f"install_{task_id}"] = {
            "target": target, "host_id": target.host_id,
            "wait_event": wait_event, "is_install": True,
        }
        try:
            await asyncio.wait_for(wait_event.wait(), timeout=300)
        except asyncio.TimeoutError:
            pending_confirmations.pop(f"install_{task_id}", None)
            pending_events.pop(f"install_{task_id}", None)
            await event_store.emit(task_id, {
                "type": "delegate_fallback",
                "message": "安装确认超时，退回 Agent 模式。",
            })
            await _fallback_to_agent(task_id, target, host_context, payload, current_agent, conversation_id)
            return
        install_pending = pending_confirmations.pop(f"install_{task_id}", None)
        pending_events.pop(f"install_{task_id}", None)
        if not install_pending or not install_pending.get("confirmed"):
            await event_store.emit(task_id, {
                "type": "delegate_fallback",
                "message": "用户拒绝安装，退回 Agent 模式。",
            })
            await _fallback_to_agent(task_id, target, host_context, payload, current_agent, conversation_id)
            return
        # 执行安装
        ok, msg, report = await ensure_claude_code_available(executor)
        if not ok:
            await event_store.emit(task_id, {
                "type": "delegate_fallback",
                "message": f"安装失败: {msg}，退回 Agent 模式。",
            })
            await _fallback_to_agent(task_id, target, host_context, payload, current_agent, conversation_id)
            return
        await event_store.emit(task_id, {
            "type": "status",
            "message": f"Claude Code 安装完成: {msg}",
        })

    # 4. 探测服务器环境
    host_info = await probe_remote_environment(executor) or {}

    # 5. 生成对话摘要
    messages = current_agent.conversation.get_messages()
    settings = await load_runtime_settings()
    summary = await build_conversation_summary(
        settings.get("api_base", "https://api.deepseek.com"),
        settings.get("api_key", ""),
        settings.get("aux_model", "deepseek-chat"),
        messages,
    )

    # 6. 确定工作目录
    work_dir = action.work_dir or (host_context.get("cwd") if host_context else None)

    # 7. 构建委托上下文并执行
    ctx = DelegationContext(
        user_input=payload.prompt,
        host_info=host_info,
        work_dir=work_dir,
        conversation_summary=summary,
        task_id=task_id,
        risk_level=risk_level,
    )

    # 在 run_delegation 前捕获排队消息（其 finally 会清理 session）
    active_before = get_active_delegation(target.host_id, conversation_id)
    queued_before = list(active_before.queued_messages) if active_before else []

    sub_agent = ClaudeCodeSubAgent()
    result = await run_delegation(
        sub_agent, action.context_for_delegate, ctx, executor,
        event_store, target.host_id, conversation_id,
    )

    # 用户取消委托 → 退回基础 Agent 继续执行
    if result.cancelled:
        await event_store.emit(task_id, {
            "type": "delegate_fallback",
            "message": "委托已取消，退回 Agent 模式继续执行。",
        })
        await _fallback_to_agent(task_id, target, host_context, payload, current_agent, conversation_id)
        return

    # 8. 审核委托结果
    review = await review_delegation_result(
        settings.get("api_base", "https://api.deepseek.com"),
        settings.get("api_key", ""),
        settings.get("aux_model", "deepseek-chat"),
        payload.prompt,
        result.stdout or "",
        result.exit_code,
        result.execution_time_sec,
        stderr=result.stderr or "",
    )

    await event_store.emit(task_id, {
        "type": "delegate_review",
        "goal_achieved": review.get("goal_achieved", "⚠️ 部分达成"),
        "goal_reasoning": review.get("goal_reasoning", ""),
        "exit_code": review.get("exit_code"),
        "exit_ok": review.get("exit_ok", False),
        "execution_time_sec": review.get("execution_time_sec"),
        "files_changed": review.get("files_changed", []),
        "risk_warnings": review.get("risk_warnings", []),
        "output_summary": review.get("output_summary", ""),
        "stderr": review.get("stderr", ""),
    })

    # 9. 融入对话上下文
    summary_text = f"[委托执行结果 - {sub_agent.display_name}]\n{review.get('output_summary', '')}"
    current_agent.conversation.add_assistant_message(summary_text)

    # 10. 写入操作日志
    await append_operation_log(
        host_id=target.host_id, mode="delegate", intent="delegation",
        commands_plan=[{
            "agent": action.target_agent,
            "task": action.context_for_delegate,
            "reason": action.reason,
            "risk_level": risk_level,
            "exit_code": result.exit_code,
            "goal_achieved": review.get("goal_achieved"),
            "execution_time_sec": result.execution_time_sec,
            "files_changed": review.get("files_changed", []),
            "cancelled": result.cancelled,
            "timed_out": result.timed_out,
        }],
        risk_level=risk_level,
        status="completed" if not result.cancelled else "cancelled",
        stdout=result.stdout[:2000] if result.stdout else None,
        stderr=result.stderr[:1000] if result.stderr else None,
        exit_code=result.exit_code,
        task_id=task_id,
    )

    # 11. 保存委托结果到聊天记录
    if target.host_id:
        final_msg = (
            f"**🧠 智能委托 - {sub_agent.display_name}**\n\n"
            f"**目标达成:** {review.get('goal_achieved', '⚠️ 部分达成')}\n"
            f"**耗时:** {result.execution_time_sec:.1f}秒\n"
            f"**变更文件:** {len(review.get('files_changed', []))}个\n"
        )
        if review.get("risk_warnings"):
            final_msg += f"\n⚠️ **风险警告:** {', '.join(review['risk_warnings'])}"
        final_msg += f"\n\n{review.get('output_summary', '')[:2000]}"
        await append_chat_message(
            target.host_id, "assistant", final_msg,
            {"blocks": [{
                "type": "delegation",
                "state": "completed",
                "agent": sub_agent.display_name,
                "reason": action.reason,
                "riskLevel": risk_level,
                "goalAchieved": review.get("goal_achieved", "⚠️ 部分达成"),
                "goalReasoning": review.get("goal_reasoning", ""),
                "executionTime": result.execution_time_sec,
                "filesChanged": review.get("files_changed", []),
                "filesChangedCount": len(review.get("files_changed", [])),
                "riskWarnings": review.get("risk_warnings", []),
                "outputSummary": review.get("output_summary", "")[:2000],
                "exitCode": review.get("exit_code"),
            }]},
            conversation_id=conversation_id,
        )

    await event_store.emit(task_id, {
        "type": "done",
        "message": f"委托执行完成 - {review.get('goal_achieved', '⚠️ 部分达成')}",
    })

    # 12. 处理排队消息（使用 run_delegation 前捕获的副本）
    for queued in queued_before:
        await event_store.emit(queued["task_id"], {
            "type": "status",
            "message": "上一个委托已完成，正在处理排队任务...",
        })
        t = asyncio.create_task(
            _handle_chat_task(
                queued["task_id"],
                ChatRequest(**queued["payload"]),
                [TargetHost(**t) for t in queued["targets"]],
                queued["host_context"],
                queued["conversation_id"],
            )
        )
        t.add_done_callback(
            lambda t: asyncio.ensure_future(
                _on_task_crash(queued["task_id"], t)
            ) if t.exception() else None
        )


async def _summarize_memory(current_agent, conv_id: int | None, host_id: int | None):
    """对话结束后触发记忆总结（后台任务，不阻塞响应）"""
    try:
        from aios.memory import memory_manager
        messages = current_agent.conversation.get_messages()
        if len(messages) < 4:  # 至少有几个来回才值得总结
            return
        count = await memory_manager.summarize_and_store(messages, conv_id, host_id)
        if count > 0:
            logger.info("Memory: summarized %d entries from conversation %s", count, conv_id)
    except Exception as exc:
        logger.warning("Memory summarization failed: %s", exc)


async def _fallback_to_agent(
    task_id: str, target, host_context: dict | None,
    payload, current_agent, conversation_id: int | None = None,
):
    """委托拒绝/失败后回退到正常 Agent 流程"""
    # 简化回退：用非委托模式重新生成回复
    system_prompt = current_agent._build_system_prompt(
        payload.mode, host_context or {}, stage="plan", metrics_text="",
        hosts_context=None, memory_text="",
    )
    current_agent.conversation.set_system_prompt(system_prompt)
    try:
        plan = await current_agent.stage2_plan_generate(payload.prompt, host_context or {}, payload.mode)
        reply = plan.reply_message or "已退回 Agent 模式处理，请重新描述您的需求。"
    except Exception:
        reply = "委托已取消，请重新描述您的需求。"
    await event_store.emit(task_id, {"type": "done", "message": reply})
    if target.host_id:
        await append_chat_message(
            target.host_id, "assistant", reply, conversation_id=conversation_id,
        )


async def _execute_plan(
    task_id: str,
    target: TargetHost,
    plan_result: Any,
    host_context: Dict[str, Any] | None,
    mode: str,
    host_id: int | None,
    conversation_id: int | None = None,
):
    executor = ExecutorRouter.create_executor(target)
    stdout = []
    stderr = []

    for cmd in plan_result.commands_plan:
        await event_store.emit(
            task_id, {"type": "command_start", "command": cmd.command}
        )

        # 动态超时：下载/git clone 类命令给 300s，其余 60s
        is_download = any(kw in cmd.command for kw in ["wget", "curl", "git clone", "tar"])
        timeout = 300 if is_download else 60

        async def on_output(line: str, is_stderr: bool):
            try:
                await event_store.emit(task_id, {
                    "type": "command_output",
                    "command": cmd.command,
                    "line": line,
                    "is_stderr": is_stderr,
                })
            except Exception:
                pass

        try:
            result = await executor.run(
                cmd.command,
                ExecContext(timeout_sec=timeout, on_output=on_output)
            )
            stdout.append(result.stdout or "")
            stderr.append(result.stderr or "")
            await event_store.emit(
                task_id,
                {
                    "type": "command_result",
                    "command": cmd.command,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
            )
        except Exception as exc:
            error_msg = str(exc)
            stderr.append(error_msg)
            await event_store.emit(
                task_id,
                {
                    "type": "command_result",
                    "command": cmd.command,
                    "stdout": None,
                    "stderr": error_msg,
                    "returncode": -1,
                },
            )

    await append_operation_log(
        host_id=host_id,
        mode=mode,
        intent=plan_result.intent,
        commands_plan=[item.model_dump() for item in plan_result.commands_plan],
        risk_level=plan_result.risk_level,
        status="completed",
        stdout="\n".join(filter(None, stdout)),
        stderr="\n".join(filter(None, stderr)),
        task_id=task_id,
    )

    await event_store.emit(
        task_id,
        {
            "type": "done",
            "message": plan_result.reply_message,
            "stdout": "\n".join(filter(None, stdout)),
            "stderr": "\n".join(filter(None, stderr)),
        },
    )
    if host_id:
        final_content = plan_result.reply_message
        if stdout:
            final_content += "\n\n" + "\n".join(filter(None, stdout))
        await append_chat_message(
            host_id,
            "assistant",
            final_content,
            {
                "blocks": [{
                    "type": "plan",
                    "reasoning": plan_result.reasoning or "",
                    "commands": [{"purpose": cmd.purpose or "", "command": cmd.command} for cmd in plan_result.commands_plan],
                    "risk": plan_result.risk_level or "LOW",
                }],
            },
            conversation_id=conversation_id,
        )


@router.post("/execute/confirm")
async def api_confirm(payload: ConfirmRequest) -> dict[str, Any]:
    pending = pending_confirmations.get(payload.task_id)
    if not pending:
        raise HTTPException(status_code=404, detail="task confirmation not found")

    wait_event = pending.get("wait_event")
    if not wait_event:
        raise HTTPException(status_code=404, detail="task event not found")

    if not payload.force_execute:
        await append_audit_record(
            host_id=pending["host_id"],
            task_id=payload.task_id,
            reason="用户取消执行",
            risk_level=pending.get("risk_level", "LOW"),
            approved=False,
            operator_name=payload.operator_name,
        )
        pending["confirmed"] = False
        wait_event.set()
        await event_store.emit(
            payload.task_id,
            {"type": "confirmation_cancelled", "task_id": payload.task_id},
        )
        return {"task_id": payload.task_id, "status": "cancelled"}

    await append_audit_record(
        host_id=pending["host_id"],
        task_id=payload.task_id,
        reason="用户确认执行",
        risk_level=pending.get("risk_level", "LOW"),
        approved=True,
        operator_name=payload.operator_name,
    )
    pending["confirmed"] = True
    wait_event.set()
    await event_store.emit(
        payload.task_id,
        {"type": "confirmation_accepted", "task_id": payload.task_id},
    )
    return {"task_id": payload.task_id, "status": "confirmed"}


@router.post("/conversations")
async def api_create_conversation(payload: dict[str, Any]) -> dict[str, Any]:
    host_id = payload.get("host_id")
    title = payload.get("title", "新对话")
    if not host_id:
        raise HTTPException(status_code=400, detail="host_id is required")
    conv_id = await create_conversation(host_id, title)
    return {"id": conv_id, "title": title, "host_id": host_id}


@router.get("/conversations/{host_id}")
async def api_list_conversations(host_id: int) -> List[Dict[str, Any]]:
    return await list_conversations(host_id)


@router.patch("/conversations/{conv_id}")
async def api_update_conversation(conv_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    title = payload.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    ok = await update_conversation_title(conv_id, title)
    if not ok:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"ok": True}


@router.delete("/conversations/{conv_id}")
async def api_delete_conversation(conv_id: int) -> dict[str, Any]:
    ok = await delete_conversation(conv_id)
    if not ok:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"ok": True}


@router.get("/conversations/{conv_id}/messages")
async def api_get_conversation_messages(conv_id: int) -> List[Dict[str, Any]]:
    return await list_conversation_messages(conv_id)


@router.get("/chat/{host_id}")
async def api_get_chat_history(host_id: int) -> List[Dict[str, Any]]:
    return await list_chat_messages(host_id)


@router.delete("/chat/{host_id}")
async def api_clear_chat_history(host_id: int) -> Dict[str, Any]:
    await clear_chat_messages(host_id)
    return {"ok": True, "message": "对话历史已清除"}


@router.get("/stream/{task_id}")
async def api_stream(task_id: str) -> StreamingResponse:
    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        cached = event_store.subscribe(task_id, queue)

        # 先发送缓存事件
        for event in cached:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    if data.get("type") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    # 每 15s 发心跳注释，防止反向代理/Uvicorn 断开空闲连接
                    yield ": heartbeat\n\n"
        finally:
            event_store.unsubscribe(task_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class ExecutePlanRequest(BaseModel):
    commands: list[dict]
    hosts: list[MultiHostPayload]


@router.post("/chat/execute-plan")
async def api_execute_plan(payload: ExecutePlanRequest) -> dict:
    """接收命令计划 + hosts 列表，走 BatchExecutor 直接执行（不走 LLM）"""
    from app.executor import ExecContext

    targets = []
    for h in payload.hosts:
        hd = h.model_dump()
        hd.pop("id", None)
        targets.append(TargetHost(**hd))

    batch = BatchExecutor(targets)
    results = {}
    for cmd_item in payload.commands:
        cmd = cmd_item.get("command", "")
        if not cmd:
            continue
        ctx = ExecContext(timeout_sec=60)
        cmd_results = await batch.run_command(cmd, ctx)
        for host_id, result in cmd_results.items():
            if host_id not in results:
                results[host_id] = []
            results[host_id].append({
                "command": cmd,
                "purpose": cmd_item.get("purpose", ""),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            })

    return {"ok": True, "data": {"results": results}}


# ── 委托相关 API ──


class DelegateCancelRequest(BaseModel):
    task_id: str


class DelegateInstallRequest(BaseModel):
    host: HostPayload


class DelegateConflictResolveRequest(BaseModel):
    task_id: str
    action: str  # "cancel_and_new" | "queue"


@router.post("/delegate/cancel")
async def api_delegate_cancel(payload: DelegateCancelRequest) -> dict[str, Any]:
    """取消正在执行的委托任务"""
    # 查找所有活跃委托中匹配的
    from app.delegate.executor import _active_delegations

    cancelled = False
    for key, session in list(_active_delegations.items()):
        if session.task_id == payload.task_id:
            session.cancel_event.set()
            try:
                await session.agent.cancel()
            except Exception:
                pass
            cancelled = True
            break

    if not cancelled:
        raise HTTPException(status_code=404, detail="未找到活跃的委托任务")

    await event_store.emit(payload.task_id, {
        "type": "delegate_cancelled",
        "message": "委托已被用户取消",
    })
    return {"task_id": payload.task_id, "status": "cancelled"}


@router.post("/delegate/confirm-install")
async def api_delegate_confirm_install(payload: ConfirmRequest) -> dict[str, Any]:
    """确认或拒绝安装 Claude Code"""
    install_key = f"install_{payload.task_id}"
    pending = pending_confirmations.get(install_key)
    if not pending:
        raise HTTPException(status_code=404, detail="安装确认请求未找到")

    wait_event = pending.get("wait_event")
    if not wait_event:
        raise HTTPException(status_code=404, detail="事件未找到")

    if not payload.force_execute:
        pending["confirmed"] = False
        wait_event.set()
        return {"task_id": payload.task_id, "status": "install_rejected"}

    pending["confirmed"] = True
    wait_event.set()
    return {"task_id": payload.task_id, "status": "install_confirmed"}


@router.post("/delegate/resolve-conflict")
async def api_delegate_resolve_conflict(payload: DelegateConflictResolveRequest) -> dict[str, Any]:
    """解决委托冲突：取消当前委托 + 执行新任务，或排队等待"""
    from app.delegate.executor import _active_delegations, get_active_delegation

    # 找到相关的活跃委托
    active_session = None
    active_key = None
    for key, session in _active_delegations.items():
        if any(
            q.get("task_id") == payload.task_id
            for q in session.queued_messages
        ):
            active_session = session
            active_key = key
            break

    if not active_session:
        raise HTTPException(status_code=404, detail="未找到冲突的委托任务")

    if payload.action == "cancel_and_new":
        # 取消当前委托
        active_session.cancel_event.set()
        try:
            await active_session.agent.cancel()
        except Exception:
            pass
        _active_delegations.pop(active_key, None)

        # 找到排队的消息，重新启动 _handle_chat_task
        queued_msg = None
        for q in active_session.queued_messages:
            if q.get("task_id") == payload.task_id:
                queued_msg = q
                break
        if queued_msg:
            active_session.queued_messages.remove(queued_msg)
            # 重新处理排队的消息
            t3 = asyncio.create_task(
                _handle_chat_task(
                    queued_msg["task_id"],
                    ChatRequest(**queued_msg["payload"]),
                    [TargetHost(**t) for t in queued_msg["targets"]],
                    queued_msg["host_context"],
                    queued_msg["conversation_id"],
                )
            )
            t3.add_done_callback(
                lambda t: asyncio.ensure_future(
                    _on_task_crash(queued_msg["task_id"], t)
                ) if t.exception() else None
            )
        return {"task_id": payload.task_id, "status": "cancelled", "action": "cancel_and_new", "reprocessing": True}
    elif payload.action == "queue":
        return {"task_id": payload.task_id, "status": "queued", "action": "queue"}
    else:
        raise HTTPException(status_code=400, detail=f"无效的 action: {payload.action}")


@router.get("/delegate/status/{task_id}")
async def api_delegate_status(task_id: str) -> dict[str, Any]:
    """查询委托任务状态"""
    from app.delegate.executor import _active_delegations

    for key, session in _active_delegations.items():
        if session.task_id == task_id:
            return {
                "task_id": task_id,
                "active": True,
                "agent": session.agent.display_name,
            }
    return {"task_id": task_id, "active": False}


class DelegatePermissionRequest(BaseModel):
    task_id: str
    permission_id: str
    approved: bool


@router.post("/delegate/respond-permission")
async def api_delegate_respond_permission(payload: DelegatePermissionRequest) -> dict[str, Any]:
    """用户响应 Claude Code 的权限请求（当前版本自动同意，此 API 保留兼容）"""
    return {
        "task_id": payload.task_id,
        "permission_id": payload.permission_id,
        "approved": payload.approved,
        "status": "ok",
        "note": "权限已由系统自动处理",
    }


# ── 对话归档 API ──

class PauseConversationRequest(BaseModel):
    conversation_id: int


class ResumeConversationRequest(BaseModel):
    conversation_id: int
    host: HostPayload


@router.post("/conversations/{conv_id}/pause")
async def api_pause_conversation(conv_id: int) -> dict[str, Any]:
    """暂停对话：LLM 总结当前进度，标记为 paused"""
    from app.database import pause_conversation, list_conversation_messages
    from aios.llm import request_text_from_messages

    messages = await list_conversation_messages(conv_id)
    if not messages:
        raise HTTPException(status_code=404, detail="对话不存在或为空")

    # LLM 生成任务进度总结
    conv_text = "\n".join(
        f"[{m['role']}]: {m['content'][:300]}" for m in messages[-10:]
    )
    summary = ""
    try:
        settings = await load_runtime_settings()
        raw = await request_text_from_messages(
            settings.get("api_base", "https://api.deepseek.com"),
            settings.get("api_key", ""),
            settings.get("aux_model", "deepseek-chat"),
            [
                {"role": "system", "content": "用一句话总结这段人机对话的当前任务进度（中文，30字以内），方便下次恢复时理解上下文。"},
                {"role": "user", "content": conv_text},
            ],
            timeout_sec=20,
        )
        from app.llm_client import extract_json
        summary = raw.strip()[:120]
    except Exception:
        summary = "任务进行中"

    await pause_conversation(conv_id, summary)
    return {"ok": True, "conversation_id": conv_id, "status": "paused", "task_summary": summary}


@router.post("/conversations/{conv_id}/resume")
async def api_resume_conversation(conv_id: int) -> dict[str, Any]:
    """恢复暂停的对话"""
    from app.database import resume_conversation

    conv = await resume_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    return {
        "ok": True,
        "conversation_id": conv_id,
        "status": "active",
        "task_summary": conv.get("task_summary", ""),
    }


@router.post("/conversations/{conv_id}/archive")
async def api_archive_conversation(conv_id: int) -> dict[str, Any]:
    """归档对话"""
    from app.database import archive_conversation

    await archive_conversation(conv_id)
    return {"ok": True, "conversation_id": conv_id, "status": "archived"}


@router.get("/conversations/{host_id}/paused")
async def api_list_paused_conversations(host_id: int) -> list[dict[str, Any]]:
    """列出暂停中的对话"""
    from app.database import list_paused_conversations
    return await list_paused_conversations(host_id)
