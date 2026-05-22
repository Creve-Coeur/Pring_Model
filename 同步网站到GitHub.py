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
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parent
PUBLISH_DIR = SOURCE_DIR
REMOTE_URL = "git@github.com:Creve-Coeur/Pring_Model.git"
BRANCH = "main"

SKIP_DIR_NAMES = {".git", ".git_backup", ".netlify", "__pycache__"}

# 这些文件由每日实盘脚本维护，静态内容同步时不要覆盖或删除。
LIVE_DATA_PATTERNS = [
    "组合实盘追踪/data.json",
    "组合实盘追踪/latest.xlsx",
    "组合实盘追踪/nav_history.json",
    "组合实盘追踪/20*.xlsx",
]

MODULE_HOME_LINKS = {
    Path("组合介绍/index.html"): "../index.html",
    Path("组合的诞生/index.html"): "../index.html",
    Path("组合实盘追踪/index.html"): "../index.html",
}

HOME_LINK_STYLE_MARKER = "site-home-link injected by sync script"
HOME_LINK_STYLE = f"""
  <style>
    /* {HOME_LINK_STYLE_MARKER} */
    .site-home-link {{
      position: fixed;
      left: 18px;
      bottom: 18px;
      z-index: 3000;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 0 18px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.92);
      color: #fff;
      font-size: 14px;
      font-weight: 700;
      text-decoration: none;
      box-shadow: 0 14px 34px rgba(15, 23, 42, 0.24);
      backdrop-filter: blur(10px);
      transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
    }}

    .site-home-link:hover {{
      transform: translateY(-2px);
      background: #0f172a;
      box-shadow: 0 18px 42px rgba(15, 23, 42, 0.3);
    }}

    @media (max-width: 640px) {{
      .site-home-link {{
        left: 12px;
        bottom: 12px;
        min-height: 36px;
        padding: 0 12px;
        font-size: 12px;
      }}
    }}
  </style>"""


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


def is_in_place_repo() -> bool:
    return SOURCE_DIR.resolve() == PUBLISH_DIR.resolve()


def assert_safe_paths() -> None:
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"源文件夹不存在：{SOURCE_DIR}")
    if not PUBLISH_DIR.exists():
        raise FileNotFoundError(f"发布仓库文件夹不存在：{PUBLISH_DIR}")
    if not (PUBLISH_DIR / ".git").exists():
        raise RuntimeError(f"发布仓库没有 .git 目录：{PUBLISH_DIR}")


def ensure_home_link(html_path: Path, href: str) -> None:
    if not html_path.exists():
        return

    text = html_path.read_text(encoding="utf-8")
    updated = text

    if HOME_LINK_STYLE_MARKER not in updated and ".site-home-link" not in updated:
        if "</head>" in updated:
            updated = updated.replace("</head>", f"{HOME_LINK_STYLE}\n</head>", 1)
        else:
            print(f"未找到 </head>，跳过返回按钮样式：{html_path}")

    has_link = 'class="site-home-link"' in updated or "class='site-home-link'" in updated
    if not has_link:
        link_html = f'<a class="site-home-link" href="{href}">返回首页</a>'
        body_match = re.search(r"<body\b[^>]*>", updated, flags=re.IGNORECASE)
        if body_match:
            insert_at = body_match.end()
            updated = updated[:insert_at] + f"\n  {link_html}" + updated[insert_at:]
        else:
            print(f"未找到 <body>，跳过返回首页按钮：{html_path}")

    if updated != text:
        html_path.write_text(updated, encoding="utf-8")
        rel = html_path.relative_to(html_path.parents[1]) if len(html_path.parents) > 1 else html_path
        print(f"已补返回首页按钮：{rel}")


def ensure_module_home_links(root: Path) -> None:
    for rel_path, href in MODULE_HOME_LINKS.items():
        ensure_home_link(root / rel_path, href)


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
    if is_in_place_repo():
        print("\n当前文件夹已是发布仓库，跳过文件复制步骤。")
        return

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

    if has_changes():
        message = "Sync website content " + datetime.now().strftime("%Y-%m-%d %H:%M")
        run_git(["commit", "-m", message])
    else:
        print("\n没有检测到需要提交的文件变化，仍会尝试推送到 GitHub。")

    run_git(["push", "-u", "origin", BRANCH])
    print("\n推送完成，GitHub Pages 稍等片刻会自动刷新。")


def main() -> int:
    try:
        assert_safe_paths()
        print(f"源文件夹：{SOURCE_DIR}")
        print(f"发布仓库：{PUBLISH_DIR}")
        ensure_module_home_links(SOURCE_DIR)
        sync_to_publish_repo()
        if not is_in_place_repo():
            ensure_module_home_links(PUBLISH_DIR)
        commit_and_push()
        return 0
    except Exception as exc:
        print(f"\n同步失败：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
