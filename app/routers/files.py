from __future__ import annotations

import logging

from fastapi import APIRouter

from app.files import (
    FileListRequest,
    FileOperationRequest,
    FileReadRequest,
    FileWriteRequest,
    create_file_entry,
    delete_entry,
    list_directory,
    read_file,
    rename_entry,
    write_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["files"])


@router.post("/files/list")
async def api_files_list(payload: FileListRequest) -> dict:
    try:
        return await list_directory(payload)
    except Exception as exc:
        logger.error(f"文件列表获取失败: {exc}")
        return {"ok": False, "message": str(exc)}


@router.post("/files/read")
async def api_files_read(payload: FileReadRequest) -> dict:
    try:
        return await read_file(payload)
    except Exception as exc:
        logger.error(f"文件读取失败: {exc}")
        return {"ok": False, "message": str(exc)}


@router.post("/files/write")
async def api_files_write(payload: FileWriteRequest) -> dict:
    try:
        return await write_file(payload)
    except Exception as exc:
        logger.error(f"文件写入失败: {exc}")
        return {"ok": False, "message": str(exc)}


@router.post("/files/create")
async def api_files_create(payload: FileOperationRequest) -> dict:
    try:
        return await create_file_entry(payload)
    except Exception as exc:
        logger.error(f"创建失败: {exc}")
        return {"ok": False, "message": str(exc)}


@router.post("/files/delete")
async def api_files_delete(payload: FileOperationRequest) -> dict:
    try:
        return await delete_entry(payload)
    except Exception as exc:
        logger.error(f"删除失败: {exc}")
        return {"ok": False, "message": str(exc)}


@router.post("/files/rename")
async def api_files_rename(payload: FileOperationRequest) -> dict:
    try:
        return await rename_entry(payload)
    except Exception as exc:
        logger.error(f"重命名失败: {exc}")
        return {"ok": False, "message": str(exc)}
