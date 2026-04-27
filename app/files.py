from __future__ import annotations

import asyncio
import base64
import os
from dataclasses import dataclass
from typing import Any

import asyncssh
import paramiko
from pydantic import BaseModel

from app.database import get_host_context
from app.executor import TargetHost, ExecContext, SSHExecutor


class FileListRequest(BaseModel):
    host_id: int | None = None
    host: str
    port: int = 22
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    path: str = "/"


class FileReadRequest(BaseModel):
    host_id: int | None = None
    host: str
    port: int = 22
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    path: str


class FileWriteRequest(BaseModel):
    host_id: int | None = None
    host: str
    port: int = 22
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    path: str
    content: str


class FileOperationRequest(BaseModel):
    host_id: int | None = None
    host: str
    port: int = 22
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    path: str
    new_name: str | None = None
    destination: str | None = None


async def _build_target(payload: BaseModel) -> TargetHost:
    password = payload.password
    private_key = payload.private_key

    # 如果密码未传或是掩码（***），尝试从 DB 加载存储的凭证
    if (not password or password == "***") and payload.host_id:
        stored = await get_host_context(payload.host_id, decrypt_pwd=True)
        if stored:
            if not password or password == "***":
                password = stored.get("last_pwd") or password
            if not private_key:
                private_key = stored.get("private_key") or private_key
            if not payload.username:
                payload.username = stored.get("username")
            if not payload.port or payload.port == 22:
                payload.port = stored.get("port", 22)

    return TargetHost(
        host_id=payload.host_id,
        name="file-explorer",
        host=payload.host,
        port=payload.port,
        username=payload.username,
        password=password,
        private_key=private_key,
        use_local=False,
    )


async def _exec_ssh_command(target: TargetHost, command: str, timeout: int = 15) -> dict:
    executor = SSHExecutor(target)
    context = ExecContext(cwd=None, timeout_sec=timeout)
    result = await executor.run(command, context)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


async def list_directory(payload: FileListRequest) -> dict[str, Any]:
    target = await _build_target(payload)
    path = payload.path.rstrip("/") or "/"

    # 使用 find + stat 替代 shell globbing，避免路径含空格等问题
    cmd = f"find {path} -maxdepth 1 -mindepth 1 -exec stat -c '%F|%s|%Y|%n' {{}} \\; 2>/dev/null"
    result = await _exec_ssh_command(target, cmd)

    if result["returncode"] != 0 or not result["stdout"].strip():
        # 备用方案：使用 ls -la 并解析
        cmd2 = f"ls -la {path} 2>&1"
        result2 = await _exec_ssh_command(target, cmd2)
        if result2["returncode"] != 0:
            return {"ok": False, "message": f"无法访问目录: {result2['stderr'] or result2['stdout']}"}
        # 解析 ls -la 输出
        return await _parse_ls_output(target, path, result2["stdout"])

    entries = []
    for line in result["stdout"].strip().splitlines():
        if not line.strip():
            continue
        try:
            parts = line.strip().split("|", 3)
            if len(parts) < 4:
                continue
            file_type_raw = parts[0].strip()
            size = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
            mtime = int(parts[2].strip()) if parts[2].strip().isdigit() else 0
            name = parts[3].strip()

            basename = os.path.basename(name)
            if basename in (".", ".."):
                continue

            is_dir = "directory" in file_type_raw
            is_link = "link" in file_type_raw

            ext = os.path.splitext(basename)[1].lower() if not is_dir else ""
            icon_type = _get_icon_type(basename, ext, is_dir)

            entries.append({
                "name": basename,
                "path": name,
                "is_dir": is_dir,
                "is_link": is_link,
                "size": size,
                "mtime": mtime,
                "icon_type": icon_type,
            })
        except (ValueError, IndexError):
            continue

    entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

    return {"ok": True, "path": path, "entries": entries}


async def _parse_ls_output(target: TargetHost, path: str, ls_output: str) -> dict[str, Any]:
    """解析 ls -la 输出"""
    entries = []
    for line in ls_output.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("total"):
            continue

        parts = line.split(None, 8)
        if len(parts) < 9:
            continue

        perm = parts[0]
        size_str = parts[4]
        name = parts[8]

        if name in (".", ".."):
            continue

        is_dir = perm.startswith("d")
        is_link = perm.startswith("l")
        size = int(size_str) if size_str.isdigit() else 0
        ext = os.path.splitext(name)[1].lower() if not is_dir else ""
        icon_type = _get_icon_type(name, ext, is_dir)
        full_path = f"{path.rstrip('/')}/{name}" if path != "/" else f"/{name}"

        entries.append({
            "name": name,
            "path": full_path,
            "is_dir": is_dir,
            "is_link": is_link,
            "size": size,
            "mtime": 0,
            "icon_type": icon_type,
        })

    entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {"ok": True, "path": path, "entries": entries}


