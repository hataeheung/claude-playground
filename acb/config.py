"""에이전트 설정 관리"""

import json
import os
from dataclasses import asdict, dataclass, field

CONFIG_FILE = ".acb/agent_config.json"


@dataclass
class ProjectConfig:
    """프로젝트별 설정"""
    language: str = ""
    framework: str = ""
    test_command: str = ""
    lint_command: str = ""
    build_command: str = ""
    deploy_command: str = ""
    branch_strategy: str = "feature-branch"
    commit_convention: str = "conventional"
    code_style: str = ""


@dataclass
class AgentConfig:
    """에이전트 전체 설정"""
    # LLM 설정
    anthropic_api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096

    # 에이전트 동작 설정
    auto_commit: bool = True
    auto_push: bool = True
    auto_pr: bool = True
    auto_deploy: bool = False
    require_confirmation: bool = True  # 각 단계마다 사용자 확인 요구

    # Git 설정
    base_branch: str = "main"
    branch_prefix: str = "agent/"

    # 프로젝트 설정
    project: ProjectConfig = field(default_factory=ProjectConfig)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        project_data = data.pop("project", {})
        config = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        config.project = ProjectConfig(**{
            k: v for k, v in project_data.items()
            if k in ProjectConfig.__dataclass_fields__
        })
        return config


def load_config(path: str = CONFIG_FILE) -> AgentConfig:
    """설정 파일 로드. 없으면 기본값 반환."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return AgentConfig.from_dict(json.load(f))
    # 환경변수에서 API 키 가져오기
    config = AgentConfig()
    config.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    return config


def save_config(config: AgentConfig, path: str = CONFIG_FILE):
    """설정 파일 저장."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = config.to_dict()
    # API 키는 파일에 저장하지 않음
    data.pop("anthropic_api_key", None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_api_key(config: AgentConfig) -> str:
    """API 키를 환경변수 또는 설정에서 가져오기."""
    return os.environ.get("ANTHROPIC_API_KEY", "") or config.anthropic_api_key
