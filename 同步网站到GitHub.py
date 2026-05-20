# -*- coding: utf-8 -*-
"""
一键同步当前网站文件夹到 GitHub Pages 仓库。

用途：
1. 你在当前文件夹里更新了首页、组合介绍、组合的诞生等网页内容；
2. 运行本脚本；
3. 脚本会复制到发布仓库、自动提交，并推送到 GitHub。

说明：
- 当前文件夹是内容源。
- GitHub Pages 发布仓库是 PUBLISH_DIR。
- 为了避免覆盖每日实盘更新，本脚本默认保留发布仓库中
  组合实盘追踪/data.json、latest.xlsx、nav_history.json、20*.xlsx。
"""

from __future__ import annotations

import fnmatch
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parent
PUBLISH_DIR = Path(r"C:\Users\Coeur\Desktop\红筹投资\组合构建\new_etf_website\etf-portfolio-dashboard")
REMOTE_URL = "git@github.com:Creve-Coeur/Pring_Model.git"
BRANCH = "main"

SKIP_DIR_NAMES = {".git", ".netlify", "__pycache__"}

# 这些文件由每日实盘脚本维护，静态内容同步时不要覆盖或删除。
LIVE_DATA_PATTERNS = [
    "组合实盘追踪/data.json",
    "组合实盘追踪/latest.xlsx",
    "组合实盘追踪/nav_history.json",
    "组合实盘追踪/20*.xlsx",
]


def to_posix(path: Path) -> str:
    return path.as_posix()


def matches_any(path: Path, patterns: list[str]) -> bool:
    text = to_posix(path)
    return any(fnmatch.fnmatch(text, pattern) for pattern in patterns)


def should_skip_source(rel_path: Path) -> bool:
    if any(part in SKIP_DIR_NAMES for part in rel_path.parts):
        return True
    return matches_any(rel_path, LIVE_DATA_PATTERNS)


def should_preserve_destination(rel_path: Path) -> bool:
    if any(part in {".git", ".netlify"} for part in rel_path.parts):
        return True
    return matches_any(rel_path, LIVE_DATA_PATTERNS)


def assert_safe_paths() -> None:
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"源文件夹不存在：{SOURCE_DIR}")
    if not PUBLISH_DIR.exists():
        raise FileNotFoundError(f"发布仓库文件夹不存在：{PUBLISH_DIR}")
    if not (PUBLISH_DIR / ".git").exists():
        raise RuntimeError(f"发布仓库没有 .git 目录：{PUBLISH_DIR}")
    if SOURCE_DIR == PUBLISH_DIR:
        raise RuntimeError("源文件夹和发布仓库不能是同一个目录。")


def copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def remove_stale_files(src_root: Path, dest_root: Path) -> None:
    """删除发布仓库中对应目录下源文件夹已不存在的旧文件。"""
    if not dest_root.exists():
        return

    wanted_files: set[Path] = set()
    wanted_dirs: set[Path] = {Path(".")}
    for src_path in src_root.rglob("*"):
        rel_to_source_item = src_path.relative_to(src_root)
        rel_to_site = src_path.relative_to(SOURCE_DIR)
        if should_skip_source(rel_to_site):
            continue
        if src_path.is_dir():
            wanted_dirs.add(rel_to_source_item)
        else:
            wanted_files.add(rel_to_source_item)
            wanted_dirs.add(rel_to_source_item.parent)

    for dest_file in sorted(dest_root.rglob("*"), reverse=True):
        rel_to_site = dest_file.relative_to(PUBLISH_DIR)
        rel_to_dest_root = dest_file.relative_to(dest_root)
        if should_preserve_destination(rel_to_site):
            continue
        if dest_file.is_file() and rel_to_dest_root not in wanted_files:
            dest_file.unlink()

    for dest_dir in sorted((p for p in dest_root.rglob("*") if p.is_dir()), reverse=True):
        rel_to_site = dest_dir.relative_to(PUBLISH_DIR)
        rel_to_dest_root = dest_dir.relative_to(dest_root)
        if should_preserve_destination(rel_to_site):
            continue
        if rel_to_dest_root not in wanted_dirs:
            try:
                dest_dir.rmdir()
            except OSError:
                pass


def sync_item(src_item: Path) -> None:
    rel = src_item.relative_to(SOURCE_DIR)
    if should_skip_source(rel):
        return

    dest_item = PUBLISH_DIR / rel

    if src_item.is_file():
        copy_file(src_item, dest_item)
        print(f"复制文件：{rel}")
        return

    if src_item.is_dir():
        dest_item.mkdir(parents=True, exist_ok=True)
        remove_stale_files(src_item, dest_item)
        for src_path in src_item.rglob("*"):
            rel_path = src_path.relative_to(SOURCE_DIR)
            if should_skip_source(rel_path):
                continue
            dest_path = PUBLISH_DIR / rel_path
            if src_path.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
            elif src_path.is_file():
                copy_file(src_path, dest_path)
        print(f"同步目录：{rel}")


def sync_to_publish_repo() -> None:
    for src_item in SOURCE_DIR.iterdir():
        sync_item(src_item)


def run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=PUBLISH_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    print(f"\n$ git {' '.join(args)}")
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    if check and result.returncode != 0:
        raise RuntimeError(f"Git 命令失败：git {' '.join(args)}")
    return result


def has_changes() -> bool:
    result = run_git(["status", "--porcelain"], check=True)
    return bool(result.stdout.strip())


def commit_and_push() -> None:
    run_git(["remote", "set-url", "origin", REMOTE_URL])
    run_git(["add", "."])

    if not has_changes():
        print("\n没有检测到需要同步的变化。")
        return

    message = "Sync website content " + datetime.now().strftime("%Y-%m-%d %H:%M")
    run_git(["commit", "-m", message])
    run_git(["push", "-u", "origin", BRANCH])
    print("\n同步完成，GitHub Pages 稍等片刻会自动刷新。")


def main() -> int:
    try:
        assert_safe_paths()
        print(f"源文件夹：{SOURCE_DIR}")
        print(f"发布仓库：{PUBLISH_DIR}")
        sync_to_publish_repo()
        commit_and_push()
        return 0
    except Exception as exc:
        print(f"\n同步失败：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
