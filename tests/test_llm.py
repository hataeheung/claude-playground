"""llm.py 테스트 - API 호출 없이 구조만 테스트"""


from acb.llm import (
    AGENT_TOOLS,
    LLMResponse,
    ToolCall,
    build_system_prompt,
)


class TestLLMResponse:
    def test_empty_response(self):
        resp = LLMResponse()
        assert resp.text == ""
        assert not resp.has_tool_calls

    def test_with_tool_calls(self):
        resp = LLMResponse(
            text="Let me read the file.",
            tool_calls=[
                ToolCall(tool_id="tc1", name="read_file", arguments={"path": "main.py"})
            ],
        )
        assert resp.has_tool_calls
        assert resp.tool_calls[0].name == "read_file"

    def test_stop_reason(self):
        resp = LLMResponse(stop_reason="end_turn")
        assert resp.stop_reason == "end_turn"


class TestAgentTools:
    def test_tools_are_valid(self):
        """도구 정의가 Anthropic API 스키마에 맞는지 확인"""
        assert len(AGENT_TOOLS) > 0
        for tool in AGENT_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            schema = tool["input_schema"]
            assert schema["type"] == "object"
            assert "properties" in schema

    def test_required_tools_exist(self):
        tool_names = {t["name"] for t in AGENT_TOOLS}
        expected = {
            "read_file", "write_file", "edit_file",
            "run_command", "search_files", "search_content",
            "list_directory",
        }
        assert expected.issubset(tool_names)


class TestBuildSystemPrompt:
    def test_analyze_prompt(self):
        prompt = build_system_prompt("analyze")
        assert "ANALYZE" in prompt
        assert "요구사항" in prompt

    def test_implement_prompt(self):
        prompt = build_system_prompt("implement")
        assert "IMPLEMENT" in prompt
        assert "YAGNI" in prompt

    def test_with_context(self):
        prompt = build_system_prompt("plan", project_context="Python FastAPI 프로젝트")
        assert "Python FastAPI" in prompt

    def test_all_phases_have_prompts(self):
        phases = ["analyze", "explore", "plan", "implement", "verify", "deliver", "review"]
        for phase in phases:
            prompt = build_system_prompt(phase)
            assert len(prompt) > 50  # 의미있는 길이
