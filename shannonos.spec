# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包规格 — Shannon OS 独立 exe"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

# 要打包的 Python 包
hidden_imports = [
    "app", "app.main", "app.agent", "app.conversation", "app.connection",
    "app.database", "app.errors", "app.events", "app.executor",
    "app.files", "app.llm_client", "app.logger", "app.models",
    "app.monitor", "app.prompts", "app.schemas", "app.security",
    "app.settings", "app.speech", "app.terminal", "app.voice", "app.voice_router",
    "app.routers", "app.routers.chat", "app.routers.files", "app.routers.history",
    "app.routers.hosts", "app.routers.monitoring", "app.routers.settings",
    "app.routers.terminal", "app.routers.alert_rules", "app.routers.alerts",
    "app.routers.tools",
    "app.delegate", "app.delegate.base", "app.delegate.claude_code",
    "app.delegate.context_builder",
    "app.delegate.executor", "app.delegate.reviewer", "app.delegate.install",
    "app.delegate.tool_detector",
    "app.repl_sessions",
    "app.batch_executor",
    # 第三方依赖
    "fastapi", "uvicorn", "starlette", "pydantic",
    "asyncssh", "paramiko", "httpx", "aiosqlite",
    "anyio", "sniffio", "h11", "httpcore",
    "websockets", "cryptography", "bcrypt", "pynacl",
]

# 要排除的模块（减小体积）
excluded = [
    "tkinter", "test", "unittest", "pydoc", "distutils",
    "setuptools", "pip", "wheel", "pkg_resources",
]

# 补充缺失的隐式导入
hidden_imports.extend([
    "jaraco.text", "jaraco.context", "jaraco.functools",
    "platformdirs", "platformdirs.windows", "platformdirs.macos", "platformdirs.unix",
])

# 数据文件：前端静态资源
datas = []
web_dist = ROOT / "web" / "dist"
if web_dist.exists():
    datas.append((str(web_dist), "web/dist"))

# 二进制依赖
binaries = []

a = Analysis(
    [str(ROOT / "build_standalone.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        str(Path("C:/Users/huchaolong/AppData/Local/Programs/Python/Python311/Lib/site-packages/PyInstaller/hooks/rthooks/pyi_rth_multiprocessing.py")),
        str(Path("C:/Users/huchaolong/AppData/Local/Programs/Python/Python311/Lib/site-packages/_pyinstaller_hooks_contrib/rthooks/pyi_rth_cryptography_openssl.py")),
        str(Path("C:/Users/huchaolong/AppData/Local/Programs/Python/Python311/Lib/site-packages/PyInstaller/hooks/rthooks/pyi_rth_inspect.py")),
        str(Path("C:/Users/huchaolong/AppData/Local/Programs/Python/Python311/Lib/site-packages/_pyinstaller_hooks_contrib/rthooks/pyi_rth_traitlets.py")),
        str(Path("C:/Users/huchaolong/AppData/Local/Programs/Python/Python311/Lib/site-packages/_pyinstaller_hooks_contrib/rthooks/pyi_rth_pywintypes.py")),
    ],
    excludes=excluded,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ShannonOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "desktop" / "icon.png") if (ROOT / "desktop" / "icon.png").exists() else None,
)
