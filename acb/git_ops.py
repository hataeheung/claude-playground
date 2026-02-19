"""Git 및 GitHub 작업 자동화"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class CommandResult:
    success: bool
    output: str
    error: str = ""


def _run(cmd: list[str], cwd: str = ".") -> CommandResult:
    """Git 명령어 실행 헬퍼"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=cwd
        )
        if result.returncode != 0:
            return CommandResult(
                success=False, output=result.stdout, error=result.stderr
            )
        return CommandResult(success=True, output=result.stdout.strip())
    except subprocess.TimeoutExpired:
        return CommandResult(success=False, output="", error="타임아웃: 60초 초과")
    except FileNotFoundError:
        return CommandResult(success=False, output="", error="git 명령어를 찾을 수 없습니다.")


class GitOps:
    """Git 작업을 수행하는 클래스"""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def status(self) -> CommandResult:
        return _run(["git", "status", "--porcelain"], self.repo_path)

    def diff(self, staged: bool = False) -> CommandResult:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        return _run(cmd, self.repo_path)

    def current_branch(self) -> str:
        result = _run(["git", "branch", "--show-current"], self.repo_path)
        return result.output if result.success else ""

    def create_branch(self, branch_name: str) -> CommandResult:
        return _run(["git", "checkout", "-b", branch_name], self.repo_path)

    def checkout(self, branch_name: str) -> CommandResult:
        return _run(["git", "checkout", branch_name], self.repo_path)

    def add(self, files: list[str] | None = None) -> CommandResult:
        if files:
            return _run(["git", "add"] + files, self.repo_path)
        return _run(["git", "add", "-A"], self.repo_path)

    def commit(self, message: str) -> CommandResult:
        return _run(["git", "commit", "-m", message], self.repo_path)

    def push(self, branch: str = "", set_upstream: bool = True) -> CommandResult:
        cmd = ["git", "push"]
        if set_upstream and branch:
            cmd.extend(["-u", "origin", branch])
        elif branch:
            cmd.extend(["origin", branch])
        return _run(cmd, self.repo_path)

    def log(self, count: int = 5) -> CommandResult:
        return _run(
            ["git", "log", f"-{count}", "--oneline", "--no-decorate"],
            self.repo_path,
        )

    def diff_from_base(self, base_branch: str = "main") -> CommandResult:
        """현재 브랜치와 base 브랜치 간의 차이"""
        return _run(
            ["git", "diff", f"{base_branch}...HEAD"],
            self.repo_path,
        )

    def get_changed_files(self, base_branch: str = "main") -> list[str]:
        """base 브랜치 대비 변경된 파일 목록"""
        result = _run(
            ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
            self.repo_path,
        )
        if result.success and result.output:
            return result.output.strip().split("\n")
        return []


class GitHubOps:
    """GitHub CLI(gh)를 통한 PR 및 리뷰 작업"""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def create_pr(
        self,
        title: str,
        body: str,
        base: str = "main",
        draft: bool = False,
    ) -> CommandResult:
        """PR 생성"""
        cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base]
        if draft:
            cmd.append("--draft")
        return _run(cmd, self.repo_path)

    def get_pr_reviews(self, pr_number: int) -> CommandResult:
        """PR 리뷰 코멘트 가져오기"""
        return _run(
            ["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments"],
            self.repo_path,
        )

    def get_pr_review_comments(self, pr_number: int) -> CommandResult:
        """PR 리뷰 가져오기 (gh pr view 방식)"""
        return _run(
            ["gh", "pr", "view", str(pr_number), "--json",
             "reviews,comments,reviewRequests"],
            self.repo_path,
        )

    def list_pr(self, state: str = "open") -> CommandResult:
        """PR 목록 조회"""
        return _run(
            ["gh", "pr", "list", "--state", state, "--json",
             "number,title,state,url"],
            self.repo_path,
        )

    def pr_checks(self, pr_number: int) -> CommandResult:
        """PR CI 체크 상태 조회"""
        return _run(
            ["gh", "pr", "checks", str(pr_number)],
            self.repo_path,
        )

    def deploy(self, command: str) -> CommandResult:
        """배포 명령어 실행 (설정에 따라 다양)"""
        return _run(command.split(), self.repo_path)
