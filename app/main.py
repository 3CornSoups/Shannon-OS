from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.connection import pool as ssh_pool
from app.database import init_db
from app.routers import (
    alert_rules,
    alerts,
    chat,
    files,
    history,
    hosts,
    monitoring,
    settings as settings_router,
    terminal,
    tools,
)

app = FastAPI(title="Shannon OS Agent API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由模块
app.include_router(hosts.router)
app.include_router(chat.router)
app.include_router(settings_router.router)
app.include_router(terminal.router)
app.include_router(files.router)
app.include_router(monitoring.router)
app.include_router(history.router)
app.include_router(alert_rules.router)
app.include_router(alerts.router)
app.include_router(tools.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


logger = logging.getLogger("uvicorn")


@app.on_event("startup")
async def startup_event():
    await init_db()
    await ssh_pool.start()
    logging.basicConfig(level=logging.INFO)

    from app.monitor_scheduler import MonitorScheduler
    app.state.monitor_scheduler = MonitorScheduler()
    await app.state.monitor_scheduler.start()

    web_dist_path = Path(__file__).resolve().parent.parent / "web" / "dist"
    if web_dist_path.exists():

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path.startswith("api/") or full_path == "api":
                raise HTTPException(status_code=404)
            file_path = web_dist_path / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(web_dist_path / "index.html"))
    else:
        logger.warning(f"前端构建目录不存在：{web_dist_path}，请先执行 cd web && npm run build")
        # 开发模式下提示用户
        @app.get("/")
        async def dev_hint():
            return {"status": "dev_mode", "message": "后端运行正常。前端请执行: cd web && npm install && npm run dev",
                    "api_docs": "/docs"}


@app.on_event("shutdown")
async def shutdown_event():
    from app.repl_sessions import close_all_sessions as _close_repl

    if hasattr(app.state, "monitor_scheduler"):
        await app.state.monitor_scheduler.stop()
    await _close_repl()
    await ssh_pool.stop()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
