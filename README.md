# ACB - Agentic Coding Bot

에이전틱 코딩 프로세스를 체계적으로 가이드하는 개인 어시스턴트 봇입니다.
**수동 인터랙티브 모드**와 **자율 AI 에이전트 모드** 두 가지를 지원합니다.

## 왜 필요한가?

AI와 함께 코딩할 때 체계적인 프로세스 없이 바로 구현에 뛰어들면:
- 요구사항을 놓치거나 잘못 이해함
- 기존 코드를 읽지 않고 수정하여 버그 발생
- 불필요한 복잡성 추가
- 검증 없이 배포하여 장애 발생

ACB는 6단계 프로세스를 따라가도록 가이드하여 이런 문제를 예방합니다.

## 두 가지 모드

### 1. 인터랙티브 모드 (`acb`)
사용자가 각 단계를 직접 진행하며, 체크리스트와 메모를 통해 프로세스를 관리합니다.

### 2. 자율 에이전트 모드 (`acb auto`)
Claude API를 활용하여 요구사항 분석부터 배포까지 전체 파이프라인을 자동으로 수행합니다.

```
인터랙티브: ANALYZE → EXPLORE → PLAN → IMPLEMENT → VERIFY → DELIVER
자율 에이전트: ANALYZE → EXPLORE → PLAN → IMPLEMENT → VERIFY → DELIVER → REVIEW → DEPLOY
```

## 프로세스 (8단계)

| 단계 | 핵심 질문 | 산출물 | 모드 |
|------|-----------|--------|------|
| **ANALYZE** | 무엇을 만들어야 하는가? | 요구사항, 성공 기준 | 공통 |
| **EXPLORE** | 현재 상태는 어떠한가? | 파일 목록, 아키텍처 메모 | 공통 |
| **PLAN** | 어떻게 만들 것인가? | TODO 목록, 구현 순서 | 공통 |
| **IMPLEMENT** | 코드를 작성한다 | 코드, 검증 결과 | 공통 |
| **VERIFY** | 제대로 동작하는가? | 테스트 결과, 리뷰 | 공통 |
| **DELIVER** | 변경사항을 전달한다 | 커밋, PR | 공통 |
| **REVIEW** | 코드리뷰를 반영한다 | 수정 커밋 | 자율 전용 |
| **DEPLOY** | 배포한다 | 배포 결과 | 자율 전용 |

## 설치 및 실행

```bash
# 의존성 설치
pip install -e .

# 개발 의존성 포함 설치
pip install -e ".[dev]"

# 인터랙티브 모드 실행
acb

# 자율 에이전트 모드 실행
ANTHROPIC_API_KEY=sk-... acb auto "사용자 인증 API 구현"
```

## 사용법

### 인터랙티브 모드

```
$ acb

  Agentic Coding Bot
  에이전틱 코딩 프로세스 어시스턴트

새로운 코딩 세션을 시작합니다.
어떤 작업을 하려고 하시나요?

Task > 사용자 인증 API 구현
```

#### 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `next` / `prev` | 다음/이전 단계 이동 |
| `goto <N>` | N번 단계로 이동 (1-6) |
| `check <N>` | 체크리스트 N번 항목 토글 |
| `note <text>` | 현재 단계에 메모 추가 |
| `task <text>` | 작업 항목 추가 |
| `done <N>` | 작업 N번 완료 토글 |
| `status` | 전체 진행 상황 보기 |
| `guide` | 현재 단계 상세 가이드 |
| `export` | 마크다운으로 보고서 출력 |
| `save` / `load` | 세션 저장/로드 |
| `auto <요구사항>` | 자율 모드로 전환 |
| `help` | 전체 명령어 보기 |

#### 예시 워크플로우

```bash
# 1. ANALYZE 단계
[ANALYZE] > note 사용자 로그인/회원가입 API 필요
[ANALYZE] > note JWT 토큰 기반 인증
[ANALYZE] > check 0    # 요구사항 확인
[ANALYZE] > check 4    # 완료 기준 정의
[ANALYZE] > next

# 2. EXPLORE 단계
[EXPLORE] > note src/auth/ 디렉토리에 기존 인증 코드 존재
[EXPLORE] > check 0    # 프로젝트 구조 파악
[EXPLORE] > next

# 3. PLAN 단계
[PLAN] > task User 모델 정의
[PLAN] > task 로그인 엔드포인트 구현
[PLAN] > task JWT 미들웨어 구현
[PLAN] > task 테스트 작성
[PLAN] > next

# 4~6. 구현, 검증, 전달...
```

