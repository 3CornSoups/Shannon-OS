from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


def is_venv_active() -> bool:
    return sys.prefix != sys.base_prefix


def ensure_venv():
    root = Path(__file__).parent
    venv_path = root / ".venv"
    venv_python = venv_path / "Scripts" / "python.exe"

    if venv_python.exists():
        return str(venv_python)

    print("正在创建虚拟环境...")
    subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

    print("正在安装后端依赖...")
    pip = venv_path / "Scripts" / "pip.exe"
    subprocess.run([str(pip), "install", "-r", "requirements.txt"], check=True, cwd=str(root))

    return str(venv_python)


def ensure_frontend_deps():
    web_dir = Path(__file__).parent / "web"
    node_modules = web_dir / "node_modules"
    if node_modules.exists():
        return
    print("正在安装前端依赖...")
    subprocess.run(["npm", "install"], cwd=str(web_dir), check=True)


def open_browser(url: str) -> None:
    time.sleep(1.5)
    webbrowser.open(url)


if __name__ == "__main__":
    if not is_venv_active():
        python = None
        root = Path(__file__).parent
        venv_python = root / ".venv" / "Scripts" / "python.exe"

        if venv_python.exists():
            python = str(venv_python)
            print(f"检测到虚拟环境，使用: {python}")
        else:
            python = ensure_venv()
            ensure_frontend_deps()

        threading.Thread(target=open_browser, args=("http://127.0.0.1:8000",), daemon=True).start()
        subprocess.run([python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"])
    else:
        threading.Thread(target=open_browser, args=("http://127.0.0.1:8000",), daemon=True).start()
        import uvicorn
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
