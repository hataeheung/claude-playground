"""자율 AI 개발 에이전트 - 전체 개발 파이프라인 오케스트레이션

파이프라인:
  ANALYZE → EXPLORE → PLAN → IMPLEMENT → VERIFY → DELIVER → REVIEW → DEPLOY
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from acb.config import AgentConfig
from acb.git_ops import GitHubOps, GitOps
from acb.llm import AGENT_TOOLS, LLMClient, LLMResponse, build_system_prompt
from acb.tools import ToolExecutor

console = Console()

# 에이전트 파이프라인의 단계 (기존 6단계 + review + deploy)
PIPELINE_PHASES = [
    "analyze", "explore", "plan", "implement", "verify", "deliver",
    "review", "deploy",
]

PHASE_DISPLAY = {
    "analyze": ("ANALYZE", "bright_cyan", "요구사항 분석 중"),
    "explore": ("EXPLORE", "bright_yellow", "코드베이스 탐색 중"),
    "plan": ("PLAN", "bright_magenta", "구현 계획 수립 중"),
    "implement": ("IMPLEMENT", "bright_green", "코드 구현 중"),
    "verify": ("VERIFY", "bright_blue", "검증 및 테스트 중"),
    "deliver": ("DELIVER", "bright_red", "커밋 및 PR 생성 중"),
    "review": ("REVIEW", "bright_cyan", "코드리뷰 반영 중"),
    "deploy": ("DEPLOY", "bright_green", "배포 중"),
}

MAX_TOOL_ITERATIONS = 20  # 각 단계에서 최대 tool 호출 횟수


@dataclass
class PhaseResult:
    """각 단계의 실행 결과"""
    phase: str
    success: bool
    output: str
    data: dict = field(default_factory=dict)
    error: str = ""


@dataclass
class PipelineState:
    """파이프라인 전체 상태"""
    requirement: str
    current_phase: str = "analyze"
    results: dict[str, PhaseResult] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)  # 단계 간 전달할 컨텍스트
    pr_number: int | None = None
    pr_url: str = ""
    is_complete: bool = False
    error: str = ""


def _show_phase_header(phase: str):
    """단계 시작 헤더 표시"""
    name, color, desc = PHASE_DISPLAY.get(phase, (phase, "white", ""))
    header = Text()
    header.append(f" [{name}] ", style=f"bold white on {color}")
    header.append(f" {desc}", style=f"{color}")
    console.print()
    console.print(header)
    console.print(f"[dim]{'─' * 60}[/dim]")


def _show_tool_call(tool_name: str, args: dict):
    """도구 호출 표시"""
    arg_summary = ""
    if "path" in args:
        arg_summary = args["path"]
    elif "command" in args:
        arg_summary = args["command"][:60]
    elif "pattern" in args:
        arg_summary = args["pattern"]
    console.print(f"  [dim]> {tool_name}[/dim] [cyan]{arg_summary}[/cyan]")


def _show_phase_result(result: PhaseResult):
    """단계 결과 표시"""
    status = "[green]성공[/green]" if result.success else "[red]실패[/red]"
    console.print(f"\n  결과: {status}")
    if result.output:
        # 긴 출력은 잘라서 표시
        lines = result.output.split("\n")
        preview = "\n".join(lines[:10])
        if len(lines) > 10:
            preview += f"\n  ... ({len(lines) - 10}줄 더)"
        console.print(f"  [dim]{preview}[/dim]")


def _confirm(prompt: str, default: bool = True) -> bool:
    """사용자 확인"""
    suffix = " [Y/n]" if default else " [y/N]"
    response = console.input(f"  [bold yellow]{prompt}{suffix}[/bold yellow] ").strip().lower()
    if not response:
        return default
    return response in ("y", "yes")


class DevAgent:
    """자율 개발 에이전트 - 전체 파이프라인 실행"""

    def __init__(self, config: AgentConfig, project_root: str = "."):
        self.config = config
        self.project_root = project_root
        self.llm = LLMClient(config)
        self.tools = ToolExecutor(project_root)
        self.git = GitOps(project_root)
        self.github = GitHubOps(project_root)

    def run(self, requirement: str) -> PipelineState:
        """전체 파이프라인 실행"""
        state = PipelineState(requirement=requirement)

        console.print(Panel(
            f"[bold]요구사항:[/bold] {requirement}",
            title="AI Dev Agent - 자율 개발 시작",
            border_style="blue",
        ))

        phases_to_run = list(PIPELINE_PHASES)

        # 배포가 비활성화면 deploy 단계 제외
        if not self.config.auto_deploy:
            phases_to_run = [p for p in phases_to_run if p != "deploy"]

        for phase in phases_to_run:
            state.current_phase = phase
            _show_phase_header(phase)

            # 사용자 확인이 필요한 경우
            if self.config.require_confirmation and phase in ("implement", "deliver", "deploy"):
                if not _confirm(f"{phase.upper()} 단계를 진행할까요?"):
                    state.error = f"사용자가 {phase} 단계를 취소했습니다."
                    console.print("  [yellow]취소됨[/yellow]")
                    break

            try:
                result = self._run_phase(phase, state)
                state.results[phase] = result
                _show_phase_result(result)

                if not result.success:
                    state.error = f"{phase} 단계 실패: {result.error}"
                    console.print(f"  [red]파이프라인 중단: {result.error}[/red]")
                    break

            except Exception as e:
                state.error = f"{phase} 단계 예외: {str(e)}"
                state.results[phase] = PhaseResult(
                    phase=phase, success=False, output="", error=str(e)
                )
                console.print(f"  [red]예외 발생: {e}[/red]")
                break
        else:
            state.is_complete = True

        self._show_summary(state)
        return state

    def _run_phase(self, phase: str, state: PipelineState) -> PhaseResult:
        """각 단계 실행"""
        handlers = {
            "analyze": self._phase_analyze,
            "explore": self._phase_explore,
            "plan": self._phase_plan,
            "implement": self._phase_implement,
            "verify": self._phase_verify,
            "deliver": self._phase_deliver,
            "review": self._phase_review,
            "deploy": self._phase_deploy,
        }
        handler = handlers[phase]
        return handler(state)

    def _agentic_loop(
        self,
        phase: str,
        state: PipelineState,
        initial_prompt: str,
    ) -> LLMResponse:
        """에이전틱 루프 - LLM과 도구를 반복 호출하여 작업 완료"""
        system = build_system_prompt(phase, self._build_context(state))
        messages = [{"role": "user", "content": initial_prompt}]

        for iteration in range(MAX_TOOL_ITERATIONS):
            response = self.llm.chat(messages, system=system, tools=AGENT_TOOLS)

            if not response.has_tool_calls:
                return response

            # assistant 메시지 기록 (tool_use 포함)
            assistant_content = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
                console.print(f"  [dim]{response.text[:200]}[/dim]")

            for tc in response.tool_calls:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc.tool_id,
                    "name": tc.name,
                    "input": tc.arguments,
                })

            messages.append({"role": "assistant", "content": assistant_content})

            # 도구 실행 및 결과 반환
            tool_results = []
            for tc in response.tool_calls:
                _show_tool_call(tc.name, tc.arguments)
                result = self.tools.execute(tc.name, tc.arguments)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.tool_id,
                    "content": (
                        result.output if result.success
                        else f"ERROR: {result.error}\n{result.output}"
                    ),
                })

            messages.append({"role": "user", "content": tool_results})

        # 최대 반복 도달
        return LLMResponse(text="최대 도구 호출 횟수에 도달했습니다.", stop_reason="max_iterations")

    def _build_context(self, state: PipelineState) -> str:
        """이전 단계 결과를 컨텍스트 문자열로 변환"""
        parts = [f"요구사항: {state.requirement}"]
        for phase, result in state.results.items():
            if result.success:
                parts.append(f"\n[{phase.upper()} 결과]\n{result.output[:2000]}")
        return "\n".join(parts)

    # ── 각 단계 구현 ──────────────────────────────────────────────

    def _phase_analyze(self, state: PipelineState) -> PhaseResult:
        """ANALYZE: 요구사항 분석"""
        prompt = (
            f"다음 요구사항을 분석해주세요:\n\n{state.requirement}\n\n"
            "JSON 형태로 분석 결과를 출력하세요:\n"
            '{"requirements": [...], "constraints": [...], '
            '"success_criteria": [...], "questions": []}'
        )
        response = self.llm.simple_chat(
            prompt, system=build_system_prompt("analyze")
        )

        # JSON 파싱 시도
        try:
            data = self._extract_json(response)
            state.context["analysis"] = data
        except (json.JSONDecodeError, ValueError):
            state.context["analysis"] = {"raw": response}

        return PhaseResult(phase="analyze", success=True, output=response)

    def _phase_explore(self, state: PipelineState) -> PhaseResult:
        """EXPLORE: 코드베이스 탐색 (에이전틱 루프)"""
        prompt = (
            "프로젝트 코드베이스를 탐색하세요.\n"
            "1. 프로젝트 구조 파악 (list_directory 사용)\n"
            "2. 주요 설정 파일 읽기 (package.json, pyproject.toml 등)\n"
            "3. 관련 소스 파일 탐색\n"
            "4. 기존 테스트 확인\n\n"
            "탐색이 끝나면 발견한 내용을 요약해주세요."
        )
        response = self._agentic_loop("explore", state, prompt)

        state.context["exploration"] = response.text
        return PhaseResult(phase="explore", success=True, output=response.text)

    def _phase_plan(self, state: PipelineState) -> PhaseResult:
        """PLAN: 구현 계획 수립"""
        prompt = (
            "이전 탐색 결과를 바탕으로 구현 계획을 세워주세요.\n"
            "JSON 형태로 출력하세요:\n"
            '{"tasks": [{"id": 1, "title": "...", "description": "...", '
            '"files": [...], "depends_on": []}], '
            '"risks": [...], "approach": "..."}'
        )
        response = self.llm.simple_chat(
            prompt, system=build_system_prompt("plan", self._build_context(state))
        )

        try:
            data = self._extract_json(response)
            state.context["plan"] = data
        except (json.JSONDecodeError, ValueError):
            state.context["plan"] = {"raw": response}

        return PhaseResult(phase="plan", success=True, output=response)

    def _phase_implement(self, state: PipelineState) -> PhaseResult:
        """IMPLEMENT: 코드 구현 (에이전틱 루프)"""
        plan = state.context.get("plan", {})
        tasks_desc = ""
        if isinstance(plan, dict) and "tasks" in plan:
            for t in plan["tasks"]:
                tid = t.get('id', '?')
                title = t.get('title', '')
                desc = t.get('description', '')
                tasks_desc += f"- [{tid}] {title}: {desc}\n"
        else:
            tasks_desc = str(plan)

        prompt = (
            "다음 계획에 따라 코드를 구현하세요.\n\n"
            f"구현할 태스크:\n{tasks_desc}\n\n"
            "도구를 사용하여 파일을 읽고, 수정하고, 작성하세요.\n"
            "한 태스크씩 순서대로 진행하세요."
        )
        response = self._agentic_loop("implement", state, prompt)

        return PhaseResult(phase="implement", success=True, output=response.text)

    def _phase_verify(self, state: PipelineState) -> PhaseResult:
        """VERIFY: 테스트 및 검증 (에이전틱 루프)"""
        test_cmd = self.config.project.test_command
        lint_cmd = self.config.project.lint_command

        prompt = "구현한 코드를 검증하세요.\n\n"
        if test_cmd:
            prompt += f"1. 테스트 실행: `{test_cmd}`\n"
        if lint_cmd:
            prompt += f"2. 린터 실행: `{lint_cmd}`\n"
        prompt += (
            "3. 변경된 파일을 리뷰하여 버그나 누락이 없는지 확인\n"
            "4. 문제가 있으면 수정\n\n"
            "검증 결과를 보고해주세요."
        )

        response = self._agentic_loop("verify", state, prompt)

        # 검증 실패 판단
        success = True
        if "실패" in response.text.lower() or "fail" in response.text.lower():
            if "수정 완료" not in response.text and "fixed" not in response.text.lower():
                success = False

        return PhaseResult(
            phase="verify", success=success, output=response.text,
            error="" if success else "검증에서 미해결 문제가 발견되었습니다."
        )

    def _phase_deliver(self, state: PipelineState) -> PhaseResult:
        """DELIVER: 커밋 및 PR 생성"""
        # LLM에게 커밋 메시지와 PR 내용 생성 요청
        prompt = (
            "지금까지의 변경사항을 정리하여 다음을 JSON으로 출력하세요:\n"
            '{"commit_message": "type: short description", '
            '"pr_title": "...", '
            '"pr_body": "## Summary\\n...\\n## Changes\\n...", '
            '"summary": "..."}'
        )
        response = self.llm.simple_chat(
            prompt, system=build_system_prompt("deliver", self._build_context(state))
        )

        try:
            data = self._extract_json(response)
        except (json.JSONDecodeError, ValueError):
            data = {
                "commit_message": f"feat: implement {state.requirement[:50]}",
                "pr_title": state.requirement[:70],
                "pr_body": response,
                "summary": response,
            }

        # Git 작업 수행
        if self.config.auto_commit:
            console.print("  [dim]변경사항 커밋 중...[/dim]")
            self.git.add()
            commit_result = self.git.commit(data.get("commit_message", "feat: auto commit"))
            if not commit_result.success:
                return PhaseResult(
                    phase="deliver", success=False, output=commit_result.output,
                    error=f"커밋 실패: {commit_result.error}",
                )
            console.print(f"  [green]커밋 완료[/green]: {data.get('commit_message', '')}")

        if self.config.auto_push:
            branch = self.git.current_branch()
            console.print(f"  [dim]{branch} 브랜치 푸시 중...[/dim]")
            push_result = self.git.push(branch)
            if not push_result.success:
                return PhaseResult(
                    phase="deliver", success=False, output=push_result.output,
                    error=f"푸시 실패: {push_result.error}",
                )
            console.print("  [green]푸시 완료[/green]")

        if self.config.auto_pr:
            console.print("  [dim]PR 생성 중...[/dim]")
            pr_result = self.github.create_pr(
                title=data.get("pr_title", state.requirement[:70]),
                body=data.get("pr_body", "Auto-generated PR"),
                base=self.config.base_branch,
            )
            if pr_result.success:
                state.pr_url = pr_result.output.strip()
                console.print(f"  [green]PR 생성 완료[/green]: {state.pr_url}")
            else:
                console.print(f"  [yellow]PR 생성 실패 (커밋은 완료): {pr_result.error}[/yellow]")

        return PhaseResult(
            phase="deliver", success=True, output=response,
            data=data,
        )

    def _phase_review(self, state: PipelineState) -> PhaseResult:
        """REVIEW: 코드리뷰 반영"""
        if not state.pr_number and not state.pr_url:
            console.print("  [dim]PR이 없어 리뷰 단계를 건너뜁니다.[/dim]")
            return PhaseResult(phase="review", success=True, output="PR 없음 - 건너뜀")

        # PR 번호 추출 시도
        pr_number = state.pr_number
        if not pr_number and state.pr_url:
            try:
                pr_number = int(state.pr_url.rstrip("/").split("/")[-1])
                state.pr_number = pr_number
            except (ValueError, IndexError):
                pass

        if not pr_number:
            return PhaseResult(phase="review", success=True, output="PR 번호 확인 불가 - 건너뜀")

        # 리뷰 코멘트 가져오기
        review_result = self.github.get_pr_review_comments(pr_number)
        if not review_result.success or not review_result.output.strip():
            console.print("  [dim]리뷰 코멘트가 없습니다.[/dim]")
            return PhaseResult(phase="review", success=True, output="리뷰 코멘트 없음")

        # LLM에게 리뷰 코멘트 분석 및 수정 요청
        prompt = (
            f"다음 PR 리뷰 코멘트를 분석하고 필요한 수정을 해주세요:\n\n"
            f"{review_result.output}\n\n"
            "각 코멘트에 대해 수정이 필요하면 도구를 사용하여 코드를 수정하세요."
        )
        response = self._agentic_loop("review", state, prompt)

        # 수정사항이 있으면 추가 커밋
        status = self.git.status()
        if status.success and status.output.strip():
            self.git.add()
            self.git.commit("fix: address code review feedback")
            branch = self.git.current_branch()
            self.git.push(branch)
            console.print("  [green]리뷰 반영 커밋 완료[/green]")

        return PhaseResult(phase="review", success=True, output=response.text)

    def _phase_deploy(self, state: PipelineState) -> PhaseResult:
        """DEPLOY: 배포"""
        deploy_cmd = self.config.project.deploy_command
        if not deploy_cmd:
            return PhaseResult(
                phase="deploy", success=True,
                output="배포 명령어가 설정되지 않아 건너뜁니다."
            )

        if self.config.require_confirmation:
            if not _confirm(f"배포 명령어를 실행할까요? ({deploy_cmd})"):
                return PhaseResult(
                    phase="deploy", success=True,
                    output="사용자가 배포를 취소했습니다."
                )

        console.print(f"  [dim]배포 실행: {deploy_cmd}[/dim]")
        result = self.github.deploy(deploy_cmd)

        return PhaseResult(
            phase="deploy",
            success=result.success,
            output=result.output,
            error=result.error if not result.success else "",
        )

    # ── 유틸리티 ──────────────────────────────────────────────────

    def _extract_json(self, text: str) -> dict:
        """텍스트에서 JSON 블록 추출"""
        # ```json ... ``` 블록에서 추출 시도
        import re
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # 중괄호 기반 추출
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])

        raise ValueError("JSON을 찾을 수 없습니다.")

    def _show_summary(self, state: PipelineState):
        """파이프라인 실행 요약"""
        console.print()
        console.print(Panel(
            self._build_summary_text(state),
            title="파이프라인 실행 결과",
            border_style="green" if state.is_complete else "red",
        ))

    def _build_summary_text(self, state: PipelineState) -> str:
        """요약 텍스트 생성"""
        lines = []
        status = "[green]완료[/green]" if state.is_complete else "[red]중단[/red]"
        lines.append(f"상태: {status}")
        lines.append(f"요구사항: {state.requirement}")
        lines.append("")

        for phase in PIPELINE_PHASES:
            result = state.results.get(phase)
            if result:
                icon = "[green]+[/green]" if result.success else "[red]x[/red]"
                name = PHASE_DISPLAY.get(phase, (phase, "", ""))[0]
                lines.append(f"  {icon} {name}")
            else:
                name = PHASE_DISPLAY.get(phase, (phase, "", ""))[0]
                lines.append(f"  [dim]- {name}[/dim]")

        if state.pr_url:
            lines.append(f"\nPR: {state.pr_url}")
        if state.error:
            lines.append(f"\n[red]오류: {state.error}[/red]")

        return "\n".join(lines)
