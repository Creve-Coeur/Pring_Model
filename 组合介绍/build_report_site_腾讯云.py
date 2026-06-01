# -*- coding: utf-8 -*-
"""
生成“组合介绍”网页，并部署到腾讯云服务器。

本脚本不改动 build_report_site.py 的生成逻辑，只是在生成完成后把
“组合介绍”目录上传到 /data/www/Asset_Class/组合介绍/。
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
ORIGINAL_SCRIPT = ROOT / "build_report_site.py"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tencent_cloud_deploy import deploy_path_to_tencent


def build_report_site() -> None:
    if not ORIGINAL_SCRIPT.exists():
        raise FileNotFoundError(f"未找到原始生成脚本：{ORIGINAL_SCRIPT}")

    namespace = runpy.run_path(str(ORIGINAL_SCRIPT))
    namespace["main"]()


def deploy_to_tencent_cloud() -> dict[str, object]:
    return deploy_path_to_tencent(
        ROOT,
        remote_subdir="组合介绍",
        prune=True,
    )


def main() -> dict[str, object]:
    build_report_site()
    deploy_result = deploy_to_tencent_cloud()
    globals()["deploy_result"] = deploy_result
    return deploy_result


if __name__ == "__main__":
    main()
