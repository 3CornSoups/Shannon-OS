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
from app.models import AgentConfig, AgentOutput, ReActCommand, ReActDone, ReActAsk
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

async def _parse_first_action(
    agent: ShannonAgent, raw_output: str, payload: ChatRequest, host_context: dict | None
) -> ReActCommand | ReActDone | ReActAsk:
    """从流式响应中解析首个 ReAct 动作"""
    data = extract_json(raw_output)
    if not data:
        # fallback: 非流式重试
        plan = await agent.stage2_plan_generate(payload.prompt, host_context or {}, payload.mode)
        if plan.commands_plan:
            first = plan.commands_plan[0]
            return ReActCommand(command=first.command, purpose=first.purpose, reasoning=plan.reasoning)
        return ReActDone(message=plan.reply_message or raw_output)
    action_type = data.get("action")
    if action_type == "run":
        return ReActCommand(**data)
    elif action_type == "done":
        return ReActDone(**data)
    elif action_type == "ask":
        return ReActAsk(**data)
    # 兼容旧格式：有 commands_plan 则取第一条
    commands = data.get("commands_plan", [])
    if commands:
        return ReActCommand(command=commands[0]["command"], purpose=commands[0].get("purpose", ""),
                            reasoning=data.get("reasoning", ""))
    return ReActDone(message=data.get("reply_message", raw_output))


async def _fallback_first_action(
    agent: ShannonAgent, payload: ChatRequest, host_context: dict | None
) -> ReActCommand | ReActDone | ReActAsk:
    """完全 fallback：非流式生成第一个动作"""
    plan = await agent.stage2_plan_generate(payload.prompt, host_context or {}, payload.mode)
    plan = agent.stage3_plan_validate(plan)
    if plan.commands_plan:
        first = plan.commands_plan[0]
        return ReActCommand(command=first.command, purpose=first.purpose, reasoning=plan.reasoning)
    return ReActDone(message=plan.reply_message or "已处理完成")


