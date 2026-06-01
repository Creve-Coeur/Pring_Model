# -*- coding: utf-8 -*-
"""
ETF 实盘持仓看板更新脚本（腾讯云部署版）

本脚本复用 获取每日持仓情况_ver4.0.py 的下载、搬运、数据转换逻辑，
只把最后的 GitHub 推送替换为上传到腾讯云服务器：
/data/www/Asset_Class/组合实盘追踪/。
"""

from __future__ import annotations

import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
ORIGINAL_SCRIPT = CURRENT_DIR / "获取每日持仓情况_ver4.0.py"
ORIGINAL_EXECUTION_MARKER = "#%% 9. 分步骤执行区"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tencent_cloud_deploy import deploy_path_to_tencent


def load_original_definitions() -> dict[str, object]:
    if not ORIGINAL_SCRIPT.exists():
        raise FileNotFoundError(f"未找到原始实盘脚本：{ORIGINAL_SCRIPT}")

    source = ORIGINAL_SCRIPT.read_text(encoding="utf-8")
    if ORIGINAL_EXECUTION_MARKER not in source:
        raise RuntimeError(f"未找到原始脚本的分步骤执行区标记：{ORIGINAL_EXECUTION_MARKER}")

    definitions_source = source.split(ORIGINAL_EXECUTION_MARKER, 1)[0]
    namespace = {
        "__file__": str(ORIGINAL_SCRIPT),
        "__name__": "__tencent_live_daily__",
    }
    exec(compile(definitions_source, str(ORIGINAL_SCRIPT), "exec"), namespace)
    return namespace


_original_namespace = load_original_definitions()
globals().update({key: value for key, value in _original_namespace.items() if not key.startswith("__")})


#%% 7. 腾讯云部署
def deploy_to_tencent_cloud() -> dict[str, object]:
    """把“组合实盘追踪”目录上传到腾讯云站点对应模块目录。"""
    return deploy_path_to_tencent(
        TARGET_DIR,
        remote_subdir=LIVE_MODULE_DIR_NAME,
        prune=True,
    )


def deploy_to_cloud() -> dict[str, object]:
    """保持原脚本调用名不变；在本版本中 cloud 指腾讯云服务器。"""
    return deploy_to_tencent_cloud()


def ensure_ssh_remote():
    """腾讯云部署版不使用 Git remote。"""
    print("腾讯云部署版不需要切换 Git remote。")
    return None


def commit_local_changes():
    """腾讯云部署版不需要本地 Git 提交。"""
    print("腾讯云部署版不需要本地 Git 提交。")
    return {"commit_ok": True}


def push_to_cloud(ensure_remote=True) -> dict[str, object]:
    """兼容原脚本的手动重跑习惯；腾讯云部署不需要 Git remote。"""
    return deploy_to_tencent_cloud()


#%% 8. 可选：完整流程函数
def run_full_workflow(max_wait_time=20, deploy=True):
    """完整流程函数。直接运行脚本时会自动调用，也可以手动分步调用。"""
    os.makedirs(PUBLISH_ROOT_DIR, exist_ok=True)
    os.makedirs(TARGET_DIR, exist_ok=True)
    start_time = open_broker_website()

    print(f"正在监控下载目录: {DOWNLOAD_DIR}")
    found_file = wait_for_new_export(start_time, max_wait_time=max_wait_time)
    if not found_file:
        print("任务超时，未检测到新下载的账本文件。")
        return None

    excel_path = move_export_to_project(found_file)
    dashboard_data = None
    deploy_result = None
    if excel_path.lower().endswith(".xlsx"):
        dashboard_data = refresh_data_json_from_excel(excel_path)
    if deploy:
        deploy_result = deploy_to_cloud()

    return {
        "excel_path": excel_path,
        "dashboard_data": dashboard_data,
        "deploy_result": deploy_result,
    }


#%% 9. 分步骤执行区：运行到哪个 cell，就直接执行哪个步骤
# 说明：
# - 不需要取消注释，也不需要设置触发开关。
# - 在 Spyder 里单独运行某个 cell，就会执行该 cell 的功能。
# - 直接运行整份脚本，会按下面顺序完整执行。
# - 下面产生的 benchmark_map、start_time、found_file、excel_path、dashboard_data、deploy_result 都会出现在变量浏览器。

#%% 9.1 获取并检查全部指数
benchmark_map, benchmark_errors = check_benchmark_data()


#%% 9.2 打开券商网站并记录开始时间
start_time = open_broker_website()


#%% 9.3 等待并捕获新下载文件
WAIT_MAX_SECONDS = 20
found_file = wait_for_new_export(start_time, max_wait_time=WAIT_MAX_SECONDS)


#%% 9.4 移动下载文件并刷新 latest.xlsx
if found_file is None:
    raise RuntimeError("未检测到新下载的账本文件，请检查券商网站是否已成功导出。")
excel_path = move_export_to_project(found_file)


#%% 9.5 根据 latest.xlsx 刷新网页数据
dashboard_data = refresh_data_json_from_excel(excel_path, benchmark_map=benchmark_map, benchmark_errors=benchmark_errors)


#%% 9.6 执行腾讯云部署
deploy_result = deploy_to_cloud()


#%% 9.7 汇总本次执行结果
workflow_result = {
    "benchmark_map": benchmark_map,
    "benchmark_errors": benchmark_errors,
    "start_time": start_time,
    "found_file": found_file,
    "excel_path": excel_path,
    "dashboard_data": dashboard_data,
    "deploy_result": deploy_result,
}
