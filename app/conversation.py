"""对话上下文管理器"""

from __future__ import annotations


class ConversationManager:
    """管理发送给 LLM 的消息列表，支持自动截断和智能折叠。"""

    def __init__(self, max_messages: int = 40):
        self.max_messages = max_messages
        self.messages: list[dict[str, str]] = []

    def set_system_prompt(self, prompt: str):
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0] = {"role": "system", "content": prompt}
        else:
            self.messages.insert(0, {"role": "system", "content": prompt})

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
        self._trim()

    def _trim(self):
        if len(self.messages) <= self.max_messages:
            return
        system = [m for m in self.messages if m["role"] == "system"]
        others = [m for m in self.messages if m["role"] != "system"]
        keep_count = self.max_messages - len(system)
        if keep_count <= 0:
            self.messages = system[-1:]
            return

        old_tool_results = sum(
            1 for m in others[:-keep_count]
            if m["role"] == "user" and m["content"].startswith("## 命令执行结果")
        )

        if old_tool_results > 2:
            old_items = others[:-keep_count]
            new_items = list(others[-keep_count:])
            discarded = []
            for m in old_items:
                if m["role"] == "user" and m["content"].startswith("## 命令执行结果"):
                    for line in m["content"].split("\n"):
                        if line.startswith("命令:"):
                            discarded.append(line)
                            break
            if discarded:
                summary = (
                    "## 历史执行摘要（已折叠）\n"
                    + "\n".join(discarded)
                    + "\n\n(以上历史命令已折叠以节省空间，"
                      "请基于当前上下文继续工作)"
                )
                new_items.insert(0, {"role": "user", "content": summary})
            self.messages = system + new_items
        else:
            self.messages = system + others[-keep_count:]

    def get_messages(self) -> list[dict[str, str]]:
        return self.messages

    def clear(self):
        self.messages.clear()

    def add_tool_result(self, command: str, returncode: int, stdout: str, stderr: str):
        MAX_OUTPUT = 2000
        safe_stdout = (stdout or "")[:MAX_OUTPUT]
        safe_stderr = (stderr or "")[:MAX_OUTPUT]
        truncated = ""
        if (stdout and len(stdout) > MAX_OUTPUT) or (stderr and len(stderr) > MAX_OUTPUT):
            truncated = "\n\n(输出过长已截断)"
        content = (
            f"## 命令执行结果\n"
            f"命令: `{command}`\n"
            f"返回码: {returncode}\n"
            f"标准输出:\n```\n{safe_stdout or '(空)'}\n```\n"
            f"错误输出:\n```\n{safe_stderr or '(空)'}\n```\n"
            f"{'命令成功完成。' if returncode == 0 else '命令执行失败。'}"
            f"{truncated}"
        )
        self.messages.append({"role": "user", "content": content})
        self._trim()
