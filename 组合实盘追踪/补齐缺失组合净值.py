# -*- coding: utf-8 -*-
"""
检查并补齐组合净值缺失日期。

逻辑：
1. 读取 nav_history.json 中已有的组合净值历史。
2. 读取 data.json 中的对比指数日期。
3. 若基日后的某个指数交易日有数据，但组合净值没有数据，则提示是否模拟补齐。
4. 选择模拟后，输入该日盈亏金额，脚本用“上一条总资产 + 当日盈亏”估算该日总资产和净值。
5. 同步更新 nav_history.json 和 data.json 中网页直接读取的 navSeries。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


NAV_HISTORY_NAME = "nav_history.json"
DATA_JSON_NAME = "data.json"
INITIAL_PORTFOLIO_ASSETS = 30000.0
DEFAULT_BENCHMARK_NAME = "沪深300"


def module_dir() -> Path:
    if "__file__" in globals():
        return Path(__file__).resolve().parent
    return Path.cwd().resolve()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"找不到文件: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        f.write("\n")


def parse_date(text: str):
    return datetime.strptime(str(text)[:10], "%Y-%m-%d").date()


def safe_float(value, default=0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def yes_answer(text: str) -> bool:
    return text.strip().lower() in {"y", "yes", "是", "需要", "模拟", "1"}


def get_sorted_history_series(history: dict) -> list[dict]:
    series = [item for item in history.get("series", []) if item.get("date")]
    return sorted(series, key=lambda item: item["date"])


def get_benchmark_series(data: dict) -> tuple[str, list[dict]]:
    benchmark_map = data.get("benchmarkSeriesMap") or {}
    meta = data.get("meta") or {}
    benchmark_name = meta.get("benchmarkName") or DEFAULT_BENCHMARK_NAME

    if benchmark_name in benchmark_map:
        return benchmark_name, benchmark_map[benchmark_name]

    if data.get("benchmarkSeries"):
        return benchmark_name, data["benchmarkSeries"]

    if benchmark_map:
        first_name = next(iter(benchmark_map))
        return first_name, benchmark_map[first_name]

    return benchmark_name, []


def find_missing_dates(history: dict, data: dict) -> tuple[str, list[str]]:
    series = get_sorted_history_series(history)
    if not series:
        return "", []

    portfolio_dates = {item["date"] for item in series}
    base_date = parse_date(history.get("baseDate") or series[0]["date"])
    last_portfolio_date = parse_date(series[-1]["date"])

    benchmark_name, benchmark_series = get_benchmark_series(data)
    benchmark_dates = {
        item.get("date")
        for item in benchmark_series
        if item.get("date")
    }

    missing_dates = []
    for date_text in sorted(benchmark_dates):
        current_date = parse_date(date_text)
        if current_date <= base_date:
            continue
        if current_date > last_portfolio_date:
            continue
        if date_text not in portfolio_dates:
            missing_dates.append(date_text)

    return benchmark_name, missing_dates


def previous_record(series: list[dict], date_text: str) -> dict | None:
    previous = None
    for item in series:
        if item["date"] >= date_text:
            break
        previous = item
    return previous


def next_record(series: list[dict], date_text: str) -> dict | None:
    for item in series:
        if item["date"] > date_text:
            return item
    return None


def read_pnl(date_text: str) -> float:
    while True:
        raw = input(f"请输入 {date_text} 当天盈亏金额，例如 -123.45 或 80：").strip()
        try:
            return float(raw.replace(",", ""))
        except ValueError:
            print("金额格式无法识别，请重新输入。")


def build_simulated_record(date_text: str, pnl: float, previous: dict, base_assets: float) -> dict:
    previous_total_assets = safe_float(previous.get("totalAssets"))
    previous_position_ratio = safe_float(previous.get("positionRatio"), default=0.0)
    total_assets = round(previous_total_assets + pnl, 2)
    holding_market_value = (
        round(total_assets * previous_position_ratio, 2)
        if previous_position_ratio > 0
        else total_assets
    )

    return {
        "date": date_text,
        "totalAssets": total_assets,
        "holdingMarketValue": holding_market_value,
        "dailyPnL": round(pnl, 2),
        "positionRatio": round(previous_position_ratio, 6),
        "nav": round(total_assets / base_assets, 6) if base_assets else 1.0,
        "isSimulated": True,
        "note": "由补齐缺失组合净值脚本根据上一条总资产和手工输入当日盈亏模拟",
    }


def recalculate_history(history: dict) -> dict:
    series = get_sorted_history_series(history)
    if not series:
        return history

    base_assets = INITIAL_PORTFOLIO_ASSETS

    history["baseDate"] = history.get("baseDate") or series[0]["date"]
    history["baseAssets"] = round(base_assets, 2)
    history.pop("baseSnapshotAssets", None)

    for index, item in enumerate(series):
        total_assets = safe_float(item.get("totalAssets"))
        item["totalAssets"] = round(total_assets, 2)
        item["nav"] = 1.0 if index == 0 else round(total_assets / base_assets, 6) if base_assets else 1.0

    history["series"] = series
    return history


def sync_data_json_nav_series(data: dict, history: dict) -> dict:
    series = get_sorted_history_series(history)
    data["navSeries"] = [
        {
            "date": item["date"],
            "nav": item["nav"],
            **({"isSimulated": True} if item.get("isSimulated") else {}),
        }
        for item in series
    ]

    meta = data.setdefault("meta", {})
    meta["navBaseDate"] = history.get("baseDate")
    meta["navBaseAssets"] = history.get("baseAssets")
    meta.pop("navBaseSnapshotAssets", None)
    meta["navHistoryPatchedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return data


def main() -> None:
    target_dir = module_dir()
    nav_history_path = target_dir / NAV_HISTORY_NAME
    data_json_path = target_dir / DATA_JSON_NAME

    history = load_json(nav_history_path)
    data = load_json(data_json_path)

    benchmark_name, missing_dates = find_missing_dates(history, data)
    if not missing_dates:
        print(f"未发现缺失日期。检查基准：{benchmark_name}")
        return

    print(f"检查基准：{benchmark_name}")
    print("发现组合净值缺失日期：")
    for date_text in missing_dates:
        print(f"  - {date_text}")

    series_by_date = {item["date"]: item for item in get_sorted_history_series(history)}
    base_assets = INITIAL_PORTFOLIO_ASSETS
    added_records = []

    for date_text in missing_dates:
        series = sorted(series_by_date.values(), key=lambda item: item["date"])
        previous = previous_record(series, date_text)
        following = next_record(series, date_text)

        if previous is None:
            print(f"\n{date_text} 缺少前一条组合记录，无法模拟，已跳过。")
            continue

        print(f"\n缺失日期: {date_text}")
        print(f"上一条记录: {previous['date']} 总资产={previous.get('totalAssets')} 净值={previous.get('nav')}")
        if following:
            print(f"后一条记录: {following['date']} 总资产={following.get('totalAssets')} 净值={following.get('nav')}")

        if not yes_answer(input("是否需要模拟补齐这一天？输入 y/是 确认，其他为跳过：")):
            print(f"已跳过 {date_text}。")
            continue

        pnl = read_pnl(date_text)
        simulated = build_simulated_record(date_text, pnl, previous, base_assets)
        series_by_date[date_text] = simulated
        added_records.append(simulated)
        print(f"已模拟 {date_text}: 总资产={simulated['totalAssets']} 净值={simulated['nav']}")

    if not added_records:
        print("\n没有新增模拟净值记录，文件未改动。")
        return

    history["series"] = sorted(series_by_date.values(), key=lambda item: item["date"])
    history = recalculate_history(history)
    data = sync_data_json_nav_series(data, history)

    save_json(nav_history_path, history)
    save_json(data_json_path, data)

    print("\n补齐完成，已更新：")
    print(f"  - {nav_history_path}")
    print(f"  - {data_json_path}")
    print("新增模拟记录：")
    for item in added_records:
        print(f"  - {item['date']} 当日盈亏={item['dailyPnL']} 净值={item['nav']}")


if __name__ == "__main__":
    main()
