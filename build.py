from __future__ import annotations

import os
import sys
import zipfile
import subprocess
import fnmatch
from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT = ROOT.parent / "shannonOS.zip"

# ---- 排除规则 ----
EXCLUDE_GLOBS = [
    "build",
    "build/**",
    "desktop/dist-electron",
    "desktop/dist-electron/**",
    "__pycache__",
    "**/__pycache__/**",
    ".git",
    ".git/**",
    ".trae",
    ".trae/**",
    ".claude",
    ".claude/**",
    ".vscode",
    ".vscode/**",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "build.bat",
    "build.py",
    "*.zip",
    "PRD_*.md",
    "web/src/components/HelloWorld.vue",
    "web/src/stores/counter.js",
    "web/src/assets/**",
    "web/dist/architecture.drawio",
    "web/dist/project_structure.drawio",
    "web/public/architecture.drawio",
    "web/public/architecture.html",
    "web/public/project_structure.drawio",
    "scripts/build.bat",
]

# ---- 调试：打印最终清单 ----
DRY_RUN = "--dry-run" in sys.argv


def should_exclude(rel_path: str) -> bool:
    basename = os.path.basename(rel_path)
    for pattern in EXCLUDE_GLOBS:
        if rel_path == pattern or rel_path.startswith(pattern.rstrip("/") + "/") or rel_path.startswith(pattern.rstrip("/") + "\\"):
            return True
        if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(basename, pattern):
            return True
    return False


def main():
    # 1. 确认前端已构建
    dist_dir = ROOT / "web" / "dist"
    if not dist_dir.exists() or not (dist_dir / "index.html").exists():
        print("前端未构建，正在构建...")
        subprocess.run(["npm", "run", "build"], cwd=str(ROOT / "web"), check=True)

    # 2. 收集文件
    files_to_pack: list[tuple[str, str]] = []
    for root, dirs, filenames in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".") or d == ".env.example"]
        for fn in filenames:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            if should_exclude(rel):
                continue
            files_to_pack.append((full, rel))

    if DRY_RUN:
        print(f"将打包 {len(files_to_pack)} 个文件:")
        for _, rel in sorted(files_to_pack, key=lambda x: x[1]):
            print(f"  {rel}")
        return

    # 3. 创建 zip
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in files_to_pack:
            zf.write(full, f"shannonOS/{rel}")

    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"\n✅ 打包完成: {OUTPUT}")
    print(f"   大小: {size_mb:.1f} MB")
    print(f"   文件数: {len(files_to_pack)}")


if __name__ == "__main__":
    main()