def _estimate_risk(action: ReActCommand | ReActDone | ReActAsk) -> str:
    """使用 agent 的统一风险判断逻辑"""
    from app.agent import assess_risk
    if isinstance(action, ReActCommand):
        risk, _ = assess_risk(action.command)
        return risk
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
    target = TargetHost(host_id=host_id, **host_data)

    if not target.host or not target.host.strip():
        raise HTTPException(status_code=400, detail="请填写服务器地址")
    if not target.username or not target.username.strip():
        raise HTTPException(status_code=400, detail="请填写SSH用户名")

    has_password = bool(target.password and target.password.strip())
    has_key = bool(target.private_key and target.private_key.strip())
    if not has_password and not has_key:
        raise HTTPException(status_code=400, detail="请填写SSH密码或私钥后再执行。")

    task_id = str(uuid.uuid4())
    host_context = await get_host_context(target.host_id) if target.host_id else None

    # 如果密码是掩码 ***，从 DB 加载真实密码
    if target.password == "***" and host_context:
        real_pwd = host_context.get("last_pwd")
        if real_pwd and real_pwd != "***":
            target.password = real_pwd

    # 保存或更新主机信息（排除 *** 掩码值，防止覆盖真实密码）
    if target.host_id and host_context:
        raw_pwd = target.password.strip() if target.password else ""
        if raw_pwd and raw_pwd != "***":
            await upsert_host_context(
                name=host_context["name"],
                host=host_context["host"],
                port=host_context["port"],
                username=host_context["username"],
                last_pwd=raw_pwd,
            )
    else:
        target.host_id = await upsert_host_context(
            name=target.name,
            host=target.host,
            port=target.port,
            username=target.username,
            last_pwd=target.password.strip() if target.password else None,
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

    asyncio.create_task(
        _handle_chat_task(task_id, payload, target, host_context, conversation_id)
    )
    return {"task_id": task_id, "status": "accepted", "conversation_id": conversation_id}


async def _handle_chat_task(
    task_id: str,
    payload: ChatRequest,
    target: TargetHost,
    host_context: Dict[str, Any] | None,
    conversation_id: int | None = None,
):
    try:
        current_agent = await _create_agent()

        # 加载历史消息到 ConversationManager
        # 注意：用户消息已由 api_chat 存入 DB，历史中已包含
        if conversation_id:
            history = await list_conversation_messages(conversation_id)
            for msg in history:
                if msg["role"] == "user":
                    current_agent.conversation.add_user_message(msg["content"])
                elif msg["role"] == "assistant":
                    current_agent.conversation.add_assistant_message(msg["content"])

        await event_store.emit(task_id, {"type": "status", "message": "正在分析意图..."})

        # 构建系统提示词
        if payload.mode == "chat":
            # 纯聊天模式：直接流式回复，不解析 JSON/命令
            system_prompt = current_agent._build_system_prompt(
                "chat", host_context or {}, stage="chat"
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

        # agent 模式：意图分析与计划生成
        system_prompt = current_agent._build_system_prompt(
            payload.mode, host_context or {}, stage="plan"
        )
        current_agent.conversation.set_system_prompt(system_prompt)

        full_response: list[str] = []
        thinking = ""
        last_raw = ""

        # 优先尝试 tool calling 获取结构化输出
        first_action = await current_agent._request_first_action(
            payload.prompt, host_context or {}, payload.mode
        )

        if first_action is None:
            # tool calling 失败，回退到流式 + JSON 解析
            async for chunk in current_agent.stream_reply(
                payload.prompt
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
            first_action = await _parse_first_action(current_agent, raw_output, payload, host_context)
            if first_action is None:
                first_action = await _fallback_first_action(current_agent, payload, host_context)
        else:
            # tool calling 成功，将结构化的内容流式输出给前端
            action_json = json.dumps(first_action.model_dump(), ensure_ascii=False)
            # 分段模拟流式输出
            chunk_size = 50
            for i in range(0, len(action_json), chunk_size):
                await event_store.emit(task_id, {
                    "type": "raw_content", "stage": "plan",
                    "content": action_json[i:i + chunk_size],
                })
                await asyncio.sleep(0.02)
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
            return

        # agent 模式：等待用户确认执行
        if payload.mode == "agent":
            reason = first_action.reasoning or "请确认执行以下操作"
            # 构造展示用 plan 事件（兼容前端确认对话框）
            action_display = first_action.model_dump()
            await event_store.emit(task_id, {
                "type": "plan",
                "intent": "executing_task",
                "risk_level": _estimate_risk(first_action),
                "reasoning": first_action.reasoning,
                "reply_message": first_action.message if hasattr(first_action, "message") else "",
                "commands_plan": [{"command": action_display.get("command", ""), "purpose": action_display.get("purpose", "")}],
            })
            wait_event = asyncio.Event()
            pending_events[task_id] = wait_event
            pending_confirmations[task_id] = {
                "target": target, "host_id": target.host_id,
                "host_context": host_context, "mode": payload.mode,
                "wait_event": wait_event, "risk_level": _estimate_risk(first_action),
            }
            await append_audit_record(
                host_id=target.host_id, task_id=task_id, reason=reason,
                risk_level="LOW", approved=False, operator_name=None,
            )
            await event_store.emit(task_id, {"type": "risk_hold", "reason": reason, "task_id": task_id,
                                              "risk_level": "LOW",
                                              "commands_plan": [{"command": action_display.get("command", ""), "purpose": action_display.get("purpose", "")}]})
            try:
                await asyncio.wait_for(wait_event.wait(), timeout=600)
            except asyncio.TimeoutError:
                pending_confirmations.pop(task_id, None)
                pending_events.pop(task_id, None)
                await event_store.emit(task_id, {"type": "done", "message": "确认超时，已自动取消。"})
                return
            pending_confirmations.pop(task_id, None)
            pending_events.pop(task_id, None)

        # 切换为 ReAct 系统提示词
        react_prompt = current_agent._build_system_prompt(
            payload.mode, host_context or {}, stage="react"
        )
        current_agent.conversation.set_system_prompt(react_prompt)

        # ReAct 循环执行
        await event_store.emit(task_id, {"type": "status", "message": "正在执行命令..."})

        # 将首次 action 加入 conversation（流式响应中已含，这里再标注）
        current_agent.conversation.add_assistant_message(
            json.dumps(first_action.model_dump(), ensure_ascii=False)
        )

        executor = ExecutorRouter.create_executor(target)
        max_iterations = 20
        iteration = 0
        accumulated_stdout = []
        accumulated_stderr = []
        final_reply = first_action.message if hasattr(first_action, "message") else ""

        while iteration < max_iterations:
            iteration += 1
            await event_store.emit(task_id, {"type": "iteration_start", "iteration": iteration, "max_iterations": max_iterations})

            if isinstance(first_action, ReActCommand) and first_action.command:
                cmd = first_action.command
                # 保存 LLM 的决策到 DB
                if target.host_id:
                    await append_chat_message(
                        target.host_id, "assistant",
                        f"**思考:** {first_action.reasoning or ''}\n\n**命令:** `{cmd}`\n**目的:** {first_action.purpose or ''}",
                        {"type": "react_action", "action": "run", "command": cmd,
                         "purpose": first_action.purpose, "reasoning": first_action.reasoning},
                        conversation_id=conversation_id,
                    )

                await event_store.emit(task_id, {"type": "command_start", "command": cmd, "purpose": first_action.purpose,
                                                  "reasoning": first_action.reasoning})

                # 执行命令
                is_download = any(kw in cmd for kw in ["wget", "curl", "git clone", "tar"])
                timeout = 300 if is_download else 60

                async def on_output(line: str, is_stderr: bool, _cmd=cmd):
                    try:
                        await event_store.emit(task_id, {"type": "command_output", "command": _cmd, "line": line, "is_stderr": is_stderr})
                    except Exception:
                        pass

                try:
                    result = await executor.run(cmd, ExecContext(timeout_sec=timeout, on_output=on_output))
                    await event_store.emit(task_id, {"type": "command_result", "command": cmd,
                                                      "stdout": result.stdout, "stderr": result.stderr,
                                                      "returncode": result.returncode})
                    accumulated_stdout.append(result.stdout or "")
                    accumulated_stderr.append(result.stderr or "")

                    # 保存命令结果到 DB
                    if target.host_id:
                        result_summary = f"返回码: {result.returncode}"
                        if result.stdout:
                            result_summary += f"\n标准输出: {(result.stdout[:500])}"
                        if result.stderr:
                            result_summary += f"\n错误输出: {(result.stderr[:500])}"
                        await append_chat_message(
                            target.host_id, "assistant",
                            result_summary,
                            {"type": "react_result", "command": cmd, "returncode": result.returncode,
                             "stdout": result.stdout, "stderr": result.stderr},
                            conversation_id=conversation_id,
                        )

                    # 将执行结果反馈给 LLM
                    current_agent.conversation.add_tool_result(cmd, result.returncode, result.stdout, result.stderr)

                except Exception as exc:
                    error_msg = str(exc)
                    accumulated_stderr.append(error_msg)
                    await event_store.emit(task_id, {"type": "command_result", "command": cmd,
                                                      "stdout": None, "stderr": error_msg, "returncode": -1})
                    if target.host_id:
                        await append_chat_message(
                            target.host_id, "assistant",
                            f"命令执行异常: {error_msg}",
                            {"type": "react_result", "command": cmd, "returncode": -1, "stdout": None, "stderr": error_msg},
                            conversation_id=conversation_id,
                        )
                    current_agent.conversation.add_tool_result(cmd, -1, "", error_msg)

            elif isinstance(first_action, ReActDone):
                final_reply = first_action.message
                await event_store.emit(task_id, {"type": "react_done", "message": final_reply})
                break

            elif isinstance(first_action, ReActAsk):
                final_reply = first_action.message
                await event_store.emit(task_id, {"type": "react_ask", "message": final_reply, "reasoning": first_action.reasoning})
                break

            # 调用 LLM 获取下一步动作
            try:
                first_action = await current_agent._request_react_action()
            except Exception as exc:
                final_reply = f"LLM 调用失败: {exc}"
                await event_store.emit(task_id, {"type": "error", "message": final_reply})
                break

        else:
            final_reply = f"已达到最大迭代次数 ({max_iterations})，执行终止。"
            await event_store.emit(task_id, {"type": "done", "message": final_reply})

        # 所有迭代完成，记录操作日志
        await append_operation_log(
            host_id=target.host_id, mode=payload.mode, intent="react_execution",
            commands_plan=None, risk_level=None, status="completed",
            stdout="\n".join(filter(None, accumulated_stdout)),
            stderr="\n".join(filter(None, accumulated_stderr)),
            task_id=task_id,
        )

        # done 事件（尚未触发过的场景）
        if not isinstance(first_action, (ReActDone, ReActAsk)):
            await event_store.emit(task_id, {"type": "done", "message": final_reply})
            if target.host_id:
                await append_chat_message(
                    target.host_id, "assistant", final_reply or "执行完成",
                    conversation_id=conversation_id,
                )
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
                "plan": plan_result.model_dump(),
                "commands": [cmd.model_dump() for cmd in plan_result.commands_plan],
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
                data = await asyncio.wait_for(queue.get(), timeout=600)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                if data.get("type") in ("done", "error"):
                    break
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'error', 'message': '连接超时'}, ensure_ascii=False)}\n\n"
        finally:
            event_store.unsubscribe(task_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
