"""工具单元测试 —— 不依赖 Neo4j 和 Ollama 也能跑。"""
import pytest
from backend.tools.calculator import calculator


class TestCalculator:

    def test_growing_degree_days(self):
        result = calculator.invoke({
            "formula": "growing_degree_days",
            "params": {"t_max": 28, "t_min": 18}
        })
        assert result["unit"] == "°C·d"
        assert result["result"] == 13.0  # (28+18)/2 - 10

    def test_growing_degree_days_custom_base(self):
        result = calculator.invoke({
            "formula": "growing_degree_days",
            "params": {"t_max": 30, "t_min": 20, "t_base": 12}
        })
        assert result["result"] == 13.0

    def test_spray_window(self):
        result = calculator.invoke({
            "formula": "spray_window",
            "params": {"detection_date": "2026-07-13", "days_before": 3}
        })
        assert "2026-07-10" in result["result"]
        assert "2026-07-16" in result["result"]

    def test_safety_interval(self):
        result = calculator.invoke({
            "formula": "safety_interval",
            "params": {"last_spray_date": "2026-07-01", "interval_days": 21}
        })
        assert result["result"] == "2026-07-22"

    def test_seeding_rate(self):
        result = calculator.invoke({
            "formula": "seeding_rate",
            "params": {"area_mu": 5.5, "rate_per_mu": 2.0}
        })
        assert result["result"] == 11.0
        assert result["unit"] == "kg"

    def test_unknown_formula(self):
        result = calculator.invoke({
            "formula": "nonexistent",
            "params": {}
        })
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