### 자율 에이전트 모드

자율 모드는 Claude API를 사용하여 전체 개발 파이프라인을 자동으로 수행합니다.

#### 초기 설정

```bash
# 대화형 설정 (프로젝트별 1회)
acb auto init
```

설정 항목:
- 프로그래밍 언어, 프레임워크
- 테스트/린트/빌드/배포 명령어
- 기본 브랜치

#### 실행

```bash
# 기본 실행 (각 단계마다 확인 요청)
ANTHROPIC_API_KEY=sk-... acb auto "사용자 인증 API 구현"

# 확인 없이 자동 진행
acb auto --no-confirm "버그 수정: 로그인 실패 시 500 에러"

# PR 생성 없이 (로컬 개발만)
acb auto --no-pr "리팩토링: 코드 정리"

# 커밋/푸시 없이 (코드 생성만)
acb auto --no-commit "프로토타입: 새 기능 탐색"

# 배포까지 수행
acb auto --deploy "핫픽스: 긴급 버그 수정"
```

#### 자율 모드 파이프라인

```
사용자 요구사항 입력
  │
  ├─ [ANALYZE]   LLM이 요구사항 분석, 구조화
  ├─ [EXPLORE]   코드베이스 자동 탐색 (파일 읽기, 검색)
  ├─ [PLAN]      구현 계획 수립, 태스크 분해
  ├─ [IMPLEMENT] 태스크별 코드 자동 생성/수정
  ├─ [VERIFY]    테스트/린트 자동 실행, 결과 분석
  ├─ [DELIVER]   Git 커밋 → 푸시 → PR 생성
  ├─ [REVIEW]    PR 리뷰 코멘트 읽기 → 자동 수정 반영
  └─ [DEPLOY]    배포 명령어 실행
```

#### 아키텍처

```
DevAgent.run(requirement)
  │
  ├── LLMClient (Claude API)
  │   ├── tool_use 기반 에이전틱 루프
  │   └── 단계별 시스템 프롬프트
  │
  ├── ToolExecutor (도구 실행)
  │   ├── read_file / write_file / edit_file
  │   ├── run_command (셸 실행)
  │   ├── search_files / search_content
  │   └── list_directory
  │
  └── GitOps + GitHubOps
      ├── 브랜치 관리, 커밋, 푸시
      ├── PR 생성, 리뷰 읽기
      └── 배포 실행
```

## 프로젝트 구조

```
claude-playground/
├── acb/
│   ├── __init__.py      # 패키지 초기화
│   ├── cli.py           # CLI 메인 인터페이스 (인터랙티브 + auto)
│   ├── display.py       # Rich 기반 터미널 UI
│   ├── process.py       # 프로세스 엔진 및 상태 관리
│   ├── agent.py         # 자율 에이전트 파이프라인 오케스트레이터
│   ├── config.py        # 에이전트 설정 관리
│   ├── llm.py           # Claude API 클라이언트 (tool_use 지원)
│   ├── tools.py         # 에이전트용 도구 실행기
│   └── git_ops.py       # Git/GitHub 자동화
├── tests/
│   ├── test_agent.py    # 파이프라인 상태, JSON 추출 테스트
│   ├── test_config.py   # 설정 관리 테스트
│   ├── test_git_ops.py  # Git 작업 테스트
│   ├── test_llm.py      # LLM 도구/프롬프트 테스트
│   └── test_tools.py    # 도구 실행 테스트
├── templates/
│   ├── CLAUDE.md.template        # CLAUDE.md 템플릿
│   └── session_report.md.template # 세션 보고서 템플릿
├── PROCESS.md           # 프로세스 상세 문서
├── pyproject.toml       # 프로젝트 설정
└── README.md
```

## 개발

```bash
# 테스트 실행
pytest tests/ -v

# 린트
ruff check acb/ tests/

# 린트 자동 수정
ruff check --fix acb/ tests/
```

## 상세 프로세스 문서

각 단계의 상세 체크리스트와 가이드는 [PROCESS.md](./PROCESS.md)를 참고하세요.
