"""에이전틱 코딩 프로세스 정의 및 상태 관리"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Phase(Enum):
    ANALYZE = "analyze"
    EXPLORE = "explore"
    PLAN = "plan"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    DELIVER = "deliver"


PHASE_INFO = {
    Phase.ANALYZE: {
        "title": "ANALYZE (분석)",
        "question": "무엇을 만들어야 하는가?",
        "description": "요구사항을 명확히 이해하고 범위를 정의합니다.",
        "checklist": [
            "요구사항이 명확한가?",
            "모호한 부분에 대해 질문했는가?",
            "기능적/비기능적 요구사항을 구분했는가?",
            "제약 조건을 파악했는가? (기술 스택, 시간, 리소스)",
            "완료 기준(Done criteria)을 정의했는가?",
        ],
        "outputs": ["요구사항 정리", "성공 기준 목록"],
    },
    Phase.EXPLORE: {
        "title": "EXPLORE (탐색)",
        "question": "현재 상태는 어떠한가?",
        "description": "기존 코드베이스를 파악하고 영향 범위를 분석합니다.",
        "checklist": [
            "프로젝트 구조를 파악했는가?",
            "관련 파일을 모두 읽었는가?",
            "기존 패턴과 컨벤션을 이해했는가?",
            "의존성(dependencies)을 확인했는가?",
            "기존 테스트가 있다면 확인했는가?",
            "영향 범위(blast radius)를 파악했는가?",
        ],
        "outputs": ["관련 파일 목록", "아키텍처 이해 메모", "영향 범위 분석"],
    },
    Phase.PLAN: {
        "title": "PLAN (계획)",
        "question": "어떻게 만들 것인가?",
        "description": "구현 전략을 수립하고 작업을 분해합니다.",
        "checklist": [
            "구현 접근 방식을 결정했는가?",
            "대안적 접근 방식을 검토했는가?",
            "작업을 독립적인 단위로 분해했는가?",
            "작업 순서(의존성)를 정했는가?",
            "각 작업의 예상 복잡도를 평가했는가?",
            "위험 요소와 대응 방안을 준비했는가?",
        ],
        "outputs": ["작업 분해 목록 (TODO)", "구현 순서도", "위험 요소 목록"],
    },
    Phase.IMPLEMENT: {
        "title": "IMPLEMENT (구현)",
        "question": "코드를 작성한다",
        "description": "계획에 따라 점진적으로 코드를 작성합니다.",
        "checklist": [
            "한 번에 하나의 작업만 진행하는가?",
            "기존 코드 스타일/패턴을 따르는가?",
            "불필요한 복잡성을 추가하지 않았는가? (YAGNI)",
            "보안 취약점이 없는가? (injection, XSS 등)",
            "에러 처리가 적절한가?",
            "각 변경 후 동작을 확인했는가?",
        ],
        "outputs": ["구현된 코드", "각 단계별 검증 결과"],
    },
    Phase.VERIFY: {
        "title": "VERIFY (검증)",
        "question": "제대로 동작하는가?",
        "description": "구현이 요구사항을 충족하는지 검증합니다.",
        "checklist": [
            "모든 기존 테스트가 통과하는가?",
            "새로운 기능에 대한 테스트를 작성했는가?",
            "엣지 케이스를 고려했는가?",
            "린터/포매터를 실행했는가?",
            "수동 테스트를 수행했는가?",
            "성능에 문제가 없는가?",
            "원래 요구사항과 비교하여 누락된 것이 없는가?",
        ],
        "outputs": ["테스트 결과", "코드 리뷰 체크리스트", "검증 보고서"],
    },
    Phase.DELIVER: {
        "title": "DELIVER (전달)",
        "question": "변경사항을 전달한다",
        "description": "깔끔한 커밋을 만들고 PR을 준비합니다.",
        "checklist": [
            "커밋 메시지가 명확한가?",
            "불필요한 파일이 포함되지 않았는가?",
            "변경사항 요약을 작성했는가?",
            "리뷰어에게 필요한 컨텍스트를 제공했는가?",
            "필요시 문서를 업데이트했는가?",
        ],
        "outputs": ["Git 커밋", "PR 설명", "변경사항 요약"],
    },
}

PHASE_ORDER = [
    Phase.ANALYZE,
    Phase.EXPLORE,
    Phase.PLAN,
    Phase.IMPLEMENT,
    Phase.VERIFY,
    Phase.DELIVER,
]


@dataclass
class TaskNote:
    """프로세스 단계에서 기록하는 메모"""
    phase: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CheckItem:
    """체크리스트 항목"""
    text: str
    checked: bool = False


@dataclass
class Session:
    """하나의 코딩 세션(작업) 상태"""
    task_name: str
    current_phase: Phase = Phase.ANALYZE
    checklists: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    tasks: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        # 각 Phase별 체크리스트 초기화
        if not self.checklists:
            self.checklists = {}
            for phase in Phase:
                items = PHASE_INFO[phase]["checklist"]
                self.checklists[phase.value] = [
                    {"text": item, "checked": False} for item in items
                ]

    def get_current_checklist(self) -> list[dict]:
        return self.checklists.get(self.current_phase.value, [])

    def check_item(self, phase: Phase, index: int) -> bool:
        items = self.checklists.get(phase.value, [])
        if 0 <= index < len(items):
            items[index]["checked"] = not items[index]["checked"]
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def add_note(self, content: str):
        self.notes.append(TaskNote(
            phase=self.current_phase.value,
            content=content,
        ).__dict__)
        self.updated_at = datetime.now().isoformat()

    def add_task(self, description: str):
        self.tasks.append({
            "description": description,
            "done": False,
            "phase": self.current_phase.value,
        })
        self.updated_at = datetime.now().isoformat()

    def toggle_task(self, index: int) -> bool:
        if 0 <= index < len(self.tasks):
            self.tasks[index]["done"] = not self.tasks[index]["done"]
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def advance_phase(self) -> Optional[Phase]:
        idx = PHASE_ORDER.index(self.current_phase)
        if idx < len(PHASE_ORDER) - 1:
            self.current_phase = PHASE_ORDER[idx + 1]
            self.updated_at = datetime.now().isoformat()
            return self.current_phase
        return None

    def go_back_phase(self) -> Optional[Phase]:
        idx = PHASE_ORDER.index(self.current_phase)
        if idx > 0:
            self.current_phase = PHASE_ORDER[idx - 1]
            self.updated_at = datetime.now().isoformat()
            return self.current_phase
        return None

    def get_progress(self) -> dict:
        """전체 진행 상황 요약"""
        result = {}
        for phase in Phase:
            items = self.checklists.get(phase.value, [])
            total = len(items)
            checked = sum(1 for i in items if i["checked"])
            result[phase.value] = {
                "total": total,
                "checked": checked,
                "complete": checked == total and total > 0,
            }
        return result

    def to_dict(self) -> dict:
        return {
            "task_name": self.task_name,
            "current_phase": self.current_phase.value,
            "checklists": self.checklists,
            "notes": self.notes,
            "tasks": self.tasks,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        session = cls(task_name=data["task_name"])
        session.current_phase = Phase(data["current_phase"])
        session.checklists = data["checklists"]
        session.notes = data.get("notes", [])
        session.tasks = data.get("tasks", [])
        session.created_at = data.get("created_at", "")
        session.updated_at = data.get("updated_at", "")
        return session


class SessionStore:
    """세션을 파일에 저장/로드"""

    def __init__(self, base_dir: str = ".acb"):
        self.base_dir = base_dir
        self.sessions_dir = os.path.join(base_dir, "sessions")
        os.makedirs(self.sessions_dir, exist_ok=True)

    def _path(self, name: str) -> str:
        safe = name.replace(" ", "_").replace("/", "_")
        return os.path.join(self.sessions_dir, f"{safe}.json")

    def save(self, session: Session):
        with open(self._path(session.task_name), "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self, name: str) -> Optional[Session]:
        path = self._path(name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return Session.from_dict(json.load(f))
        return None

    def list_sessions(self) -> list[str]:
        if not os.path.exists(self.sessions_dir):
            return []
        files = os.listdir(self.sessions_dir)
        sessions = []
        for f in sorted(files):
            if f.endswith(".json"):
                path = os.path.join(self.sessions_dir, f)
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    sessions.append(data["task_name"])
        return sessions

    def delete(self, name: str) -> bool:
        path = self._path(name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
