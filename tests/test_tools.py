"""tools.py 테스트"""


import pytest

from acb.tools import ToolExecutor


@pytest.fixture
def project_dir(tmp_path):
    """테스트용 프로젝트 디렉토리"""
    # 파일 구조 생성
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n")
    (tmp_path / "src" / "utils.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_hello(): pass\n")
    (tmp_path / "README.md").write_text("# Project\n")
    return tmp_path


@pytest.fixture
def executor(project_dir):
    return ToolExecutor(str(project_dir))


class TestReadFile:
    def test_read_existing_file(self, executor, project_dir):
        result = executor.execute("read_file", {"path": "src/main.py"})
        assert result.success
        assert "print('hello')" in result.output

    def test_read_nonexistent_file(self, executor):
        result = executor.execute("read_file", {"path": "nonexistent.py"})
        assert not result.success
        assert "찾을 수 없습니다" in result.error


class TestWriteFile:
    def test_write_new_file(self, executor, project_dir):
        result = executor.execute("write_file", {
            "path": "src/new_file.py",
            "content": "# new file\n",
        })
        assert result.success
        assert (project_dir / "src" / "new_file.py").read_text() == "# new file\n"

    def test_write_creates_directories(self, executor, project_dir):
        result = executor.execute("write_file", {
            "path": "src/sub/deep/file.py",
            "content": "content\n",
        })
        assert result.success
        assert (project_dir / "src" / "sub" / "deep" / "file.py").exists()


class TestEditFile:
    def test_edit_replaces_text(self, executor, project_dir):
        result = executor.execute("edit_file", {
            "path": "src/main.py",
            "old_text": "print('hello')",
            "new_text": "print('world')",
        })
        assert result.success
        assert (project_dir / "src" / "main.py").read_text() == "print('world')\n"

    def test_edit_nonexistent_text(self, executor):
        result = executor.execute("edit_file", {
            "path": "src/main.py",
            "old_text": "nonexistent text",
            "new_text": "replacement",
        })
        assert not result.success
        assert "찾을 수 없습니다" in result.error


class TestRunCommand:
    def test_run_simple_command(self, executor):
        result = executor.execute("run_command", {"command": "echo hello"})
        assert result.success
        assert "hello" in result.output

    def test_run_failing_command(self, executor):
        result = executor.execute("run_command", {"command": "false"})
        assert not result.success

    def test_dangerous_command_blocked(self, executor):
        result = executor.execute("run_command", {"command": "rm -rf /"})
        assert not result.success
        assert "위험한 명령어" in result.error


class TestSearchFiles:
    def test_search_by_pattern(self, executor):
        result = executor.execute("search_files", {"pattern": "**/*.py"})
        assert result.success
        assert "main.py" in result.output
        assert "utils.py" in result.output

    def test_search_no_match(self, executor):
        result = executor.execute("search_files", {"pattern": "**/*.rs"})
        assert result.success
        assert "일치하는 파일이 없습니다" in result.output


class TestListDirectory:
    def test_list_root(self, executor):
        result = executor.execute("list_directory", {"path": "."})
        assert result.success
        assert "src/" in result.output
        assert "README.md" in result.output

    def test_list_recursive(self, executor):
        result = executor.execute("list_directory", {"path": ".", "recursive": True})
        assert result.success
        assert "main.py" in result.output

    def test_list_nonexistent(self, executor):
        result = executor.execute("list_directory", {"path": "nonexistent/"})
        assert not result.success


class TestPathSecurity:
    def test_cannot_escape_project_root(self, executor):
        result = executor.execute("read_file", {"path": "../../etc/passwd"})
        assert not result.success
        assert "프로젝트 루트 밖" in result.error


class TestUnknownTool:
    def test_unknown_tool_name(self, executor):
        result = executor.execute("unknown_tool", {})
        assert not result.success
        assert "알 수 없는 도구" in result.error
