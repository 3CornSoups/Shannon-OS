"""独立打包入口 — PyInstaller 启动脚本
打包后双击 exe 自动启动后端 + 打开浏览器
"""
import os
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn
from uvicorn.config import LOGGING_CONFIG


def open_browser(url: str, delay: float = 1.5):
    import time
    time.sleep(delay)
    webbrowser.open(url)


def main():
    # 禁用 uvicorn 的 access log，减少终端干扰
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(levelprefix)s %(message)s"
    LOGGING_CONFIG["formatters"]["access"]["fmt"] = "%(levelprefix)s %(client_addr)s - '%(request_line)s' %(status_code)s"

    port = 8278
    url = f"http://127.0.0.1:{port}"

    print(f"  Shannon OS 启动中...")
    print(f"  打开浏览器访问: {url}")
    print(f"  按 Ctrl+C 退出")
    print()

    # 延迟自动打开浏览器
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # 启动服务
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