def _get_icon_type(name: str, ext: str, is_dir: bool) -> str:
    if is_dir:
        special_dirs = {"src", "lib", "libs", "node_modules", ".git", ".svn", ".vscode", "__pycache__"}
        if name in special_dirs:
            return "folder-special"
        return "folder"

    code_exts = {".py", ".js", ".ts", ".vue", ".jsx", ".tsx", ".c", ".cpp", ".h", ".go", ".rs", ".java", ".rb", ".php", ".sh", ".bash", ".zsh"}
    config_exts = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".xml"}
    doc_exts = {".md", ".txt", ".rst", ".doc", ".docx", ".pdf"}
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp"}
    data_exts = {".csv", ".sql", ".db", ".sqlite"}

    if ext in code_exts:
        return "code"
    if ext in config_exts:
        return "config"
    if ext in doc_exts:
        return "document"
    if ext in image_exts:
        return "image"
    if ext in data_exts:
        return "data"
    if name.startswith("."):
        return "hidden"
    return "file"


async def read_file(payload: FileReadRequest) -> dict[str, Any]:
    target = await _build_target(payload)
    path = payload.path

    check_cmd = f"stat -c '%F|%s' {path} 2>&1"
    check = await _exec_ssh_command(target, check_cmd)
    if check["returncode"] != 0:
        return {"ok": False, "message": f"文件不存在: {check['stderr']}"}

    parts = check["stdout"].strip().split("|")
    if len(parts) >= 1 and "directory" in parts[0]:
        return {"ok": False, "message": "不能读取目录，请选择文件"}

    size = int(parts[1].strip()) if len(parts) >= 2 and parts[1].strip().isdigit() else 0
    if size > 2 * 1024 * 1024:
        return {"ok": False, "message": f"文件过大 ({size} bytes)，不支持预览超过 2MB 的文件"}

    cmd = f"cat {path} 2>&1"
    result = await _exec_ssh_command(target, cmd, timeout=10)

    if result["returncode"] != 0:
        return {"ok": False, "message": f"读取文件失败: {result['stderr']}"}

    content = result["stdout"]
    ext = os.path.splitext(path)[1].lower()
    language = _get_language(ext)

    return {
        "ok": True,
        "path": path,
        "content": content,
        "size": size,
        "language": language,
    }


def _get_language(ext: str) -> str:
    mapping = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".vue": "html", ".jsx": "jsx", ".tsx": "tsx",
        ".c": "c", ".cpp": "cpp", ".h": "c",
        ".go": "go", ".rs": "rust", ".java": "java",
        ".rb": "ruby", ".php": "php", ".sh": "bash",
        ".bash": "bash", ".zsh": "bash",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".toml": "toml", ".ini": "ini", ".cfg": "ini",
        ".conf": "ini", ".xml": "xml",
        ".md": "markdown", ".txt": "text", ".rst": "rst",
        ".html": "html", ".css": "css", ".scss": "scss",
        ".sql": "sql", ".env": "env",
    }
    return mapping.get(ext, "text")


async def write_file(payload: FileWriteRequest) -> dict[str, Any]:
    target = await _build_target(payload)
    path = payload.path
    content = payload.content

    # 使用 base64 编码避免 heredoc 被 SSH 执行器的额外命令污染
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

    # 使用 printf '%s' 避免 printf 对 \n 的特殊解释，确保 base64 字符串原样传递
    cmd = f"printf '%s' '{encoded}' | base64 -d > {path}"
    result = await _exec_ssh_command(target, cmd, timeout=15)

    if result["returncode"] != 0:
        return {"ok": False, "message": f"写入文件失败: {result['stderr']}"}

    return {"ok": True, "message": "文件保存成功", "path": path}


async def create_file_entry(payload: FileOperationRequest) -> dict[str, Any]:
    target = await _build_target(payload)
    path = payload.path
    is_dir = payload.new_name and payload.new_name.endswith("/")
    name = (payload.new_name or "").rstrip("/")

    if not name:
        return {"ok": False, "message": "请输入名称"}

    full_path = f"{path.rstrip('/')}/{name}"

    if is_dir:
        cmd = f"mkdir -p {full_path}"
    else:
        cmd = f"touch {full_path}"

    result = await _exec_ssh_command(target, cmd)
    if result["returncode"] != 0:
        return {"ok": False, "message": f"创建失败: {result['stderr']}"}

    return {"ok": True, "message": f"{'目录' if is_dir else '文件'}创建成功", "path": full_path, "is_dir": is_dir}


async def delete_entry(payload: FileOperationRequest) -> dict[str, Any]:
    target = await _build_target(payload)
    path = payload.path

    cmd = f"rm -rf {path}"
    result = await _exec_ssh_command(target, cmd)
    if result["returncode"] != 0:
        return {"ok": False, "message": f"删除失败: {result['stderr']}"}

    return {"ok": True, "message": "删除成功", "path": path}


async def rename_entry(payload: FileOperationRequest) -> dict[str, Any]:
    target = await _build_target(payload)
    old_path = payload.path
    new_name = payload.new_name

    if not new_name:
        return {"ok": False, "message": "请输入新名称"}

    parent = os.path.dirname(old_path)
    new_path = f"{parent}/{new_name}"

    cmd = f"mv {old_path} {new_path}"
    result = await _exec_ssh_command(target, cmd)
    if result["returncode"] != 0:
        return {"ok": False, "message": f"重命名失败: {result['stderr']}"}

    return {"ok": True, "message": "重命名成功", "old_path": old_path, "new_path": new_path}
