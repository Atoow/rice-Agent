"""Agent 状态图集成测试 —— 验证图结构、路由逻辑。

当前图为 ReAct 模式（3 节点: intent_route / react_agent / execute_tools）。
"""
import ast
import textwrap
import pytest
from backend.agent.state import initial_state, AgentState


class TestAgentGraph:

    def test_graph_builds_successfully(self):
        """通过 AST 验证图构建逻辑 —— 确认 ReAct 模式 3 个节点和入口点。"""
        import os
        graph_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "agent", "graph.py"
        )
        with open(graph_path, encoding="utf-8") as f:
            tree = ast.parse(f.read())

        # 检查 add_node 调用
        add_node_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "add_node":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        add_node_calls.append(node.args[0].value)

        # 当前 ReAct 模式有 3 个节点
        assert len(add_node_calls) == 3, (
            f"Expected 3 add_node calls, got {len(add_node_calls)}: {add_node_calls}"
        )

        expected_nodes = {"intent_route", "react_agent", "execute_tools"}
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
                     "final_diagnosis", "sources", "verification_result", "node_events",
                     "pending_action", "pending_observation", "react_loops"]
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
    """路由函数测试 —— 从 graph.py AST 提取路由函数并执行。"""

    @classmethod
    def setup_class(cls):
        """从 graph.py 源码中提取路由函数。"""
        import os
        graph_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "agent", "graph.py"
        )
        with open(graph_path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)

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
        assert route(state) == "react_agent"

    def test_route_after_intent_knowledge(self):
        route = self.route_funcs["route_after_intent"]
        state = initial_state()
        state["intent"] = "knowledge"
        assert route(state) == "react_agent"

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

    def test_route_after_react_with_action(self):
        """有 pending_action 时应该走 execute_tools。"""
        route = self.route_funcs["route_after_react"]
        state = initial_state()
        state["pending_action"] = {"tool": "vector_search", "tool_input": "稻瘟病"}
        assert route(state) == "execute_tools"

    def test_route_after_react_no_action(self):
        """无 pending_action 时应该结束。"""
        route = self.route_funcs["route_after_react"]
        state = initial_state()
        state["pending_action"] = None
        assert route(state) == "end"

    def test_route_after_react_max_loops(self):
        """超过最大循环次数走 force_end。"""
        route = self.route_funcs["route_after_react"]
        state = initial_state()
        state["react_loops"] = 8
        state["pending_action"] = {"tool": "vector_search", "tool_input": "稻瘟病"}
        assert route(state) == "force_end"

    def test_route_after_tools(self):
        """工具执行后回到 react_agent。"""
        route = self.route_funcs["route_after_tools"]
        state = initial_state()
        assert route(state) == "react_agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
