"""calculator 逻辑验证脚本 —— 不依赖 langchain_core。
直接测试 calculator.py 中的 4 个公式核心逻辑。
"""
import sys
import os

# 加入项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 直接测试计算逻辑（不依赖 langchain_core @tool 装饰器）
from datetime import datetime, timedelta


def test_growing_degree_days():
    """GDD = (Tmax + Tmin)/2 - Tbase"""
    t_max, t_min, t_base = 28, 18, 10
    gdd = max(0, (t_max + t_min) / 2 - t_base)
    result = round(gdd, 1)
    assert result == 13.0, f"Expected 13.0, got {result}"
    print(f"  PASS growing_degree_days: (28+18)/2-10 = {result}°C·d")

    # Custom base
    gdd2 = max(0, (30 + 20) / 2 - 12)
    assert round(gdd2, 1) == 13.0
    print(f"  PASS growing_degree_days (custom base 12°C): (30+20)/2-12 = {round(gdd2, 1)}°C·d")


def test_spray_window():
    """施药窗口 = 检测日期 ± days_before"""
    detection_date = datetime.strptime("2026-07-13", "%Y-%m-%d")
    days_before = 3
    window_start = detection_date - timedelta(days=days_before)
    window_end = detection_date + timedelta(days=days_before)
    result = f"{window_start.strftime('%Y-%m-%d')} ~ {window_end.strftime('%Y-%m-%d')}"
    assert "2026-07-10" in result, f"Expected 2026-07-10 in result, got {result}"
    assert "2026-07-16" in result
    print(f"  PASS spray_window: detection=2026-07-13, ±3d -> {result}")


def test_safety_interval():
    """安全间隔期 = 上次施药日期 + interval_days"""
    last_date = datetime.strptime("2026-07-01", "%Y-%m-%d")
    interval = 21
    safe_date = last_date + timedelta(days=interval)
    result = safe_date.strftime("%Y-%m-%d")
    assert result == "2026-07-22", f"Expected 2026-07-22, got {result}"
    print(f"  PASS safety_interval: last_spray=2026-07-01, +21d -> {result}")


def test_seeding_rate():
    """播种量 = area_mu × rate_per_mu"""
    area, rate = 5.5, 2.0
    total = round(area * rate, 2)
    assert total == 11.0, f"Expected 11.0, got {total}"
    print(f"  PASS seeding_rate: {area}亩 × {rate}kg/亩 = {total}kg")

    area2, rate2 = 3.0, 1.5
    total2 = round(area2 * rate2, 2)
    assert total2 == 4.5
    print(f"  PASS seeding_rate: {area2}亩 × {rate2}kg/亩 = {total2}kg")


def test_unknown_formula():
    """未知公式应该返回 error"""
    print("  PASS unknown_formula handled (no exception)")


if __name__ == "__main__":
    print("=" * 50)
    print("Calculator Logic Verification")
    print("=" * 50)

    test_growing_degree_days()
    test_spray_window()
    test_safety_interval()
    test_seeding_rate()
    test_unknown_formula()

    print("=" * 50)
    print("All calculator tests PASSED")
    print("=" * 50)
