"""Claude API 클라이언트 - 에이전트의 두뇌"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import anthropic

from acb.config import AgentConfig, get_api_key


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class ToolCall:
    """LLM이 요청한 도구 호출"""
    tool_id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """LLM 응답 결과"""
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = ""

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


# 에이전트가 사용할 도구 정의 (Anthropic tool_use 형식)
AGENT_TOOLS = [
    {
        "name": "read_file",
        "description": "파일 내용을 읽습니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "읽을 파일 경로"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "파일에 내용을 씁니다. 기존 파일은 덮어씁니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "쓸 파일 경로"},
                "content": {"type": "string", "description": "파일에 쓸 내용"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "파일의 특정 부분을 교체합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "수정할 파일 경로"},
                "old_text": {"type": "string", "description": "교체할 기존 텍스트"},
                "new_text": {"type": "string", "description": "새 텍스트"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "run_command",
        "description": "셸 명령어를 실행합니다. 테스트, 린트, 빌드 등에 사용합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "실행할 셸 명령어"},
                "timeout": {
                    "type": "integer",
                    "description": "타임아웃 (초). 기본 60초",
                    "default": 60,
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "search_files",
        "description": "프로젝트에서 파일명 패턴으로 파일을 검색합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "glob 패턴 (예: '**/*.py', 'src/**/*.ts')",
                },
                "path": {
                    "type": "string",
                    "description": "검색 시작 디렉토리. 기본값은 프로젝트 루트",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "search_content",
        "description": "파일 내용에서 텍스트/정규식 패턴을 검색합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "검색할 텍스트 또는 정규식"},
                "path": {"type": "string", "description": "검색 디렉토리"},
                "file_pattern": {
                    "type": "string",
                    "description": "파일 필터 glob (예: '*.py')",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "list_directory",
        "description": "디렉토리 내용을 나열합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "디렉토리 경로"},
                "recursive": {
                    "type": "boolean",
                    "description": "재귀적으로 탐색할지 여부",
                    "default": False,
                },
            },
            "required": ["path"],
        },
    },
]


class LLMClient:
    """Claude API를 통해 에이전트의 추론을 수행하는 클라이언트"""

    def __init__(self, config: AgentConfig):
        api_key = get_api_key(config)
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY 환경변수를 설정하거나 "
                "config에 anthropic_api_key를 지정해주세요."
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = config.model
        self.max_tokens = config.max_tokens

    def chat(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Claude API 호출. tool_use를 지원합니다."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        result = LLMResponse(stop_reason=response.stop_reason)

        for block in response.content:
            if block.type == "text":
                result.text += block.text
            elif block.type == "tool_use":
                result.tool_calls.append(
                    ToolCall(
                        tool_id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        return result

    def simple_chat(self, prompt: str, system: str = "") -> str:
        """도구 없이 간단한 텍스트 응답만 받기."""
        messages = [{"role": "user", "content": prompt}]
        response = self.chat(messages, system=system)
        return response.text


def build_system_prompt(phase: str, project_context: str = "") -> str:
    """각 단계별 시스템 프롬프트 생성"""

    base = (
        "당신은 소프트웨어 개발을 자동화하는 AI 에이전트입니다. "
        "체계적인 6단계 프로세스(ANALYZE→EXPLORE→PLAN→IMPLEMENT→VERIFY→DELIVER)를 따릅니다. "
        "현재 코드베이스를 존중하고, 최소한의 변경으로 목표를 달성하세요. "
        "한국어로 응답하되, 코드와 커밋 메시지는 영어로 작성하세요.\n\n"
    )

    phase_prompts = {
        "analyze": (
            "현재 ANALYZE 단계입니다. 사용자의 요구사항을 분석하세요.\n"
            "다음을 JSON 형태로 출력하세요:\n"
            '{"requirements": [...], "constraints": [...], '
            '"success_criteria": [...], "questions": [...]}\n'
            "questions가 비어있으면 바로 다음 단계로 진행할 수 있다는 뜻입니다."
        ),
        "explore": (
            "현재 EXPLORE 단계입니다. 제공된 도구를 사용하여 코드베이스를 탐색하세요.\n"
            "프로젝트 구조, 관련 파일, 기존 패턴, 의존성을 파악하세요.\n"
            "탐색이 끝나면 발견한 내용을 요약하세요."
        ),
        "plan": (
            "현재 PLAN 단계입니다. 구현 계획을 수립하세요.\n"
            "다음을 JSON 형태로 출력하세요:\n"
            '{"tasks": [{"id": 1, "title": "...", "description": "...", '
            '"files": ["..."], "depends_on": []}], '
            '"risks": [...], "approach": "..."}'
        ),
        "implement": (
            "현재 IMPLEMENT 단계입니다. 제공된 도구를 사용하여 코드를 구현하세요.\n"
            "한 번에 하나의 태스크만 진행하세요.\n"
            "기존 코드 스타일을 따르고, YAGNI 원칙을 지키세요.\n"
            "각 파일 수정 후 간략히 무엇을 왜 변경했는지 설명하세요."
        ),
        "verify": (
            "현재 VERIFY 단계입니다. 구현한 코드를 검증하세요.\n"
            "1. 테스트 명령어 실행\n"
            "2. 린터 실행\n"
            "3. 변경사항 리뷰\n"
            "4. 엣지케이스 확인\n"
            "문제가 발견되면 수정하세요."
        ),
        "deliver": (
            "현재 DELIVER 단계입니다. 변경사항을 정리하여 전달하세요.\n"
            "1. 변경 내용 요약\n"
            "2. 커밋 메시지 작성 (Conventional Commits 형식)\n"
            "3. PR 제목과 본문 작성\n"
            "JSON으로 출력하세요:\n"
            '{"commit_message": "...", "pr_title": "...", "pr_body": "...", '
            '"summary": "..."}'
        ),
        "review": (
            "현재 코드리뷰 반영 단계입니다. PR 리뷰 코멘트를 분석하고 수정하세요.\n"
            "각 코멘트에 대해:\n"
            "1. 코멘트 내용 이해\n"
            "2. 수정이 필요하면 코드 변경\n"
            "3. 수정 완료 후 결과 보고"
        ),
    }

    prompt = base + phase_prompts.get(phase, "")

    if project_context:
        prompt += f"\n\n프로젝트 컨텍스트:\n{project_context}"

    return prompt
