"""委托结果审核器 — 退出码检查 + 命令审计 + 目标达成判断（分段审核）"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from aios.security import assess_risk

logger = logging.getLogger(__name__)

# 输出摘要最大长度（字符）
MAX_SUMMARY_CHARS = 8000
# 分段审核阈值（超过此长度启用分段审核）
SEGMENT_THRESHOLD = 8000
# 每段最大长度
SEGMENT_SIZE = 4000


# ANSI 清洗
_ANSI_RE = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[PX^_][^\x1b]*\x1b\\\\')


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


def _extract_commands_from_output(output: str) -> list[str]:
    """从 Claude Code 输出中提取疑似执行的命令"""
    commands: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("$ ") or stripped.startswith("# "):
            commands.append(stripped[2:])
        elif re.match(r"^[a-zA-Z_][\w\-.]*\s+-", stripped):
            commands.append(stripped)
    return commands


async def review_delegation_result(
    api_base: str,
    api_key: str,
    model: str,
    user_input: str,
    delegate_output: str,
    exit_code: int,
    execution_time_sec: float,
    stderr: str = "",
    timeout_sec: int = 60,
) -> dict[str, Any]:
    """审核委托结果，支持分段审核"""
    from app.llm_client import request_text

    # 1. 退出码检查
    exit_ok = exit_code == 0

    # 2. 命令风险审计
    risk_warnings: list[str] = []
    clean_output = _strip_ansi(delegate_output)
    extracted_commands = _extract_commands_from_output(clean_output)
    for cmd in extracted_commands:
        risk, reason = assess_risk(cmd)
        if risk == "HIGH":
            risk_warnings.append(f"{cmd}: {reason}")

    # 3. 输出截断（用清洗后的输出）
    truncated = clean_output[:MAX_SUMMARY_CHARS]
    is_truncated = len(clean_output) > MAX_SUMMARY_CHARS

    # 4. 目标达成判断
    if not exit_ok and not clean_output.strip():
        # 进程执行失败且无 stdout，直接报告错误
        goal_result = {
            "status": "❌ 未达成",
            "reasoning": f"执行失败 (退出码 {exit_code})",
        }
    elif len(clean_output) > SEGMENT_THRESHOLD:
        goal_result = await _segmented_goal_review(
            api_base, api_key, model, user_input, clean_output, timeout_sec
        )
    else:
        goal_result = await _single_goal_review(
            api_base, api_key, model, user_input, truncated, timeout_sec
        )

    # 5. 提取变更文件列表
    files_changed = _extract_files_changed(clean_output)

    return {
        "agent": "claude_code",
        "exit_code": exit_code,
        "exit_ok": exit_ok,
        "goal_achieved": goal_result.get("status", "⚠️ 部分达成"),
        "goal_reasoning": goal_result.get("reasoning", ""),
        "execution_time_sec": execution_time_sec,
        "files_changed": files_changed,
        "risk_warnings": risk_warnings,
        "output_summary": truncated,
        "output_truncated": is_truncated,
        "stderr": stderr[:2000] if stderr else "",
    }


async def _single_goal_review(
    api_base: str,
    api_key: str,
    model: str,
    user_input: str,
    output: str,
    timeout_sec: int,
) -> dict:
    """单段目标达成判断"""
    system_prompt = (
        "你是任务审核助手。对比原始需求和执行输出，"
        "判断目标是否达成。只输出 JSON 对象。"
    )
    user_prompt = (
        f"## 用户原始需求\n{user_input}\n\n"
        f"## 执行输出\n{output}\n\n"
        f'请输出 JSON: {{"status": "✅ 达成|⚠️ 部分达成|❌ 未达成", "reasoning": "判断理由"}}'
    )

    try:
        from app.llm_client import extract_json, request_text

        raw = await request_text(api_base, api_key, model, system_prompt, user_prompt, timeout_sec)
        data = extract_json(raw)
        if data:
            return data
    except Exception:
        pass

    return {"status": "⚠️ 部分达成", "reasoning": "审核未能完成，请人工检查"}


async def _segmented_goal_review(
    api_base: str,
    api_key: str,
    model: str,
    user_input: str,
    full_output: str,
    timeout_sec: int,
) -> dict:
    """分段审核：将大量输出分段提交给 LLM，最后汇总判断"""
    segments = [
        full_output[i : i + SEGMENT_SIZE]
        for i in range(0, len(full_output), SEGMENT_SIZE)
    ]
    if len(segments) <= 1:
        return await _single_goal_review(
            api_base, api_key, model, user_input, full_output, timeout_sec
        )

    segment_summaries: list[str] = []
    for idx, seg in enumerate(segments):
        try:
            from app.llm_client import extract_json, request_text

            raw = await request_text(
                api_base, api_key, model,
                "你是任务审核助手。请用 1-2 句话总结这段执行输出的关键操作和结果。只输出摘要文本。",
                f"## 片段 {idx + 1}/{len(segments)}\n{seg}",
                timeout_sec=min(timeout_sec, 30),
            )
            segment_summaries.append(f"片段{idx + 1}: {raw.strip()}")
        except Exception:
            segment_summaries.append(f"片段{idx + 1}: (审核失败)")

    combined = "\n".join(segment_summaries)
    system_prompt = (
        "你是任务审核助手。以下是各段输出的摘要，"
        "请对比原始需求，判断整体目标是否达成。只输出 JSON 对象。"
    )
    user_prompt = (
        f"## 用户原始需求\n{user_input}\n\n"
        f"## 执行输出分段摘要\n{combined}\n\n"
        f'请输出 JSON: {{"status": "✅ 达成|⚠️ 部分达成|❌ 未达成", "reasoning": "整体判断理由"}}'
    )

    try:
        from app.llm_client import extract_json, request_text

        raw = await request_text(api_base, api_key, model, system_prompt, user_prompt, timeout_sec)
        data = extract_json(raw)
        if data:
            return data
    except Exception:
        pass

    return {"status": "⚠️ 部分达成", "reasoning": "分段审核未能完成，请人工检查"}


def _extract_files_changed(output: str) -> list[str]:
    """从输出中提取文件变更列表（增删改）"""
    files: set[str] = set()
    patterns = [
        r"(?:created|modified|deleted|changed|updated|写入|修改|创建|删除)\s*[:：]?\s*([/\w.\-]+)",
        r"([/\w.\-]+\.[a-zA-Z]+)\s*(?:已|被)?\s*(?:修改|更新|创建|删除|changed|modified)",
        r"```(?:diff|python|js|ts|go|java|rust|c|cpp|sh|yaml|json|toml|sql)?\s*\n.*?```",
    ]
    for line in output.splitlines():
        for pattern in patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for m in matches:
                if isinstance(m, str) and len(m) > 1 and m.count("/") > 0:
                    files.add(m.strip())
    return list(files)[:50]  # 最多 50 个文件
