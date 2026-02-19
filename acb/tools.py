"""에이전트가 사용하는 도구 실행기

LLM의 tool_use 요청을 실제 파일시스템/셸 작업으로 변환합니다.
"""

from __future__ import annotations

import glob
import os
import subprocess
from dataclasses import dataclass


@dataclass
class ToolResult:
    """도구 실행 결과"""
    success: bool
    output: str
    error: str = ""


class ToolExecutor:
    """에이전트의 도구 호출을 실행하는 클래스"""

    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)

    def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        """도구 이름과 인자를 받아 실행"""
        handlers = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "edit_file": self._edit_file,
            "run_command": self._run_command,
            "search_files": self._search_files,
            "search_content": self._search_content,
            "list_directory": self._list_directory,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return ToolResult(success=False, output="", error=f"알 수 없는 도구: {tool_name}")

        try:
            return handler(**arguments)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def _resolve_path(self, path: str) -> str:
        """상대 경로를 프로젝트 루트 기준으로 절대 경로로 변환"""
        if os.path.isabs(path):
            resolved = os.path.abspath(path)
        else:
            resolved = os.path.abspath(os.path.join(self.project_root, path))

        # 프로젝트 루트 밖으로 나가는 것을 방지
        if not resolved.startswith(self.project_root):
            raise PermissionError(f"프로젝트 루트 밖의 파일에 접근할 수 없습니다: {path}")
        return resolved

    def _read_file(self, path: str) -> ToolResult:
        resolved = self._resolve_path(path)
        if not os.path.exists(resolved):
            return ToolResult(success=False, output="", error=f"파일을 찾을 수 없습니다: {path}")
        with open(resolved, "r", encoding="utf-8") as f:
            content = f.read()
        return ToolResult(success=True, output=content)

    def _write_file(self, path: str, content: str) -> ToolResult:
        resolved = self._resolve_path(path)
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        return ToolResult(success=True, output=f"파일 작성 완료: {path}")

    def _edit_file(self, path: str, old_text: str, new_text: str) -> ToolResult:
        resolved = self._resolve_path(path)
        if not os.path.exists(resolved):
            return ToolResult(success=False, output="", error=f"파일을 찾을 수 없습니다: {path}")

        with open(resolved, "r", encoding="utf-8") as f:
            content = f.read()

        if old_text not in content:
            return ToolResult(
                success=False, output="",
                error=f"'{old_text[:50]}...'을(를) 파일에서 찾을 수 없습니다."
            )

        new_content = content.replace(old_text, new_text, 1)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(new_content)

        return ToolResult(success=True, output=f"파일 수정 완료: {path}")

    def _run_command(self, command: str, timeout: int = 60) -> ToolResult:
        # 위험한 명령어 차단
        dangerous = ["rm -rf /", "mkfs", "dd if=", "> /dev/"]
        for d in dangerous:
            if d in command:
                return ToolResult(
                    success=False, output="",
                    error=f"위험한 명령어가 차단되었습니다: {command}"
                )

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root,
            )
            output = result.stdout
            if result.returncode != 0:
                output += f"\n[STDERR]\n{result.stderr}" if result.stderr else ""
                return ToolResult(
                    success=False,
                    output=output,
                    error=f"명령어 실패 (exit code: {result.returncode})",
                )
            return ToolResult(success=True, output=output)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error=f"타임아웃: {timeout}초 초과")

    def _search_files(self, pattern: str, path: str = "") -> ToolResult:
        search_root = self._resolve_path(path) if path else self.project_root
        matches = glob.glob(os.path.join(search_root, pattern), recursive=True)

        # 프로젝트 루트 기준 상대 경로로 변환
        relative = [os.path.relpath(m, self.project_root) for m in matches]
        # .git 디렉토리 제외
        relative = [r for r in relative if not r.startswith(".git/")]

        if not relative:
            return ToolResult(success=True, output="일치하는 파일이 없습니다.")
        return ToolResult(success=True, output="\n".join(sorted(relative)))

    def _search_content(
        self, pattern: str, path: str = "", file_pattern: str = ""
    ) -> ToolResult:
        search_root = self._resolve_path(path) if path else self.project_root

        cmd = ["grep", "-rn", "--include", file_pattern or "*", pattern, search_root]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, cwd=self.project_root
            )
            output = result.stdout
            if not output:
                return ToolResult(success=True, output="일치하는 결과가 없습니다.")

            # 절대 경로를 상대 경로로 변환
            lines = []
            for line in output.split("\n"):
                if line:
                    line = line.replace(self.project_root + "/", "")
                    lines.append(line)
            return ToolResult(success=True, output="\n".join(lines[:50]))
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="검색 타임아웃")

    def _list_directory(self, path: str, recursive: bool = False) -> ToolResult:
        resolved = self._resolve_path(path)
        if not os.path.isdir(resolved):
            return ToolResult(
                success=False, output="",
                error=f"디렉토리가 아닙니다: {path}"
            )

        entries = []
        if recursive:
            for root, dirs, files in os.walk(resolved):
                # .git 제외
                dirs[:] = [d for d in dirs if d != ".git"]
                rel_root = os.path.relpath(root, self.project_root)
                for f in files:
                    entries.append(os.path.join(rel_root, f))
        else:
            for entry in sorted(os.listdir(resolved)):
                if entry.startswith(".git"):
                    continue
                full = os.path.join(resolved, entry)
                suffix = "/" if os.path.isdir(full) else ""
                rel = os.path.relpath(full, self.project_root)
                entries.append(rel + suffix)

        return ToolResult(success=True, output="\n".join(entries))
