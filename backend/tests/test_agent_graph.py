"""Agent 状态图集成测试 —— 验证图结构、路由逻辑。

策略：
- graph_builds_successfully：使用 AST 静态分析验证图结构（langgraph 不可用时）
- 初始状态测试：直接导入 state.py（无 langgraph 依赖）
- 路由函数测试：通过 AST 提取函数 + 提供缺失的类型定义（AgentState）来 exec
"""
import ast
import textwrap
import pytest
from backend.agent.state import initial_state, AgentState


class TestAgentGraph:

    def test_graph_builds_successfully(self):
        """通过 AST 验证图构建逻辑 —— 确认 7 个节点和入口点。"""
        with open("backend/agent/graph.py") as f:
            tree = ast.parse(f.read())

        # 检查 add_node 调用
        add_node_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "add_node":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        add_node_calls.append(node.args[0].value)

        # 验证至少有 7 个节点
        assert len(add_node_calls) >= 7, (
            f"Expected >=7 add_node calls, got {len(add_node_calls)}"
        )

        # 验证节点名称
        expected_nodes = {
            "intent_route", "collect_info", "check_confidence",
            "clarify", "verify_claim", "generate_plan", "knowledge_answer"
        }
        for expected in expected_nodes:
            assert expected in add_node_calls, (
                f"Missing node '{expected}' in graph.add_node calls"
            )

        # 验证 set_entry_point
        found_entry = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "set_entry_point":
                    found_entry = True
                    if node.args and isinstance(node.args[0], ast.Constant):
                        assert node.args[0].value == "intent_route"
                    break
        assert found_entry, "Missing set_entry_point('intent_route')"

    def test_initial_state_has_all_fields(self):
        """初始状态包含所有必需字段。"""
        state = initial_state()
        required = ["messages", "intent", "symptoms", "candidate_diseases",
                     "confidence", "missing_info", "clarify_count",
                     "final_diagnosis", "sources", "verification_result", "node_events"]
        for key in required:
            assert key in state, f"Missing field: {key}"

    def test_initial_state_messages_empty(self):
        state = initial_state()
        assert state["messages"] == []

    def test_initial_state_symptoms_empty(self):
        state = initial_state()
        assert state["symptoms"] == []

    def test_initial_state_clarify_count_zero(self):
        state = initial_state()
        assert state["clarify_count"] == 0

    def test_initial_state_confidence_zero(self):
        state = initial_state()
        assert state["confidence"] == 0.0

    def test_initial_state_final_diagnosis_none(self):
        state = initial_state()
        assert state["final_diagnosis"] is None

    def test_initial_state_verification_result_none(self):
        state = initial_state()
        assert state["verification_result"] is None


class TestGraphRouting:
    """路由函数测试 —— AST 提取 + exec 执行路由函数。"""

    @classmethod
    def setup_class(cls):
        """从 graph.py 源码中提取路由函数，提供 AgentState 定义。"""
        with open("backend/agent/graph.py") as f:
            source = f.read()
        tree = ast.parse(source)

        # 提取所有以 route_ 开头的函数源码
        cls.route_funcs = {}
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("route_"):
                func_source = ast.get_source_segment(source, node)
                func_source = textwrap.dedent(func_source)
                ns = {"AgentState": AgentState}
                exec(func_source, ns)
                cls.route_funcs[node.name] = ns[node.name]

    def test_route_after_intent_diagnose(self):
        route = self.route_funcs["route_after_intent"]
        state = initial_state()
        state["intent"] = "diagnose"
        assert route(state) == "collect_info"

    def test_route_after_intent_knowledge(self):
        route = self.route_funcs["route_after_intent"]
        state = initial_state()
        state["intent"] = "knowledge"
        assert route(state) == "knowledge_answer"

    def test_route_after_intent_chitchat(self):
        route = self.route_funcs["route_after_intent"]
        state = initial_state()
        state["intent"] = "chitchat"
        assert route(state) == "chitchat_end"

    def test_route_after_intent_default(self):
        """意图不明时默认走 chitchat。"""
        route = self.route_funcs["route_after_intent"]
        state = initial_state()
        state["intent"] = "unknown"
        assert route(state) == "chitchat_end"

    def test_route_after_confidence_high(self):
        route = self.route_funcs["route_after_confidence"]
        state = initial_state()
        state["confidence"] = 0.85
        assert route(state) == "verify_claim"

    def test_route_after_confidence_low_with_rounds_left(self):
        route = self.route_funcs["route_after_confidence"]
        state = initial_state()
        state["confidence"] = 0.4
        state["clarify_count"] = 1
        assert route(state) == "clarify"

    def test_route_after_confidence_low_max_rounds(self):
        route = self.route_funcs["route_after_confidence"]
        state = initial_state()
        state["confidence"] = 0.4
        state["clarify_count"] = 3
        assert route(state) == "verify_claim"

    def test_route_after_confidence_high_threshold(self):
        """边界值 0.7 应走 verify_claim。"""
        route = self.route_funcs["route_after_confidence"]
        state = initial_state()
        state["confidence"] = 0.7
        assert route(state) == "verify_claim"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
