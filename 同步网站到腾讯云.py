# -*- coding: utf-8 -*-
"""
一键同步当前网站文件夹到腾讯云服务器。

用途：
1. 你在当前文件夹里更新了首页、组合介绍、组合的诞生等网页内容；
2. 运行本脚本；
3. 脚本会刷新首页模块更新时间，并上传到腾讯云站点目录。

说明：
- 当前文件夹是内容源。
- 腾讯云发布目录是 /data/www/Asset_Class/。
- 为了避免覆盖每日实盘更新，本脚本默认保留服务器中的
  组合实盘追踪/data.json、latest.xlsx、nav_history.json、20*.xlsx。
"""

from __future__ import annotations

import runpy
from pathlib import Path

from tencent_cloud_deploy import deploy_path_to_tencent


SOURCE_DIR = Path(__file__).resolve().parent
GITHUB_SYNC_SCRIPT = SOURCE_DIR / "同步网站到GitHub.py"


def load_sync_namespace() -> dict[str, object]:
    if not GITHUB_SYNC_SCRIPT.exists():
        raise FileNotFoundError(f"未找到原始同步脚本：{GITHUB_SYNC_SCRIPT}")
    return runpy.run_path(str(GITHUB_SYNC_SCRIPT))


def main() -> int:
    sync = load_sync_namespace()

    try:
        source_dir = sync["SOURCE_DIR"]
        live_data_patterns = sync["LIVE_DATA_PATTERNS"]

        sync["assert_safe_paths"]()
        print(f"源文件夹：{source_dir}")
        print("腾讯云发布目录：/data/www/Asset_Class/")

        sync["ensure_module_home_links"](source_dir)
        sync["update_homepage_index"](source_dir)
        sync["sync_to_publish_repo"]()
        if not sync["is_in_place_repo"]():
            sync["ensure_module_home_links"](sync["PUBLISH_DIR"])

        deploy_result = deploy_path_to_tencent(
            source_dir,
            remote_subdir="",
            exclude_patterns=live_data_patterns,
            preserve_patterns=live_data_patterns,
            prune=True,
        )
        globals()["deploy_result"] = deploy_result
        return 0
    except Exception as exc:
        print(f"\n同步到腾讯云失败：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
