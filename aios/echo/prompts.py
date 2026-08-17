"""Echo 系统提示词 — 友善的日常聊天伙伴 + 记忆上下文注入。"""

from __future__ import annotations

ECHO_BASE_PROMPT = """你是「回声」（Echo），运行在 Shannon OS AIOS 上的日常聊天助手。

你的职责：
- 陪用户闲聊、回答各种问题（知识、想法、生活、技术均可）
- 记住用户问过什么、聊过什么，跨会话回找过往对话
- 基于长期记忆理解用户偏好与背景，给出贴合的回答
- 你只负责对话、信息管理与记忆整理，不执行任何系统/运维命令

风格：友善、自然、简洁。回答有实质内容，不空泛。
当你需要确认或澄清时，直接以提问结尾。"""

MEMORY_CONTEXT_PROMPT = """
以下是从记忆库检索到的上下文，供你参考（可能为空，忽略即可）：

【用户画像】
{profile}

【相关长期记忆】
{memory_hits}

【过往对话片段】
{conversation_recall}

【用户近期提问】
{recent_questions}"""


def build_system_prompt(context: dict) -> str:
    """把检索到的上下文拼进 system prompt。"""
    parts = [ECHO_BASE_PROMPT]
    profile = context.get("profile") or ""
    memory_hits = context.get("memory_hits") or []
    recall = context.get("conversation_recall") or []
    questions = context.get("recent_questions") or []

    if profile or memory_hits or recall or questions:
        block = MEMORY_CONTEXT_PROMPT.format(
            profile=profile or "（暂无）",
            memory_hits=_fmt_memory(memory_hits),
            conversation_recall=_fmt_recall(recall),
            recent_questions=_fmt_questions(questions),
        )
        parts.append(block)
    return "\n".join(parts)


def _fmt_memory(hits: list[dict]) -> str:
    if not hits:
        return "（无）"
    lines = []
    for h in hits:
        t = h.get("type", "fact")
        tag = {"preference": "偏好", "fact": "事实", "decision": "决策",
               "server_info": "服务器", "user_profile": "画像"}.get(t, t)
        lines.append(f"- [{tag}] {h.get('content', '')}")
    return "\n".join(lines) or "（无）"


def _fmt_recall(recall: list[dict]) -> str:
    if not recall:
        return "（无）"
    lines = []
    for m in recall:
        who = "用户" if m.get("role") == "user" else "你"
        lines.append(f"- {who}: {m.get('content', '')[:120]}")
    return "\n".join(lines)


def _fmt_questions(questions: list[dict]) -> str:
    if not questions:
        return "（无）"
    lines = [f"- {q.get('question', '')}" for q in questions]
    return "\n".join(lines)
