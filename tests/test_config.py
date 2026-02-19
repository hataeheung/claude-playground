"""config.py 테스트"""

import json

from acb.config import AgentConfig, ProjectConfig, get_api_key, load_config, save_config


class TestProjectConfig:
    def test_default_values(self):
        config = ProjectConfig()
        assert config.language == ""
        assert config.test_command == ""
        assert config.branch_strategy == "feature-branch"

    def test_custom_values(self):
        config = ProjectConfig(language="python", test_command="pytest")
        assert config.language == "python"
        assert config.test_command == "pytest"


class TestAgentConfig:
    def test_default_values(self):
        config = AgentConfig()
        assert config.model == "claude-sonnet-4-20250514"
        assert config.auto_commit is True
        assert config.require_confirmation is True
        assert isinstance(config.project, ProjectConfig)

    def test_to_dict_and_from_dict(self):
        config = AgentConfig(
            model="claude-sonnet-4-20250514",
            auto_deploy=True,
            base_branch="develop",
        )
        config.project.language = "python"
        config.project.test_command = "pytest"

        data = config.to_dict()
        restored = AgentConfig.from_dict(data)

        assert restored.model == config.model
        assert restored.auto_deploy == config.auto_deploy
        assert restored.base_branch == config.base_branch
        assert restored.project.language == "python"
        assert restored.project.test_command == "pytest"


class TestLoadSaveConfig:
    def test_save_and_load(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        config = AgentConfig()
        config.project.language = "typescript"
        config.anthropic_api_key = "sk-secret-key"

        save_config(config, config_path)

        # API 키는 파일에 저장되지 않아야 함
        with open(config_path) as f:
            data = json.load(f)
        assert "anthropic_api_key" not in data

        loaded = load_config(config_path)
        assert loaded.project.language == "typescript"

    def test_load_nonexistent_returns_default(self, tmp_path):
        config = load_config(str(tmp_path / "nonexistent.json"))
        assert isinstance(config, AgentConfig)
        assert config.model == "claude-sonnet-4-20250514"


class TestGetApiKey:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
        config = AgentConfig()
        assert get_api_key(config) == "sk-from-env"

    def test_from_config(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config = AgentConfig(anthropic_api_key="sk-from-config")
        assert get_api_key(config) == "sk-from-config"

    def test_env_takes_priority(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
        config = AgentConfig(anthropic_api_key="sk-from-config")
        assert get_api_key(config) == "sk-from-env"
