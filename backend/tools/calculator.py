"""农业计算工具 —— 积温、施药窗口、安全间隔期等数值计算。"""
from langchain_core.tools import tool


@tool
def calculator(formula: str, params: dict) -> dict:
    """执行农业相关数值计算。

    支持公式：
    - growing_degree_days: 积温计算，需要 t_max(float), t_min(float), t_base(float=10)
    - spray_window: 施药窗口，需要 detection_date(str YYYY-MM-DD), days_before(int)
    - safety_interval: 安全间隔期，需要 last_spray_date(str YYYY-MM-DD), interval_days(int)
    - seeding_rate: 播种量计算，需要 area_mu(float), rate_per_mu(float)

    Args:
        formula: 公式名称
        params: 公式参数

    Returns:
        {result, formula_used, unit, explanation}
    """
    from datetime import datetime, timedelta

    if formula == "growing_degree_days":
        t_max = params["t_max"]
        t_min = params["t_min"]
        t_base = params.get("t_base", 10.0)
        gdd = max(0, (t_max + t_min) / 2 - t_base)
        return {
            "result": round(gdd, 1),
            "formula_used": f"GDD = (Tmax + Tmin)/2 - Tbase ({t_base}°C)",
            "unit": "°C·d",
            "explanation": f"当日有效积温为 {gdd:.1f}°C·d，可用于判断水稻发育进度"
        }

    elif formula == "spray_window":
        detection_date = datetime.strptime(params["detection_date"], "%Y-%m-%d")
        days_before = params["days_before"]
        window_start = detection_date - timedelta(days=days_before)
        window_end = detection_date + timedelta(days=days_before)
        return {
            "result": f"{window_start.strftime('%Y-%m-%d')} ~ {window_end.strftime('%Y-%m-%d')}",
            "formula_used": f"施药窗口 = 检测日期 ± {days_before} 天",
            "unit": "日期范围",
            "explanation": f"建议在 {window_start.strftime('%m月%d日')} 至 {window_end.strftime('%m月%d日')} 期间施药"
        }

    elif formula == "safety_interval":
        last_date = datetime.strptime(params["last_spray_date"], "%Y-%m-%d")
        interval = params["interval_days"]
        safe_date = last_date + timedelta(days=interval)
        return {
            "result": safe_date.strftime("%Y-%m-%d"),
            "formula_used": f"安全间隔期 = 上次施药日期 + {interval} 天",
            "unit": "日期",
            "explanation": f"安全间隔期 {interval} 天，{safe_date.strftime('%m月%d日')} 之后方可收获"
        }

    elif formula == "seeding_rate":
        area = params["area_mu"]
        rate = params["rate_per_mu"]
        total = area * rate
        return {
            "result": round(total, 2),
            "formula_used": f"播种量 = {area} 亩 × {rate} kg/亩",
            "unit": "kg",
            "explanation": f"{area} 亩地共需 {total:.1f} kg 种子"
        }

    return {"result": None, "error": f"未知公式: {formula}", "supported": [
        "growing_degree_days", "spray_window", "safety_interval", "seeding_rate"
    ]}
