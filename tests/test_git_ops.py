"""git_ops.py 테스트"""

import subprocess

import pytest

from acb.git_ops import GitOps


def _git(tmp_path, *args):
    return subprocess.run(
        ["git"] + list(args),
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )


@pytest.fixture
def git_repo(tmp_path):
    """테스트용 git 저장소"""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@test.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "commit.gpgSign", "false")
    # 초기 커밋
    (tmp_path / "README.md").write_text("# Test\n")
    _git(tmp_path, "add", ".")
    result = _git(tmp_path, "commit", "--no-gpg-sign", "-m", "init")
    if result.returncode != 0:
        pytest.skip(f"git commit not available in test env: {result.stderr}")
    return tmp_path


class TestGitOps:
    def test_status_clean(self, git_repo):
        ops = GitOps(str(git_repo))
        result = ops.status()
        assert result.success
        assert result.output == ""  # clean status

    def test_status_with_changes(self, git_repo):
        (git_repo / "new_file.txt").write_text("hello\n")
        ops = GitOps(str(git_repo))
        result = ops.status()
        assert result.success
        assert "new_file.txt" in result.output

    def test_current_branch(self, git_repo):
        ops = GitOps(str(git_repo))
        branch = ops.current_branch()
        assert branch in ("main", "master")

    def test_add(self, git_repo):
        (git_repo / "test.txt").write_text("test content\n")
        ops = GitOps(str(git_repo))

        add_result = ops.add(["test.txt"])
        assert add_result.success

        # staged에 올라갔는지 확인
        diff_result = ops.diff(staged=True)
        assert diff_result.success

    def test_log(self, git_repo):
        ops = GitOps(str(git_repo))
        result = ops.log(count=1)
        assert result.success
        assert "init" in result.output

    def test_create_branch(self, git_repo):
        ops = GitOps(str(git_repo))
        result = ops.create_branch("feature/test")
        assert result.success
        assert ops.current_branch() == "feature/test"

    def test_diff_no_changes(self, git_repo):
        ops = GitOps(str(git_repo))
        result = ops.diff()
        assert result.success
        assert result.output == ""

    def test_diff_with_changes(self, git_repo):
        (git_repo / "README.md").write_text("# Updated\n")
        ops = GitOps(str(git_repo))
        result = ops.diff()
        assert result.success
        assert "Updated" in result.output
