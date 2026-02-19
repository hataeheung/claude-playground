"""agent.py 테스트 - 파이프라인 상태 및 유틸리티"""

import json

import pytest

from acb.agent import (
    PHASE_DISPLAY,
    PIPELINE_PHASES,
    PhaseResult,
    PipelineState,
)


class TestPipelineState:
    def test_initial_state(self):
        state = PipelineState(requirement="테스트 기능 구현")
        assert state.requirement == "테스트 기능 구현"
        assert state.current_phase == "analyze"
        assert not state.is_complete
        assert state.error == ""
        assert state.pr_number is None

    def test_phase_results(self):
        state = PipelineState(requirement="test")
        result = PhaseResult(phase="analyze", success=True, output="분석 완료")
        state.results["analyze"] = result

        assert "analyze" in state.results
        assert state.results["analyze"].success


class TestPhaseResult:
    def test_success_result(self):
        result = PhaseResult(phase="implement", success=True, output="구현 완료")
        assert result.success
        assert result.error == ""

    def test_failure_result(self):
        result = PhaseResult(
            phase="verify", success=False, output="",
            error="테스트 실패: 3개 에러"
        )
        assert not result.success
        assert "테스트 실패" in result.error

    def test_with_data(self):
        result = PhaseResult(
            phase="deliver", success=True, output="",
            data={"commit_message": "feat: add feature", "pr_title": "Add feature"}
        )
        assert result.data["commit_message"] == "feat: add feature"


class TestPipelinePhases:
    def test_all_phases_defined(self):
        expected = [
            "analyze", "explore", "plan", "implement",
            "verify", "deliver", "review", "deploy",
        ]
        assert PIPELINE_PHASES == expected

    def test_all_phases_have_display_info(self):
        for phase in PIPELINE_PHASES:
            assert phase in PHASE_DISPLAY
            name, color, desc = PHASE_DISPLAY[phase]
            assert name  # 이름이 비어있지 않아야 함
            assert color
            assert desc


class TestJsonExtraction:
    """DevAgent._extract_json 로직 테스트 (독립 함수로 테스트)"""

    def _extract_json(self, text: str) -> dict:
        """agent.py의 _extract_json 로직 복제"""
        import re
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])

        raise ValueError("JSON을 찾을 수 없습니다.")

    def test_extract_from_code_block(self):
        text = 'Here is the result:\n```json\n{"key": "value"}\n```'
        result = self._extract_json(text)
        assert result == {"key": "value"}

    def test_extract_from_raw_json(self):
        text = '분석 결과: {"requirements": ["auth"], "constraints": []}'
        result = self._extract_json(text)
        assert result["requirements"] == ["auth"]

    def test_extract_nested_json(self):
        text = '```json\n{"tasks": [{"id": 1, "title": "task1"}]}\n```'
        result = self._extract_json(text)
        assert len(result["tasks"]) == 1

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            self._extract_json("no json here")
